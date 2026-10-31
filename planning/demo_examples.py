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


def load_comparison_examples(actor):
    """Explicit, repeatable demo loading; no GET writes or official-data changes.

    The caller must authorize a planning role. Lock the unique target identity
    before loading its source so concurrent POSTs reuse the same demo records.
    """
    from django.db import transaction

    def defaults(record, exclude):
        return {field.name: getattr(record, field.name) for field in record._meta.fields
                if field.name not in exclude | {"id", "created_at", "created_by"}}

    def require_demo(record):
        if not record.is_mocked or record.status != State.DEMO:
            raise ValueError("A reserved demonstration identifier is used by a non-demo record.")

    loaded = []
    with transaction.atomic():
        for label, example, tolerance in examples():
            indicator, _ = IndicatorVersion.objects.get_or_create(
                framework=example.indicator.framework, code=example.indicator.code, version=1,
                defaults=dict(defaults(example.indicator, {"framework", "code", "version"}), created_by=actor),
            )
            indicator = IndicatorVersion.objects.select_for_update().get(pk=indicator.pk)
            require_demo(indicator)
            batch = SourceBatch.objects.filter(title=example.dataset.title).order_by("pk").first()
            if batch is None:
                batch = SourceBatch.objects.create(title=example.dataset.title,
                    **dict(defaults(example.dataset, {"title"}), created_by=actor))
            require_demo(batch)
            if not batch.rows or not all(row.get("is_mocked") is True for row in batch.rows):
                raise ValueError("The demonstration source contains non-demo or missing observations.")
            loaded.append(batch)
    return loaded
