from decimal import Decimal
from urllib.parse import urlencode
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
    demo_active = request.GET.get("data") == "demo"
    try:
        if demo_active:
            from .demo_data import district_examples
            rows = district_examples()
        else:
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
    periods = sorted({(r["season"], r["reference_period"]) for r in rows})
    period = request.GET.get("period", "2026 B")
    if period not in dict(periods):
        raise Http404("Reporting period is not available in this dataset")
    all_period_rows = rows
    rows = [r for r in rows if r["season"] == period]
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
                mocked=demo_active,
                source=("Synthetic / illustrative — not official statistics. · " + r["cell_reference"] if demo_active else f"{r['worksheet']}!{r['cell_reference']} · NISR SAS 2026 Season B"),
            )
            for r in sorted(district_crop_rows, key=lambda r: r["display_crop"])
            if r["measure"] == chart_measure
        ]
        chart = bar_chart(
            f"{dict(districts)[district_id]} · {title}",
            source_unit,
            points,
            f"{period} · " + ("Synthetic / illustrative — not official statistics." if demo_active else "Published crop estimates in alphabetical order."),
        )
    history_chart = None
    if demo_active and crop and district_id:
        history = [r for r in all_period_rows if r["district_id"] == district_id and r["crop_code"] == crop and r["measure"] == chart_measure]
        history_chart = bar_chart(
            f"{dict(districts)[district_id]} · {dict(crops)[crop]} · illustrative period comparison",
            MEASURES[chart_measure][2],
            [dict(label=r["season"], value=r["value"], unit=r["unit"], mocked=True,
                  available=r["source_value_status"] in {"numeric", "numeric_zero"},
                  source="Synthetic / illustrative — not official statistics. · " + r["cell_reference"]) for r in history],
            "Illustrative periods remain separate. No annual aggregation or policy target comparison.",
        )
    published_url = "?" + urlencode(dict(province=province_id, district=district_id, crop=crop, period="2026 B", chart_measure=chart_measure))
    from .demo_data import district_examples
    demo_options = district_examples()
    demo_province = province_id if province_id in {r["province_id"] for r in demo_options} else ""
    demo_district = district_id if district_id in {r["district_id"] for r in demo_options if r["province_id"] == demo_province} else ""
    demo_crop = crop if crop in {r["crop_code"] for r in demo_options if r["district_id"] == demo_district} else ""
    demo_url = "?" + urlencode(dict(data="demo", province=demo_province, district=demo_district, crop=demo_crop, period=period if demo_active else "2026 B", chart_measure=chart_measure))
    return render(
        request,
        "evidence/district.html",
        dict(
            chart=chart, history_chart=history_chart, demo_active=demo_active,
            published_url=published_url, demo_url=demo_url,
            district_eyebrow="DEMONSTRATION DATA" if demo_active else "OFFICIAL DISTRICT EVIDENCE",
            period=period, periods=periods, reference_period=dict(periods)[period],
            district_description=f"{period.replace(' ', ' Season ', 1)} ({dict(periods)[period].replace('-', '–')}) · " + ("Demonstration data" if demo_active else "Source: NISR"),
            population="Illustrative aggregate coverage; no sample or farmer population" if demo_active else "SAS district crop estimates; no farmer-type breakdown in this extract",

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
