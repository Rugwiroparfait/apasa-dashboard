"""Deterministic aggregate examples; never used by the published data adapter."""
from decimal import Decimal
from .district_data import MEASURES
from .curation import annotate

LABEL = "Synthetic / illustrative — not official statistics."
GENERATED_ON = "2026-10-31"
VERSION = "apasa-interface-demo-v1"
PERIODS = [("2025 B", "March–June 2025"), ("2026 A", "September 2025–February 2026"), ("2026 B", "March–June 2026")]


def district_examples():
    rows = []
    places = [("1", "City of Kigali", "11", "Nyarugenge"), ("1", "City of Kigali", "12", "Gasabo"), ("2", "Southern Province", "24", "Huye")]
    for place_index, (pid, province, did, district) in enumerate(places):
        for crop_index, crop in enumerate(["Maize", "Bush bean", "Cassava"]):
            for period_index, (season, reference_period) in enumerate(PERIODS):
                cultivated = Decimal(400 + place_index * 180 + crop_index * 90 + period_index * 35)
                harvested = cultivated * Decimal("0.9")
                yield_value = Decimal(1800 + crop_index * 650 + place_index * 120 + period_index * 100)
                # An explicit zero example, kept distinct from the missing example below.
                if did == "11" and crop == "Cassava" and season == "2025 B":
                    yield_value = Decimal(0)
                values = dict(cultivated_crop_area=cultivated, harvested_crop_area=harvested,
                              average_crop_yield=yield_value, crop_production=harvested * yield_value / 1000)
                for measure, value in values.items():
                    missing = did == "24" and crop == "Bush bean" and season == "2026 A" and measure in {"average_crop_yield", "crop_production"}
                    raw = "" if missing else format(value, "f")
                    state = "blank" if missing else "numeric_zero" if value == 0 else "numeric"
                    title, display_unit, unit, _ = MEASURES[measure]
                    key = f"{VERSION}:{did}:{crop}:{season}:{measure}"
                    rows.append(dict(
                        province_id=pid, province=province, district_id=did, district=district,
                        sas_district_label=district, crop_sas_label=crop, season=season,
                        reference_period=reference_period, geography_level="district", country="Rwanda",
                        measure=measure, value=raw, unit=unit, title=title, display_unit=display_unit,
                        source_value_status=state, source_value_raw=raw,
                        value_display=(raw + (" — illustrative zero" if value == 0 else "")) if not missing else "Unavailable — blank in source",
                        source_agency="", source_report="", source_workbook_url="",
                        table_name=LABEL, worksheet="APASA generated example", cell_reference=key,
                        population="Illustrative aggregate crop coverage; no sampled farmer population",
                        is_mocked=True, generated_on=GENERATED_ON, demo_version=VERSION,
                    ))
    return annotate(rows, "district")
