"""Explicitly invented examples shared by the dashboard and development seeder.

Unsaved model instances let demonstrations work on an empty database without
writing during GET requests or mixing invented values into official evidence.
"""
from decimal import Decimal
import json
from .models import SourceBatch, IndicatorVersion, Assessment, State
from .validation import fingerprint


def examples():
    for label, geo, values, target, tolerance in [
        ("National demonstration", "RW", [100000, 104000, 108000, 109000, 113000, 117000, 120000, 124000], 150000, 20000),
        ("District demonstration", "11", [400, 440, 480, 510, 550, 580, 620, 660], 900, 200),
    ]:
        rows = [dict(
            measure="production", crop="Maize", unit="MT", period=str(2019 + i),
            geography_code=geo, geography="Rwanda (MOCKED)" if geo == "RW" else "Nyarugenge (MOCKED)",
            population="All farmer types", value=str(value), standard_error="", is_mocked=True,
            source_reference="MOCKED invented example; no official source",
        ) for i, value in enumerate(values)]
        batch = SourceBatch(
            title="MOCKED · " + label, source_url="",
            source_reference="Invented annual observations, demonstration only.",
            methodology="MOCKED consistent annual example", rows=rows,
            content_sha256=fingerprint(json.dumps(rows, sort_keys=True).encode()),
            status=State.DEMO, is_mocked=True,
        )
        indicator = IndicatorVersion(
            framework="PSTA5", code="DEMO-" + geo, version=1,
            name="MOCKED · " + label + " maize production", measure="production", crop="Maize",
            unit="MT", population="All farmer types", geography_code=geo, geography=rows[0]["geography"],
            methodology=batch.methodology, baseline_period="2019", baseline_value=Decimal(values[0]),
            target_period="2028", target_value=Decimal(target), direction="higher",
            source_url="",
            source_reference="MOCKED target, not an authenticated PSTA5 goal.",
            status=State.DEMO, is_mocked=True,
        )
        report = Assessment(
            indicator=indicator, dataset=batch, row_index=7, methodology_confirmed=True,
            mapping_notes="MOCKED example with deliberately aligned definitions; not official evidence.",
            status=State.DEMO, is_mocked=True,
        )
        yield label, report, Decimal(tolerance)
