"""Overview derived from the same reviewed files and adapters as the detail pages."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from .charts import seasonal_charts, grouped_season_chart
from .workbook_data import load_bundle
from .repository import district_rows


@require_safe
def home(request):
    charts, coverage, grouped = (
        [],
        {"seasons": None, "observations": None, "years": "Unavailable"},
        None,
    )
    crops, periods = [], []
    crop, period = request.GET.get("crop", "Maize"), request.GET.get("period", "")
    try:
        observations = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))["observations"]
        production = [r for r in observations if r["indicator"] == "production"]
        crops = sorted({r["crop"] for r in production})
        periods = sorted({r["period"] for r in production})
        if crop not in crops or (period and period not in periods):
            raise Http404("Unknown overview crop or reporting period")
        selected = [
            r
            for r in production
            if r["crop"] == crop and (not period or r["period"] == period)
        ]
        charts, _ = seasonal_charts(selected)
        grouped = grouped_season_chart(selected)
        years = sorted({r["period"].split()[0] for r in observations})
        coverage = dict(
            seasons=len({r["period"] for r in observations}),
            observations=sum(r["status"] == "observed" for r in observations),
            missing=sum(r["status"] != "observed" for r in observations),
            years="–".join([years[0], years[-1]]) if len(years) > 1 else years[0],
        )
    except (OSError, ValueError, KeyError):
        pass
    district_coverage = {"districts": None, "crops": None, "period": "Unavailable"}
    try:
        districts = district_rows(settings.PUBLIC_EVIDENCE_ROOT)
        ids = {r["district_id"] for r in districts}
        counts = {
            len({r["display_crop"] for r in districts if r["district_id"] == key})
            for key in ids
        }
        district_coverage = dict(
            districts=len(ids),
            crops=(
                str(min(counts)) if len(counts) == 1 else f"{min(counts)}–{max(counts)}"
            ),
            period=", ".join(sorted({r["season"] for r in districts})),
        )
    except (
        OSError,
        ValueError,
        KeyError,
        DatabaseError,
        ObjectDoesNotExist,
        ImproperlyConfigured,
    ):
        pass
    return render(
        request,
        "evidence/home.html",
        dict(
            charts=charts,
            coverage=coverage,
            grouped_chart=grouped,
            district_coverage=district_coverage,
            crop=crop,
            period=period,
            overview_crops=crops,
            overview_periods=periods,
        ),
    )
