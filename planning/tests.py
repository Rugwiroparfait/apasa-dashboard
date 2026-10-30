"""Numerical checks and end-to-end controls for the reviewed planning workflow."""

import csv
import io
import json
import math
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, SimpleTestCase, Client
from django.urls import reverse
from .models import (
    SourceBatch,
    IndicatorVersion,
    Assessment,
    ForecastModel,
    ActionBrief,
    FollowUp,
    ReviewEvent,
    State,
)
from .validation import validate_csv, fingerprint, period_key
from .calculations import comparison, fit_forecast, scenario
from .services import transition
from .briefs import draft_brief


def csv_bytes(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def point(year, value, **changes):
    row = dict(
        measure="production",
        crop="Maize",
        unit="MT",
        period=str(year),
        geography_code="RW",
        geography="Rwanda",
        population="All farmer types",
        value=str(value),
        standard_error="",
        is_mocked=False,
        source_reference="Reviewed source table 1",
    )
    row.update(changes)
    return row


class ValidationTests(SimpleTestCase):
    def test_valid_csv_preserves_source_zero_and_precision(self):
        rows, errors = validate_csv(
            csv_bytes([point(2025, 0), point(2026, "170.123456789")])
        )
        self.assertFalse(errors)
        self.assertEqual(rows[0]["value"], "0")
        self.assertEqual(rows[1]["value"], "170.123456789")

    def test_any_bad_row_quarantines_whole_batch(self):
        rows, errors = validate_csv(csv_bytes([point(2025, 150), point(2026, "NaN")]))
        self.assertEqual(rows, [])
        self.assertIn("Row 3", errors[0])
        for value in ["-1", "Infinity", "N/A", "1e99"]:
            self.assertTrue(validate_csv(csv_bytes([point(2026, value)]))[1])

    def test_headers_and_population_duplicates_are_checked(self):
        self.assertTrue(validate_csv(b"farmer_name,phone\nPerson,123\n")[1])
        self.assertTrue(
            validate_csv(csv_bytes([point(2026, 100), point(2026, 101)]))[1]
        )
        self.assertTrue(
            validate_csv(
                csv_bytes(
                    [
                        point(2026, 1000, unit="Kg/Ha", measure="yield"),
                        point(2026, 1, unit="MT/ha", measure="yield"),
                    ]
                )
            )[1]
        )
        self.assertTrue(validate_csv(csv_bytes([point(2026, 101, unit="%")]))[1])
        self.assertTrue(validate_csv(b"x" * (2 * 1024 * 1024 + 1))[1])

    def test_periods_have_no_season_or_fiscal_shortcuts(self):
        self.assertEqual(period_key("2026 Season B"), ("Season B", 2026))
        self.assertEqual(period_key("2026/27"), ("fiscal", 2026))
        for value in ["2026/26", "2026 Season D", "2026 annual", "2013-2026"]:
            with self.assertRaises(ValueError):
                period_key(value)


class PlanningFixture(TestCase):
    def setUp(self):
        users = get_user_model()
        self.author = users.objects.create_user(
            "author", password="ExamplePassword!2026"
        )
        self.reviewer = users.objects.create_user(
            "reviewer", password="ExamplePassword!2026"
        )
        for user, role in [
            (self.author, "National policymaker"),
            (self.reviewer, "District agriculture officer"),
        ]:
            user.groups.add(Group.objects.get_or_create(name=role)[0])
        self.rows = [point(2019 + i, 100 + 10 * i) for i in range(8)]
        self.rows[-1]["standard_error"] = "5"
        self.batch = SourceBatch.objects.create(
            title="Reviewed annual data",
            source_url="https://example.org/data",
            source_reference="Table 1",
            methodology="SAS-reviewed-v1",
            content_sha256=fingerprint(csv_bytes(self.rows)),
            rows=self.rows,
            status=State.APPROVED,
            created_by=self.author,
            reviewed_by=self.reviewer,
        )
        self.indicator = IndicatorVersion.objects.create(
            framework="PSTA5",
            code="TEST-1",
            version=1,
            name="Maize production",
            measure="production",
            crop="Maize",
            unit="MT",
            population="All farmer types",
            geography_code="RW",
            geography="Rwanda",
            methodology=self.batch.methodology,
            baseline_period="2019",
            baseline_value=100,
            target_period="2028",
            target_value=200,
            direction="higher",
            source_url="https://example.org/policy",
            source_reference="Authenticated policy table 1",
            status=State.APPROVED,
            created_by=self.author,
            reviewed_by=self.reviewer,
        )
        self.report = Assessment.objects.create(
            indicator=self.indicator,
            dataset=self.batch,
            row_index=7,
            mapping_notes="Checked original definitions and sampling methodology.",
            methodology_confirmed=True,
            status=State.APPROVED,
            created_by=self.author,
            reviewed_by=self.reviewer,
        )
        self.client.force_login(self.author)

    def model(self, status=State.APPROVED, tolerance=0):
        spec = fit_forecast(self.report, Decimal(tolerance))
        return ForecastModel.objects.create(
            assessment=self.report,
            status=status,
            created_by=self.author,
            acceptable_rmse=tolerance,
            specification=spec,
            training_sha256=fingerprint(
                json.dumps(spec["points"], sort_keys=True).encode()
            ),
        )


class CalculationTests(PlanningFixture):
    def test_gap_progress_required_pace_and_sampling_interval(self):
        result = comparison(self.report)
        self.assertTrue(result["comparable"])
        self.assertEqual(result["actual"], 170)
        self.assertEqual(result["gap"], 30)
        self.assertAlmostEqual(result["progress"], 70)
        self.assertEqual(result["annual_change"], 15)
        self.assertAlmostEqual(result["required_rate"], ((200 / 170) ** 0.5 - 1) * 100)
        self.assertAlmostEqual(result["sampling_interval"]["lower"], 160.2)
        self.assertAlmostEqual(result["sampling_interval"]["gap_lower"], 20.2)
        self.assertEqual(result["trend"]["n"], 8)
        self.assertAlmostEqual(result["trend"]["slope"], 10)

    def test_lower_is_better_and_percentage_point_gap(self):
        self.indicator.direction = "lower"
        self.indicator.unit = "%"
        self.indicator.baseline_value = Decimal(100)
        self.indicator.target_value = Decimal(50)
        self.batch.rows = [point(2019 + i, 100 - 3 * i, unit="%") for i in range(8)]
        self.batch.rows[-1]["value"] = "80"
        result = comparison(self.report)
        self.assertEqual(result["gap"], 30)
        self.assertEqual(result["gap_label"], "percentage points")
        self.assertAlmostEqual(result["progress"], 40)
        self.assertLess(result["required_rate"], 0)

    def test_zero_and_equal_baseline_cases_do_not_divide_by_zero(self):
        self.batch.rows[-1]["value"] = "0"
        result = comparison(self.report)
        self.assertIsNone(result["relative_change"])
        self.assertIsNone(result["required_rate"])
        self.assertEqual(result["gap"], 200)
        self.indicator.target_value = Decimal(100)
        self.batch.rows[-1]["value"] = "100"
        result = comparison(self.report)
        self.assertIsNone(result["progress"])
        self.assertTrue(result["met"])
        self.indicator.target_value = Decimal(200)
        self.batch.rows[-1]["value"] = "250"
        met = comparison(self.report)
        self.assertEqual(met["annual_change"], 0)
        self.assertEqual(met["relative_change"], 0)
        self.indicator.direction = "lower"
        self.indicator.target_value = Decimal(0)
        self.assertIsNone(comparison(self.report)["target_gap_percent"])

    def test_conversion_is_explicit_and_standard_error_is_scaled(self):
        self.indicator.unit = "MT/ha"
        self.indicator.measure = "yield"
        self.indicator.baseline_value = Decimal(1)
        self.indicator.target_value = Decimal(2)
        self.batch.rows = [
            point(2019 + i, 1000 + 100 * i, unit="Kg/Ha", measure="yield")
            for i in range(8)
        ]
        self.batch.rows[-1]["standard_error"] = "50"
        result = comparison(self.report)
        self.assertAlmostEqual(result["actual"], 1.7)
        self.assertAlmostEqual(result["gap"], 0.3)
        self.assertIn("0.001", result["conversion"])
        self.assertAlmostEqual(result["sampling_interval"]["lower"], 1.602)

    def test_incompatible_or_unreviewed_evidence_produces_no_gap(self):
        for field, bad in [
            ("crop", "Rice"),
            ("population", "SSF"),
            ("geography_code", "11"),
            ("measure", "yield"),
            ("unit", "Ha"),
            ("period", "2026 Season B"),
        ]:
            original = self.batch.rows[-1][field]
            self.batch.rows[-1][field] = bad
            result = comparison(self.report)
            self.assertFalse(result["comparable"], field)
            self.assertNotIn("gap", result)
            self.batch.rows[-1][field] = original
        self.report.methodology_confirmed = False
        self.assertFalse(comparison(self.report)["comparable"])
        self.report.methodology_confirmed = True
        self.batch.status = State.DRAFT
        self.assertFalse(comparison(self.report)["comparable"])

    def test_missing_standard_error_does_not_create_sampling_uncertainty(self):
        self.batch.rows[-1]["standard_error"] = ""
        self.assertIsNone(comparison(self.report)["sampling_interval"])

    def test_forecast_holds_out_recent_years_and_fails_insufficient_history(self):
        spec = fit_forecast(self.report, Decimal(0))
        self.assertEqual(spec["train_n"], 6)
        self.assertEqual(spec["holdout_years"], [2025, 2026])
        self.assertTrue(spec["passes"])
        self.assertEqual(spec["holdout_rmse"], 0)
        self.report.row_index = 4
        self.assertEqual(len(comparison(self.report)["history"]), 5)
        with self.assertRaisesRegex(ValueError, "only 5"):
            fit_forecast(self.report, Decimal(1))

    def test_failed_validation_and_draft_models_cannot_run_scenarios(self):
        model = self.model(State.DRAFT)
        with self.assertRaises(ValueError):
            scenario(model, 2, 5)
        model.status = State.APPROVED
        result = scenario(model, 2, 5)
        self.assertAlmostEqual(result["baseline"], 190)
        self.assertAlmostEqual(result["adjusted"], 190 * 1.05**2)
        self.assertEqual(len(result["sensitivity"]), 3)
        self.batch.rows[-1]["value"] = "1200"
        self.batch.rows[-2]["value"] = "1000"
        spec = fit_forecast(self.report, Decimal(1))
        self.assertFalse(spec["passes"])


class WorkflowTests(PlanningFixture):
    def test_self_approval_and_approval_without_verification_are_blocked(self):
        self.batch.status = State.DRAFT
        self.batch.save()
        transition(
            "source",
            self.batch.pk,
            self.author,
            "submit",
            "Please verify original source metadata.",
        )
        with self.assertRaises(PermissionDenied):
            transition(
                "source",
                self.batch.pk,
                self.author,
                "approve",
                "I approved my own original source.",
                True,
            )
        with self.assertRaises(ValueError):
            transition(
                "source",
                self.batch.pk,
                self.reviewer,
                "approve",
                "I have not checked the original source.",
                False,
            )
        transition(
            "source",
            self.batch.pk,
            self.reviewer,
            "approve",
            "Verified original source and all dimensions.",
            True,
        )
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, State.APPROVED)
        self.assertEqual(
            ReviewEvent.objects.filter(
                record_type="source", record_id=self.batch.pk
            ).count(),
            2,
        )
        with self.assertRaises(ValueError):
            transition(
                "source",
                self.batch.pk,
                self.reviewer,
                "return",
                "A published version cannot be edited.",
                True,
            )

    def test_invalid_upload_is_quarantined_and_corrected_upload_is_a_new_version(self):
        payload = dict(
            title="Bad file",
            source_url="https://example.org/data",
            source_reference="Published table 1",
            methodology="v1",
            aggregate_only="on",
        )
        payload["file"] = SimpleUploadedFile(
            "source.csv", csv_bytes([point(2026, "NaN")]), content_type="text/csv"
        )
        response = self.client.post(reverse("planning:upload"), payload)
        self.assertEqual(response.status_code, 302)
        batch = SourceBatch.objects.get(title="Bad file")
        self.assertEqual(batch.status, State.QUARANTINED)
        self.assertEqual(batch.rows, [])
        with self.assertRaises(ValueError):
            transition(
                "source",
                batch.pk,
                self.author,
                "submit",
                "Please review this invalid data upload.",
            )
        payload["title"] = "Corrected file"
        payload["file"] = SimpleUploadedFile("fixed.csv", csv_bytes([point(2026, 170)]))
        self.client.post(
            reverse("planning:upload") + f"?supersedes={batch.pk}", payload
        )
        corrected = SourceBatch.objects.get(title="Corrected file")
        self.assertEqual(corrected.supersedes_id, batch.pk)

    def test_existing_source_snapshots_go_through_validation_and_review(self):
        for scope in ["national", "district"]:
            response = self.client.post(reverse("planning:existing"), {"scope": scope})
            self.assertEqual(response.status_code, 302)
            batch = SourceBatch.objects.get(title=f"Existing {scope} source snapshot")
            self.assertEqual(batch.status, State.DRAFT, batch.errors)
            self.assertTrue(batch.rows)

    def test_mocked_records_cannot_be_promoted_to_official(self):
        self.batch.is_mocked = True
        self.batch.status = State.DEMO
        self.batch.save()
        with self.assertRaisesRegex(ValueError, "Mocked"):
            transition(
                "source",
                self.batch.pk,
                self.reviewer,
                "approve",
                "Please publish this mock as official.",
                True,
            )
        self.assertFalse(comparison(self.report)["comparable"])

    def test_real_end_to_end_review_comparison_brief_and_followup(self):
        # Begin with independently approved source and policy versions.
        response = self.client.post(
            reverse("planning:assessment-create"),
            dict(
                indicator=self.indicator.pk,
                dataset=self.batch.pk,
                row_index=7,
                mapping_notes="Original source methods and definitions were checked.",
                methodology_confirmed="on",
            ),
        )
        report = Assessment.objects.order_by("-pk").first()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(report.status, State.DRAFT)
        self.assertContains(self.client.get(response["Location"]), "Draft comparison")
        transition(
            "assessment",
            report.pk,
            self.author,
            "submit",
            "Please review the mapping and all calculations.",
        )
        transition(
            "assessment",
            report.pk,
            self.reviewer,
            "approve",
            "Verified the mapping, periods and source methods.",
            True,
        )
        report.refresh_from_db()
        self.assertEqual(report.result_snapshot["actual"], 170)
        self.assertEqual(report.calculation_version, "comparison-v1")
        brief_text, method, _, _ = draft_brief(
            report,
            "Review feasible area and yield constraints with a district agronomist.",
        )
        brief = ActionBrief.objects.create(
            assessment=report,
            created_by=self.author,
            content=brief_text,
            method=method,
            proposed_action="Review crop constraints with the district team.",
        )
        transition(
            "brief",
            brief.pk,
            self.author,
            "submit",
            "Please check that this advice stays within the evidence.",
        )
        transition(
            "brief",
            brief.pk,
            self.reviewer,
            "approve",
            "Verified that proposed action is appropriate and limitations are explicit.",
            True,
        )
        response = self.client.post(
            reverse("planning:followup", args=[report.pk]),
            dict(
                owner=self.author.pk,
                action="Review production constraints with the district team.",
                due_date="2026-12-01",
                status="planned",
                outcome_notes="",
                outcome_source_url="",
                observed_value="",
            ),
        )
        self.assertEqual(response.status_code, 302)
        task = FollowUp.objects.get(assessment=report)
        self.client.force_login(self.reviewer)
        self.assertEqual(
            self.client.post(
                reverse("planning:followup-update", args=[report.pk, task.pk]), {}
            ).status_code,
            403,
        )
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("planning:followup-update", args=[report.pk, task.pk]),
            dict(
                owner=self.author.pk,
                action=task.action,
                due_date="2026-12-01",
                status="completed",
                outcome_notes="Team reviewed constraints; a new source observation is linked.",
                outcome_source_url="https://example.org/outcome",
                observed_value="175",
            ),
        )
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertEqual(self.batch.rows[-1]["value"], "170")

    def test_unapproved_action_cannot_be_tracked_as_implementation(self):
        self.assertEqual(
            self.client.post(
                reverse("planning:followup", args=[self.report.pk]), {}
            ).status_code,
            403,
        )

    def test_model_approval_requires_a_different_reviewer_and_passing_backtest(self):
        model = self.model(State.DRAFT)
        transition(
            "model",
            model.pk,
            self.author,
            "submit",
            "Please review the held-out accuracy and domain assumptions.",
        )
        with self.assertRaises(PermissionDenied):
            transition(
                "model",
                model.pk,
                self.author,
                "approve",
                "Trying to approve my own model.",
                True,
            )
        transition(
            "model",
            model.pk,
            self.reviewer,
            "approve",
            "Verified the holdout test, tolerance and appropriate intended use.",
            True,
        )
        model.refresh_from_db()
        self.assertEqual(model.status, State.APPROVED)
        self.assertAlmostEqual(scenario(model, 2, 0)["baseline"], 190)

    def test_ai_missing_credentials_preserves_factual_template_without_claiming_ai(
        self,
    ):
        with patch("planning.ai.key_binding", return_value=("", None)):
            content, method, notice, _ = draft_brief(
                self.report, "Investigate the published production constraints.", True
            )
        self.assertEqual(method, "template")
        self.assertIn("No API key", notice)
        self.assertIn("170.00", content)
        self.assertNotIn("AI-WRITTEN", content)

    def test_private_drafts_are_not_visible_to_other_users_until_submitted(self):
        self.report.status = State.DRAFT
        self.report.reviewed_by = None
        self.report.save()
        self.client.force_login(self.reviewer)
        self.assertEqual(
            self.client.get(
                reverse("planning:assessment", args=[self.report.pk])
            ).status_code,
            404,
        )

    def test_authenticated_roles_and_csrf_protect_writes(self):
        self.client.logout()
        self.assertEqual(self.client.get("/planning/").status_code, 302)
        stranger = get_user_model().objects.create_user("no_role")
        self.client.force_login(stranger)
        self.assertEqual(
            self.client.post(
                reverse("planning:existing"), {"scope": "national"}
            ).status_code,
            403,
        )
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.author)
        self.assertEqual(
            csrf.post(reverse("planning:existing"), {"scope": "national"}).status_code,
            403,
        )


class AdditionalStatisticalTests(PlanningFixture):
    def test_changed_training_evidence_invalidates_a_previous_model(self):
        model = self.model()
        self.batch.rows[0]["value"] = "101"
        with self.assertRaisesRegex(ValueError, "Training evidence changed"):
            scenario(model, 2, 0)

    def test_unvalidated_forecast_horizon_is_blocked(self):
        model = self.model()
        with self.assertRaisesRegex(ValueError, "two-year horizon"):
            scenario(model, 3, 0)

    def test_percentage_scenarios_respect_physical_bounds(self):
        self.indicator.measure = "improved_seeds"
        self.indicator.unit = "%"
        self.indicator.baseline_value = Decimal(50)
        self.indicator.target_value = Decimal(80)
        self.batch.rows = [
            point(2019 + i, 50 + 2 * i, unit="%", measure="improved_seeds")
            for i in range(8)
        ]
        model = self.model()
        result = scenario(model, 2, 100)
        self.assertEqual(result["adjusted"], 100)
        self.assertTrue(all(0 <= r["value"] <= 100 for r in result["sensitivity"]))

    def test_optional_ai_keeps_canonical_facts_and_never_publishes(self):
        from unittest.mock import MagicMock

        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Draft wording based on the supplied evidence."
                        }
                    }
                ]
            }
        ).encode()
        with patch.dict(
            "os.environ", {"APASA_AI_API_KEY": "test-placeholder-not-a-secret"}
        ), patch(
            "planning.briefs.generate",
            return_value=(
                "Draft wording based on the supplied evidence.",
                {"model": "openai/gpt-oss-20b"},
            ),
        ) as network:
            text, method, _, _ = draft_brief(
                self.report,
                "Investigate source-backed area and yield constraints.",
                True,
            )
        self.assertEqual(method, "ai")
        self.assertIn("AI-WRITTEN DRAFT — UNAPPROVED", text)
        self.assertIn("170.00", text)
        self.assertIn("CANONICAL INPUT FACTS", text)
        network.assert_called_once()
        self.report.status = State.DRAFT
        with patch.dict(
            "os.environ", {"APASA_AI_API_KEY": "test-placeholder-not-a-secret"}
        ), patch("planning.briefs.generate") as network:
            _, method, _, _ = draft_brief(
                self.report,
                "Investigate source-backed area and yield constraints.",
                True,
            )
            self.assertEqual(method, "template")
            network.assert_not_called()

    def test_new_target_versions_and_invalid_percentage_targets(self):
        from .forms import IndicatorForm

        data = {
            field: getattr(self.indicator, field) for field in IndicatorForm.Meta.fields
        }
        data.update(
            version=2,
            framework="NST2",
            measure="improved_seeds",
            unit="%",
            baseline_value="20",
            target_value="80",
        )
        form = IndicatorForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        data["target_value"] = "101"
        self.assertFalse(IndicatorForm(data=data).is_valid())


class ScenarioPublicationTests(PlanningFixture):
    def test_scenario_is_saved_then_independently_reviewed_before_use_in_advice(self):
        from .models import ScenarioRun

        model = self.model()
        response = self.client.post(
            reverse("planning:scenario", args=[model.pk]), {"years": 2, "adjustment": 5}
        )
        self.assertEqual(response.status_code, 302)
        run = ScenarioRun.objects.get(model=model)
        self.assertEqual(run.status, State.DRAFT)
        self.assertAlmostEqual(run.output["adjusted"], 209.475)
        self.assertEqual(run.output["baseline_gap"], 10)
        self.assertEqual(run.output["adjusted_gap"], 0)
        self.assertContains(self.client.get(response["Location"]), "scenario")
        with self.assertRaises(ValueError):
            draft_brief(
                self.report,
                "Investigate feasible actions with an agronomist.",
                False,
                run,
            )
        transition(
            "scenario",
            run.pk,
            self.author,
            "submit",
            "Check these scenario assumptions and uncertainty statements.",
        )
        transition(
            "scenario",
            run.pk,
            self.reviewer,
            "approve",
            "Reviewed the assumptions, horizon, model and uncertainty limits.",
            True,
        )
        run.refresh_from_db()
        content, _, _, _ = draft_brief(
            self.report, "Investigate feasible actions with an agronomist.", False, run
        )
        self.assertIn(f"Reviewed scenario {run.pk}", content)
        self.assertIn(format(run.output["adjusted"], ",.2f"), content)
        self.assertContains(
            self.client.get(
                reverse("planning:scenario-detail", args=[run.pk]) + "?download=text"
            ),
            "209.475",
        )

    def test_published_comparison_freezes_reviewed_calculations(self):
        from .calculations import report_result

        self.report.status = State.DRAFT
        self.report.reviewed_by = None
        self.report.save()
        transition(
            "assessment",
            self.report.pk,
            self.author,
            "submit",
            "Please independently verify these source mappings.",
        )
        transition(
            "assessment",
            self.report.pk,
            self.reviewer,
            "approve",
            "Verified mapping and every reported calculation.",
            True,
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.result_snapshot["gap"], 30)
        self.batch.rows[-1][
            "value"
        ] = "190"  # Simulate an accidental external mutation, not an application edit.
        self.batch.save(update_fields=["rows"])
        self.report.refresh_from_db()
        self.assertEqual(report_result(self.report)["gap"], 30)
        self.assertEqual(comparison(self.report)["gap"], 10)
