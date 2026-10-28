"""Workflow transitions are enforced on the server, under database locks."""

import json
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from .models import (
    State,
    ReviewEvent,
    SourceBatch,
    IndicatorVersion,
    Assessment,
    ForecastModel,
    ScenarioRun,
    ActionBrief,
    AIExplanation,
)
from .calculations import comparison, ENGINE_VERSION
from .validation import fingerprint

RECORDS = {
    "source": SourceBatch,
    "indicator": IndicatorVersion,
    "assessment": Assessment,
    "model": ForecastModel,
    "scenario": ScenarioRun,
    "brief": ActionBrief,
    "answer": AIExplanation,
}


def trusted(user):
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or user.groups.filter(
                name__in=["National policymaker", "District agriculture officer"]
            ).exists()
        )
    )


def record_event(record, user, previous, notes):
    kind = next(k for k, v in RECORDS.items() if isinstance(record, v))
    ReviewEvent.objects.create(
        record_type=kind,
        record_id=record.pk,
        actor=user,
        previous_state=previous,
        new_state=record.status,
        notes=notes,
    )


@transaction.atomic
def transition(kind, pk, user, action, notes, verified=False):
    if not trusted(user):
        raise PermissionDenied("A planning role is required to review evidence.")
    record = RECORDS[kind].objects.select_for_update().get(pk=pk)
    previous = record.status
    if record.is_mocked or previous == State.DEMO:
        raise ValueError(
            "Mocked examples cannot be approved as official publications. Use a separate real-data version."
        )
    if action == "submit":
        if record.created_by_id != user.pk:
            raise PermissionDenied("Only the author can submit this record.")
        if previous not in {State.DRAFT, State.CHANGES}:
            raise ValueError("Only drafts or returned records can be submitted.")
        if isinstance(record, SourceBatch) and (record.errors or not record.rows):
            raise ValueError("Correct and re-upload the quarantined data first.")
        record.status = State.SUBMITTED
    elif action in {"approve", "return"}:
        if previous != State.SUBMITTED:
            raise ValueError("This record is not awaiting review.")
        if record.created_by_id == user.pk:
            raise PermissionDenied(
                "A different person must review and approve your work."
            )
        if action == "approve":
            if not verified:
                raise ValueError(
                    "Confirm the source and comparability checks before approval."
                )
            if isinstance(record, ForecastModel):
                if not record.specification.get("passes"):
                    raise ValueError(
                        "The model did not meet the held-out validation requirements."
                    )
                if record.assessment.status != State.APPROVED:
                    raise ValueError(
                        "Approve the evidence comparison before approving its forecast model."
                    )
                payload = json.dumps(
                    record.specification["points"], sort_keys=True
                ).encode()
                if fingerprint(payload) != record.training_sha256:
                    raise ValueError("Model training evidence changed.")
            if isinstance(record, Assessment):
                # Evidence-gap reports may be published with explanations; calculations remain gated.
                if (
                    record.dataset.status != State.APPROVED
                    or record.indicator.status != State.APPROVED
                ):
                    raise ValueError(
                        "Approve both the source dataset and policy target before publishing a comparison."
                    )
            if isinstance(record, ScenarioRun) and (
                record.model.status != State.APPROVED
                or record.model.assessment.status != State.APPROVED
            ):
                raise ValueError(
                    "Approve the model and evidence comparison before approving its scenario."
                )
            if (
                isinstance(record, (ActionBrief, AIExplanation))
                and record.scenario_id
                and record.scenario.status != State.APPROVED
            ):
                raise ValueError(
                    "Approve the selected scenario before publishing advice based on it."
                )
            if (
                isinstance(record, (ActionBrief, AIExplanation))
                and record.assessment.status != State.APPROVED
            ):
                raise ValueError(
                    "Publish the underlying comparison before approving its advice."
                )
            if isinstance(record, Assessment):
                record.calculation_version = ENGINE_VERSION
                record.result_snapshot = comparison(record)
            record.status = State.APPROVED
        else:
            record.status = State.CHANGES
        record.reviewed_by = user
        record.reviewed_at = timezone.now()
        record.review_notes = notes
    else:
        raise ValueError("Unknown review action.")
    record.save()
    record_event(record, user, previous, notes)
    return record
