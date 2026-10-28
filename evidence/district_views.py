from decimal import Decimal
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .district_data import MEASURES
from .repository import district_rows
from .curation import crop_options, resolve_crop
from .charts import bar_chart
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured


@require_safe
def district_statistics(request):
    try:
        rows = district_rows(settings.PUBLIC_EVIDENCE_ROOT)
    except (
        OSError,
        ValueError,
        KeyError,
        DatabaseError,
        ObjectDoesNotExist,
        ImproperlyConfigured,
    ):
        return render(request, "evidence/district_unavailable.html", status=503)
    province_id = request.GET.get("province", "")
    district_id = request.GET.get("district", "")
    crop = request.GET.get("crop", "")
    provinces = sorted({(r["province_id"], r["province"]) for r in rows})
    if province_id and province_id not in dict(provinces):
        raise Http404("Unknown province")
    districts = sorted(
        {
            (r["district_id"], r["district"])
            for r in rows
            if r["province_id"] == province_id
        },
        key=lambda x: x[1],
    )
    if district_id and district_id not in dict(districts):
        raise Http404("District is not in selected province")
    district_crop_rows = (
        [r for r in rows if r["district_id"] == district_id] if district_id else []
    )
    crops = crop_options(district_crop_rows)
    if crop:
        try:
            crop = resolve_crop(crop, district_crop_rows)
        except ValueError:
            raise Http404("Crop unavailable for selected district")
    selected = [r for r in district_crop_rows if r["crop_code"] == crop] if crop else []
    selected.sort(key=lambda r: list(MEASURES).index(r["measure"]))
    for row in selected:
        if row["source_value_status"] in {"numeric", "numeric_zero"}:
            row["summary_display"] = format(Decimal(row["value"]), ",.2f") + (
                " — reported zero"
                if row["source_value_status"] == "numeric_zero"
                else ""
            )
        else:
            row["summary_display"] = row["value_display"]
    chart_measure = request.GET.get("chart_measure", "crop_production")
    if chart_measure not in MEASURES:
        raise Http404("Unknown chart measure")
    chart = None
    if district_id:
        title, unit, source_unit, _ = MEASURES[chart_measure]
        points = [
            dict(
                label=r["display_crop"],
                value=r["value"],
                unit=source_unit,
                available=r["source_value_status"] in {"numeric", "numeric_zero"},
                highlight=r["crop_code"] == crop,
                source=f"{r['worksheet']}!{r['cell_reference']} · NISR SAS 2026 Season B",
            )
            for r in sorted(district_crop_rows, key=lambda r: r["display_crop"])
            if r["measure"] == chart_measure
        ]
        chart = bar_chart(
            f"{dict(districts)[district_id]} · {title}",
            source_unit,
            points,
            "2026 Season B · Published crop estimates in alphabetical order.",
        )
    return render(
        request,
        "evidence/district.html",
        dict(
            chart=chart,
            chart_measure=chart_measure,
            chart_measures=[(key, value[0]) for key, value in MEASURES.items()],
            provinces=provinces,
            districts=districts,
            crops=crops,
            province_id=province_id,
            district_id=district_id,
            crop=crop,
            crop_name=dict(crops).get(crop, ""),
            selected=selected,
            province_name=dict(provinces).get(province_id, ""),
            district_name=dict(districts).get(district_id, ""),
        ),
    )
