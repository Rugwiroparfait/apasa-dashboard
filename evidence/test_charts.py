"""Chart integrity: units, zero baselines, missingness, series boundaries and rendered sources."""

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from .charts import bar_chart, seasonal_charts


class ChartGeometryTests(SimpleTestCase):
    def test_zero_missing_nonfinite_and_negative_are_not_fabricated(self):
        chart = bar_chart(
            "Values",
            "MT",
            [
                dict(label=str(v), value=v, unit="MT")
                for v in ["0", "100", "", "NaN", "-1"]
            ],
        )
        self.assertTrue(chart["bars"][0]["zero"])
        self.assertEqual(chart["bars"][0]["width"], 0)
        self.assertEqual(chart["bars"][1]["width"], 430)
        self.assertEqual(chart["numeric_count"], 2)
        for row in chart["bars"][2:]:
            self.assertFalse(row["available"])
            self.assertEqual(row["display"], "Unavailable")

    def test_units_cannot_share_a_chart(self):
        with self.assertRaises(ValueError):
            bar_chart(
                "Bad comparison", "MT", [dict(label="yield", unit="MT/ha", value="2")]
            )

    def test_seasons_and_populations_remain_separate(self):
        rows = [
            dict(
                indicator="improved_seeds",
                crop="All crops",
                population=p,
                unit="%",
                period=f"2024 Season {s}",
                value="20",
                status="observed",
                mocked=False,
                source_workbook="source.xlsx",
                source_sheet="Table 17",
                source_cell="D36",
            )
            for p in ["SSF", "LSF"]
            for s in ["A", "B"]
        ]
        charts, truncated = seasonal_charts(rows)
        self.assertEqual(len(charts), 4)
        self.assertFalse(truncated)
        for chart in charts:
            self.assertEqual(len(chart["bars"]), 1)
            self.assertIn("Table 17!D36", chart["bars"][0]["source"])


class ChartPageTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("chart_reader"))

    def test_national_chart_filters_and_default_download_agree(self):
        response = self.client.get("/workbook-evidence/")
        self.assertEqual(len(response.context["rows"]), 6)
        self.assertEqual(len(response.context["charts"]), 2)
        self.assertEqual(
            response.context["charts"][0]["scale_label"],
            response.context["charts"][1]["scale_label"],
        )
        self.assertContains(response, "<svg", count=2)
        self.assertContains(response, "Table 6!I6")
        exported = self.client.get(
            "/workbook-evidence/?" + response.context["download_query"]
        )
        self.assertEqual(len(exported.content.decode().splitlines()), 7)
        response = self.client.get("/workbook-evidence/?indicator=yield&crop=Maize")
        self.assertEqual({c["unit"] for c in response.context["charts"]}, {"MT/ha"})
        self.assertContains(response, "1.2921133073541144")

    def test_mock_chart_warning_and_original_bundle_are_separate(self):
        response = self.client.get(
            "/workbook-evidence/?indicator=yield&crop=Cereals&mock=1"
        )
        self.assertContains(response, "MOCKED values included")
        self.assertTrue(all(c["has_mock"] for c in response.context["charts"]))
        response = self.client.get("/workbook-evidence/?indicator=yield&crop=Cereals")
        self.assertTrue(
            all(c["numeric_count"] == 0 for c in response.context["charts"])
        )
        self.assertNotContains(response, "MOCKED values included")

    def test_district_chart_uses_one_measure_and_keeps_source_order(self):
        response = self.client.get(
            "/district-crop-statistics/?province=1&district=11&crop=Maize&chart_measure=average_crop_yield"
        )
        chart = response.context["chart"]
        self.assertEqual(chart["unit"], "Kg/Ha")
        self.assertEqual(len(chart["bars"]), 15)
        labels = [r["label"] for r in chart["bars"]]
        self.assertEqual(labels, sorted(labels))
        maize = next(r for r in chart["bars"] if r["label"] == "Maize")
        self.assertTrue(maize["highlight"])
        self.assertIn("Table 11", maize["source"])
        self.assertContains(response, "<svg")
        self.assertEqual(
            self.client.get(
                "/district-crop-statistics/?chart_measure=wrong"
            ).status_code,
            404,
        )

    def test_retired_research_and_redundant_navigation_are_removed(self):
        response = self.client.get("/workspace/overview/")
        self.assertNotContains(response, "AHS Research Evidence")
        self.assertNotContains(response, "Separate survey research")
        nav = (
            response.content.decode()
            .split('<nav class="workspace-links"', 1)[1]
            .split("</nav>", 1)[0]
        )
        self.assertNotIn("/national-policy-evidence/crop/", nav)
        self.assertNotIn("/national-policy-evidence/note/", nav)
        for path in [
            "/evidence/maize/",
            "/evidence/figures/s4_q1.png",
            "/evidence/maize/summary.csv",
        ]:
            self.assertEqual(self.client.get(path).status_code, 404)


class SeasonalOverviewTests(TestCase):
    def test_dimensional_faces_stay_within_true_zero_baseline_geometry(self):
        from .charts import grouped_season_chart
        from .workbook_data import load_bundle
        from django.conf import settings

        rows = [
            r
            for r in load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))["observations"]
            if r["crop"] == "Maize" and r["indicator"] == "production"
        ]
        chart = grouped_season_chart(rows)
        a = next(b for b in chart["bars"] if b["label"] == "2024 Season A")
        b = next(b for b in chart["bars"] if b["label"] == "2024 Season B")
        self.assertAlmostEqual(
            a["column_height"] / b["column_height"],
            float(a["value"]) / float(b["value"]),
        )
        for bar in chart["bars"]:
            self.assertAlmostEqual(bar["column_y"] + bar["column_height"], 320)
            for face in ("top_face", "side_face"):
                ys = [float(p.split(",")[1]) for p in bar[face].split()]
                self.assertGreaterEqual(min(ys), bar["column_y"])
                self.assertLessEqual(max(ys), 320)

    def test_overview_coverage_comes_from_current_adapters(self):
        from unittest.mock import patch
        from .workbook_data import load_bundle
        from django.conf import settings

        original = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
        rows = [
            r
            for r in original["observations"]
            if r["crop"] == "Maize" and r["indicator"] == "production"
        ][:2]
        districts = [
            dict(district_id="test", display_crop=crop, season="test period")
            for crop in ["A", "B", "C"]
        ]
        with patch(
            "evidence.views.load_bundle", return_value={"observations": rows}
        ), patch("evidence.views.district_rows", return_value=districts):
            # This test isolates the read-only overview from the authentication middleware.
            from django.contrib.auth import get_user_model

            self.client.force_login(
                get_user_model().objects.create_user("overview-current-data")
            )
            response = self.client.get("/workspace/overview/")
        self.assertEqual(response.context["coverage"]["seasons"], 2)
        self.assertEqual(response.context["coverage"]["observations"], 2)
        self.assertEqual(response.context["district_coverage"]["districts"], 1)
        self.assertEqual(response.context["district_coverage"]["crops"], "3")
