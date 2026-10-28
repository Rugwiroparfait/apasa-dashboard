"""Authenticated, read-only workbook exploration and labelled downloads."""

import csv
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .workbook_data import load_bundle
from .charts import seasonal_charts

LABELS = {
    "production": "Crop production",
    "yield": "Crop yield",
    "improved_seeds": "Farmers using improved seeds",
    "inorganic_fertilizer": "Farmers using inorganic fertilizer",
}


@require_safe
def workbook_evidence(request):
    try:
        bundle = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
    except (OSError, ValueError, KeyError):
        return render(request, "evidence/policy_unavailable.html", status=503)
    rows = [dict(row) for row in bundle["observations"]]
    defaults = {"indicator": "production", "crop": "Maize"} if not request.GET else {}
    filters = []
    for key, label in [
        ("indicator", "Measure"),
        ("crop", "Crop or crop group"),
        ("population", "Farmer population"),
        ("period", "Reporting period"),
    ]:
        choices = sorted({r[key] for r in bundle["observations"]})
        value = request.GET.get(key, defaults.get(key, ""))
        if value and value not in choices:
            raise Http404("Unknown workbook filter")
        filters.append(
            {
                "name": key,
                "label": label,
                "value": value,
                "options": [(v, LABELS.get(v, v)) for v in choices],
            }
        )
        if value:
            rows = [r for r in rows if r[key] == value]
    mock = request.GET.get("mock") == "1"
    for row in rows:
        row["label"] = LABELS[row["indicator"]]
        row["source_value"] = row["value"]
        if mock and row["status"] == "unavailable":
            row.update(
                value=(
                    "1000"
                    if row["unit"] == "MT"
                    else "1" if row["unit"] == "MT/ha" else "50"
                ),
                status="MOCKED — illustrative, not official evidence",
                mocked=True,
            )
    if request.GET.get("download") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        has_mock = any(r["mocked"] for r in rows)
        response["Content-Disposition"] = (
            'attachment; filename="apasa-workbook-evidence'
            + ("-MOCKED" if has_mock else "")
            + '.csv"'
        )
        fields = [
            "period",
            "indicator",
            "crop",
            "population",
            "geography",
            "value",
            "source_value",
            "unit",
            "status",
            "mocked",
            "source_workbook",
            "source_sheet",
            "source_cell",
            "source_sha256",
        ]
        writer = csv.DictWriter(response, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return response
    charts, chart_preview = seasonal_charts(rows)
    params = request.GET.copy()
    for item in filters:
        params[item["name"]] = item["value"]
    params["download"] = "csv"
    return render(
        request,
        "evidence/workbooks.html",
        {
            "rows": rows,
            "charts": charts,
            "chart_preview": chart_preview,
            "filters": filters,
            "register": bundle["register"],
            "mock_requested": mock,
            "download_query": params.urlencode(),
            "limitations": bundle["limitations"],
        },
    )
