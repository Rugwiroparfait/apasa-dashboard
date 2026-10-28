"""A concise overview of the two supported planning workflows."""

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .charts import seasonal_charts
from .workbook_data import load_bundle


@require_safe
def home(request):
    try:
        bundle = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
        observations = bundle["observations"]
        maize = [
            r
            for r in observations
            if r["crop"] == "Maize" and r["indicator"] == "production"
        ]
        charts, _ = seasonal_charts(maize)
        coverage = {
            "seasons": len({r["period"] for r in observations}),
            "observations": sum(r["status"] == "observed" for r in observations),
            "missing": sum(r["status"] != "observed" for r in observations),
        }
    except (OSError, ValueError, KeyError):
        charts, coverage = [], None
    return render(
        request, "evidence/home.html", {"charts": charts, "coverage": coverage}
    )
