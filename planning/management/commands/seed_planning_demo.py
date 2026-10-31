"""Populate invented end-to-end examples, always outside official publication."""

import json
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
        from planning.demo_examples import examples

        for label, example, tolerance in examples():
            def defaults(record, exclude):
                return {field.name: getattr(record, field.name) for field in record._meta.fields
                        if field.name not in exclude | {"id", "created_at"}}

            batch, _ = SourceBatch.objects.get_or_create(
                title=example.dataset.title,
                defaults=defaults(example.dataset, {"title"}),
            )
            self.require_demo(batch)
            indicator, _ = IndicatorVersion.objects.get_or_create(
                framework=example.indicator.framework, code=example.indicator.code, version=1,
                defaults=defaults(example.indicator, {"framework", "code", "version"}),
            )
            self.require_demo(indicator)
            report, _ = Assessment.objects.get_or_create(
                indicator=indicator, dataset=batch, row_index=7,
                defaults=defaults(example, {"indicator", "dataset", "row_index"}),
            )
            self.require_demo(report)
            spec = fit_forecast(report, tolerance)
            model, _ = ForecastModel.objects.get_or_create(
                assessment=report,
                status=State.DEMO,
                defaults=dict(
                    is_mocked=True,
                    acceptable_rmse=tolerance,
                    specification=spec,
                    training_sha256=fingerprint(
                        json.dumps(spec["points"], sort_keys=True).encode()
                    ),
                ),
            )
            self.require_demo(model)
            self.stdout.write(
                f"{label}: MOCKED report {report.pk} prepared; no official data or approvals created."
            )

    @staticmethod
    def require_demo(record):
        if not record.is_mocked or record.status != State.DEMO:
            raise CommandError("A demo identifier collides with non-demo data. No records were changed.")
