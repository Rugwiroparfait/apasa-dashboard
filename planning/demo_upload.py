"""Reproducible CSV for the actual aggregate upload contract, not published evidence."""
import csv
import io
from decimal import Decimal
from .validation import validate_csv

TITLE = "DEMO — Synthetic Rwanda crop observations (not official)"
RELEASE = "APASA interface demonstration dataset, version 1.0; generated 31 October 2026"
METHODOLOGY = "APASA-SYNTH-DEMO-2026-V1"
ORIGIN = "Synthetic illustrative data generated for APASA demonstration; not official NISR or MINAGRI statistics."
LABEL = "Synthetic / illustrative — not official statistics"
POPULATION = "Synthetic aggregate crop coverage; no sampled farmer population"
CSV_NAME = "synthetic_rwanda_crop_observations_v1.csv"
HEADERS = ["measure", "crop", "value", "unit", "period", "geography_code", "geography", "population", "source_reference", "standard_error", "is_mocked"]


def generate_csv():
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    for code, place, base_area in [("RW", "Rwanda", 120000), ("11", "Nyarugenge", 400), ("12", "Gasabo", 750), ("24", "Huye", 1800)]:
        for crop, area_factor, base_yield in [("Maize", "1", 2100), ("Bush bean", ".7", 850), ("Cassava", ".55", 10000)]:
            for year in range(2019, 2027):
                annual_area = annual_harvest = annual_production = Decimal(0)
                observations = []
                for season, area_weight, yield_weight in [("A", "1", "1"), ("B", ".8", ".96"), ("C", ".35", ".90")]:
                    area = (Decimal(base_area) * Decimal(area_factor) * Decimal(area_weight) * (1 + Decimal(".02") * (year - 2019))).quantize(Decimal(".01"))
                    harvested = (area * Decimal(".9")).quantize(Decimal(".01"))
                    yield_value = (Decimal(base_yield) * Decimal(yield_weight) * (1 + Decimal(".03") * (year - 2019))).quantize(Decimal(".01"))
                    production = harvested * yield_value / 1000
                    annual_area += area
                    annual_harvest += harvested
                    annual_production += production
                    observations.append((f"{year} Season {season}", area, harvested, yield_value, production))
                annual_yield = (annual_production * 1000 / annual_harvest).quantize(Decimal(".00000001"))
                observations.append((str(year), annual_area, annual_harvest, annual_yield, annual_production))
                for period, area, harvested, yield_value, production in observations:
                    for measure, value, unit in [("cultivated_area", area, "Ha"), ("harvested_area", harvested, "Ha"), ("yield", yield_value, "Kg/Ha"), ("production", production, "MT")]:
                        writer.writerow(dict(measure=measure, crop=crop, value=format(value, "f"), unit=unit,
                            period=period, geography_code=code, geography=place, population=POPULATION,
                            source_reference=f"{LABEL}. {METHODOLOGY} | {code} | {crop} | {period} | {measure}; generated 2026-10-31; no official statistical source",
                            standard_error="", is_mocked="true"))
    raw = stream.getvalue().encode("utf-8")
    rows, errors = validate_csv(raw)
    if errors or len(rows) != 1536 or not all(r["is_mocked"] for r in rows):
        raise ValueError(f"Generated demo did not pass the actual CSV validator: {errors}")
    return raw


def metadata(raw):
    from .validation import fingerprint
    return dict(
        dataset_name=TITLE, publication_release=RELEASE, methodology=METHODOLOGY, origin=ORIGIN,
        classification=LABEL, generation_date="2026-10-31", csv=CSV_NAME,
        sha256=fingerprint(raw), bytes=len(raw), row_count=1536, headers=HEADERS,
        years=list(range(2019, 2027)), period_types=["annual", "Season A", "Season B", "Season C"],
        geographies={"RW": "Rwanda", "11": "Nyarugenge", "12": "Gasabo", "24": "Huye"},
        crops=["Maize", "Bush bean", "Cassava"], population=POPULATION,
        variables={"cultivated_area": "Ha", "harvested_area": "Ha", "yield": "Kg/Ha", "production": "MT"},
        statistical_source_inputs=[], geographic_label_input="Existing public district extract; names and IDs only, not numeric values",
        assumptions=[
            "National RW is an independent illustrative series, not a sum of the three example districts. No provincial estimates are generated.",
            "Base cultivated Ha: RW=120000, 11=400, 12=750, 24=1800. Crop multipliers Maize=1, Bush bean=0.7, Cassava=0.55.",
            "Season area multipliers A=1, B=0.8, C=0.35; linear area growth multiplier=1+0.02*(year-2019). Areas rounded to two decimals.",
            "Harvested Ha=90% of cultivated Ha. Base yields Kg/Ha: Maize=2100, Bush bean=850, Cassava=10000. Season yield multipliers A=1, B=0.96, C=0.90; linear yield growth multiplier=1+0.03*(year-2019). Seasonal yields rounded to two decimals.",
            "Seasonal production MT=harvested Ha*yield Kg/Ha/1000. Annual cultivated/harvested area and production sum the three synthetic seasons; annual yield is production*1000/harvested area, rounded to eight decimals. Never add annual rows to seasonal rows.",
            "All numerical values are invented positive aggregates. Standard errors are empty; no sampling design, verification or uncertainty estimates are claimed. Unavailable required values cannot be uploaded through this parser and are not fabricated as zeros.",
            "Demonstration comparisons require matching geography, crop, measure, population, period type and methodology. Synthetic observations cannot establish official policy progress.",
        ],
        generator_command="venv/bin/python manage.py generate_observation_demo",
        safe_loading="Authenticated manual source form upload with synthetic demonstration checked; all rows is_mocked=true; no publication URL required; retained in demo state, never officially approved.",
    )
