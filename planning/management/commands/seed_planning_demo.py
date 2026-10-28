"""Populate invented end-to-end examples, always outside official publication."""

import json
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from planning.models import (
    SourceBatch,
    IndicatorVersion,
    Assessment,
    ForecastModel,
    State,
)
from planning.calculations import fit_forecast
from planning.validation import fingerprint


class Command(BaseCommand):
    help = "Create two explicitly MOCKED planning examples; development only and repeatable."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError("Demonstration seeding is disabled in production.")
        for label, geo, values, target, tolerance in [
            (
                "National demonstration",
                "RW",
                [100000, 104000, 108000, 109000, 113000, 117000, 120000, 124000],
                150000,
                20000,
            ),
            (
                "District demonstration",
                "11",
                [400, 440, 480, 510, 550, 580, 620, 660],
                900,
                200,
            ),
        ]:
            rows = [
                dict(
                    measure="production",
                    crop="Maize",
                    unit="MT",
                    period=str(2019 + i),
                    geography_code=geo,
                    geography=(
                        "Rwanda (MOCKED)" if geo == "RW" else "Nyarugenge (MOCKED)"
                    ),
                    population="All farmer types",
                    value=str(value),
                    standard_error="",
                    is_mocked=True,
                    source_reference="MOCKED invented example; no official source",
                )
                for i, value in enumerate(values)
            ]
            raw = json.dumps(rows, sort_keys=True).encode()
            batch, _ = SourceBatch.objects.get_or_create(
                title="MOCKED · " + label,
                defaults=dict(
                    source_url="https://example.invalid/mocked",
                    source_reference="Invented annual observations, demonstration only.",
                    methodology="MOCKED consistent annual example",
                    content_sha256=fingerprint(raw),
                    rows=rows,
                    status=State.DEMO,
                    is_mocked=True,
                ),
            )
            indicator, _ = IndicatorVersion.objects.get_or_create(
                framework="PSTA5",
                code="DEMO-" + geo,
                version=1,
                defaults=dict(
                    name="MOCKED · " + label + " maize production",
                    measure="production",
                    crop="Maize",
                    unit="MT",
                    population="All farmer types",
                    geography_code=geo,
                    geography=rows[0]["geography"],
                    methodology=batch.methodology,
                    baseline_period="2019",
                    baseline_value=Decimal(values[0]),
                    target_period="2028",
                    target_value=Decimal(target),
                    direction="higher",
                    source_url="https://example.invalid/mocked-target",
                    source_reference="MOCKED target, not an authenticated PSTA5 goal.",
                    status=State.DEMO,
                    is_mocked=True,
                ),
            )
            report, _ = Assessment.objects.get_or_create(
                indicator=indicator,
                dataset=batch,
                row_index=7,
                defaults=dict(
                    mapping_notes="MOCKED example with deliberately aligned definitions; not official evidence.",
                    methodology_confirmed=True,
                    is_mocked=True,
                    status=State.DEMO,
                ),
            )
            spec = fit_forecast(report, Decimal(tolerance))
            ForecastModel.objects.get_or_create(
                assessment=report,
                status=State.DEMO,
                defaults=dict(
                    is_mocked=True,
                    acceptable_rmse=Decimal(tolerance),
                    specification=spec,
                    training_sha256=fingerprint(
                        json.dumps(spec["points"], sort_keys=True).encode()
                    ),
                ),
            )
            self.stdout.write(
                f"{label}: MOCKED report {report.pk} prepared; no official data or approvals created."
            )
