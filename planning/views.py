"""Human-readable planning screens; all writes are authenticated and CSRF protected."""

import csv
import io
import json
from functools import wraps
from django.contrib import messages
from django.core.exceptions import (
    PermissionDenied,
    ObjectDoesNotExist,
    ImproperlyConfigured,
)
from django.db import transaction, DatabaseError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe
from django.conf import settings
from django.utils import timezone
from . import forms
from .models import (
    State,
    SourceBatch,
    IndicatorVersion,
    Assessment,
    ForecastModel,
    ScenarioRun,
    ActionBrief,
    AIExplanation,
    FollowUp,
    ReviewEvent,
)
from .services import trusted, transition, RECORDS
from .validation import validate_csv, fingerprint
from .calculations import comparison, report_result, fit_forecast, scenario
from .briefs import draft_brief, explain_evidence
from evidence.charts import bar_chart


def planner(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not trusted(request.user):
            raise PermissionDenied(
                "Your account needs a national policymaker or district agriculture officer role."
            )
        return view(request, *args, **kwargs)

    return wrapped


def visible(model, user):
    query = (
        Q(status__in=[State.APPROVED, State.DEMO])
        | Q(created_by=user)
        | Q(reviewed_by=user)
    )
    if trusted(user):
        query |= Q(status=State.SUBMITTED)
    return model.objects.filter(query)


def destination(kind, pk):
    return reverse(
        "planning:assessment" if kind == "assessment" else "planning:record",
        kwargs={"pk": pk} if kind == "assessment" else {"kind": kind, "pk": pk},
    )


@require_safe
def index(request):
    return render(
        request,
        "planning/index.html",
        {
            "reports": visible(Assessment, request.user).select_related(
                "indicator", "dataset"
            ),
            "due_tasks": FollowUp.objects.filter(
                owner=request.user, due_date__lte=timezone.localdate()
            )
            .exclude(status="completed")
            .select_related("assessment__indicator"),
            "pending": (
                sum(
                    m.objects.filter(status=State.SUBMITTED)
                    .exclude(created_by=request.user)
                    .count()
                    for m in RECORDS.values()
                )
                if trusted(request.user)
                else 0
            ),
        },
    )


@planner
def manage(request):
    return render(
        request,
        "planning/manage.html",
        {
            "sources": visible(SourceBatch, request.user),
            "indicators": visible(IndicatorVersion, request.user),
            "queue": [
                (kind, record)
                for kind, model in RECORDS.items()
                for record in model.objects.filter(status=State.SUBMITTED).exclude(
                    created_by=request.user
                )
            ],
            "review_form": forms.ReviewForm(),
        },
    )


@planner
def upload(request):
    form = forms.SourceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        raw = form.cleaned_data["file"].read(2 * 1024 * 1024 + 1)
        rows, errors = validate_csv(raw)
        mocked = any(r["is_mocked"] for r in rows)
        record = SourceBatch.objects.create(
            title=form.cleaned_data["title"],
            source_url=form.cleaned_data["source_url"],
            source_reference=form.cleaned_data["source_reference"],
            methodology=form.cleaned_data["methodology"],
            content_sha256=fingerprint(raw),
            rows=rows,
            errors=errors,
            created_by=request.user,
            is_mocked=mocked,
            status=(
                State.QUARANTINED if errors else State.DEMO if mocked else State.DRAFT
            ),
            supersedes=(
                get_object_or_404(
                    visible(SourceBatch, request.user), pk=request.GET["supersedes"]
                )
                if request.GET.get("supersedes")
                else None
            ),
        )
        messages.info(
            request,
            (
                "The entire upload was quarantined. Correct the listed errors and upload a new version."
                if errors
                else (
                    "Validated. Send this source version for independent review before using it with official targets."
                    if not mocked
                    else "MOCKED source created for demonstration only; it cannot be approved as official evidence."
                )
            ),
        )
        return redirect("planning:record", kind="source", pk=record.pk)
    return render(
        request,
        "planning/form.html",
        {
            "form": form,
            "title": "Add an observation dataset",
            "intro": "Upload aggregate statistics only. Invalid batches are quarantined as a whole. Valid real-data batches require a different person to review them.",
            "upload": True,
        },
    )


@planner
@require_POST
def import_existing(request):
    scope = request.POST.get("scope", "national")
    try:
        if scope == "national":
            from evidence.workbook_data import load_bundle

            bundle = load_bundle(str(settings.PUBLIC_EVIDENCE_ROOT))
            observations = [
                r for r in bundle["observations"] if r["status"] == "observed"
            ]
            rows = [
                dict(
                    measure=r["indicator"],
                    crop=r["crop"],
                    value=r["value"],
                    unit="%" if r["unit"] == "% of farmers" else r["unit"],
                    period=r["period"],
                    geography_code="RW",
                    geography="Rwanda",
                    population=r["population"].split(";")[0],
                    standard_error="",
                    is_mocked=False,
                    source_reference=f"{r['source_workbook']} · {r['source_sheet']}!{r['source_cell']} · SHA-256 {r['source_sha256']}",
                )
                for r in observations
            ]
        elif scope == "district":
            from evidence.repository import district_rows

            labels = {
                "crop_production": "production",
                "average_crop_yield": "yield",
                "cultivated_crop_area": "cultivated_area",
                "harvested_crop_area": "harvested_area",
            }
            rows = [
                dict(
                    measure=labels[r["measure"]],
                    crop=r["display_crop"],
                    value=r["value"],
                    unit=r["unit"],
                    period="2026 Season B",
                    geography_code=r["district_id"],
                    geography=r["district"],
                    population="All farmer types",
                    standard_error="",
                    is_mocked=False,
                    source_reference=f"{r['source_workbook_url']} · {r['worksheet']}!{r['cell_reference']}",
                )
                for r in district_rows(settings.PUBLIC_EVIDENCE_ROOT)
                if r["source_value_status"] in {"numeric", "numeric_zero"}
            ]
        else:
            raise Http404("Unknown source scope")
    except (
        OSError,
        ValueError,
        KeyError,
        DatabaseError,
        ObjectDoesNotExist,
        ImproperlyConfigured,
    ):
        messages.error(
            request,
            "The reviewed source snapshot is unavailable or invalid. Restore the source inputs before registering a new version.",
        )
        return redirect("planning:manage")
    if not rows:
        messages.error(
            request,
            "No numeric source observations are available to register. Missing data were not filled with zero.",
        )
        return redirect("planning:manage")
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    # Existing data goes through exactly the same schema gate; Python bools serialize as True/False.
    raw = text.getvalue().encode()
    validated, errors = validate_csv(raw)
    record = SourceBatch.objects.create(
        title=f"Existing {scope} source snapshot",
        source_url="https://statistics.gov.rw/",
        source_reference="Repository-reviewed public source snapshot; exact release references are retained on every observation.",
        methodology="NISR SAS — verify estimator, definitions and denominators before mapping",
        content_sha256=fingerprint(raw),
        rows=validated,
        errors=errors,
        created_by=request.user,
        status=State.QUARANTINED if errors else State.DRAFT,
    )
    return redirect("planning:record", kind="source", pk=record.pk)


@planner
def indicator_create(request):
    initial = {}
    if request.GET.get("copy"):
        previous = get_object_or_404(
            visible(IndicatorVersion, request.user), pk=request.GET["copy"]
        )
        initial = {
            field: getattr(previous, field) for field in forms.IndicatorForm.Meta.fields
        }
        initial["version"] = previous.version + 1
    form = forms.IndicatorForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.created_by = request.user
        record.status = State.DEMO if record.is_mocked else State.DRAFT
        record.save()
        return redirect("planning:record", kind="indicator", pk=record.pk)
    return render(
        request,
        "planning/form.html",
        {
            "form": form,
            "title": "Register a policy target",
            "intro": "Register one exact target version from an authenticated NST2 or PSTA5 policy source. A separate reviewer must verify it; matching labels alone do not establish comparability.",
        },
    )


@planner
def assessment_create(request):
    values = request.POST if request.method == "POST" else request.GET
    dataset = None
    try:
        dataset = SourceBatch.objects.filter(
            pk=values.get("dataset"), status__in=[State.APPROVED, State.DEMO]
        ).first()
    except (ValueError, TypeError):
        pass
    form = forms.AssessmentForm(
        request.POST or None, initial={"dataset": dataset}, dataset=dataset
    )
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.created_by = request.user
        record.is_mocked = record.dataset.is_mocked or record.indicator.is_mocked
        record.status = State.DEMO if record.is_mocked else State.DRAFT
        record.save()
        return redirect("planning:assessment", pk=record.pk)
    return render(
        request,
        "planning/assessment_form.html",
        {
            "form": form,
            "datasets": SourceBatch.objects.filter(
                status__in=[State.APPROVED, State.DEMO]
            ),
            "dataset": dataset,
        },
    )


@require_safe
def record(request, kind, pk):
    if kind not in RECORDS or kind == "assessment":
        raise Http404("Unknown record type")
    item = get_object_or_404(visible(RECORDS[kind], request.user), pk=pk)
    if kind == "scenario":
        return redirect("planning:scenario-detail", pk=pk)
    fields = []
    for field in item._meta.fields:
        if field.name not in {
            "rows",
            "errors",
            "specification",
            "id",
            "content",
            "answer",
            "ai_metadata",
            "created_by",
            "reviewed_by",
        }:
            value = getattr(item, field.name)
            if value is not None and value != "":
                fields.append(
                    (field.verbose_name.replace("_", " ").capitalize(), value)
                )
    events = ReviewEvent.objects.filter(record_type=kind, record_id=pk).select_related(
        "actor"
    )
    return render(
        request,
        "planning/record.html",
        {
            "item": item,
            "kind": kind,
            "fields": fields,
            "events": events,
            "rows": item.rows[:100] if kind == "source" else [],
            "review_form": forms.ReviewForm(),
            "can_author": item.created_by_id == request.user.pk,
            "can_review": trusted(request.user)
            and item.created_by_id != request.user.pk,
            "model_stats": item.specification if kind == "model" else None,
        },
    )


@planner
@require_POST
def review(request, kind, pk):
    if kind not in RECORDS:
        raise Http404("Unknown review type")
    get_object_or_404(visible(RECORDS[kind], request.user), pk=pk)
    form = forms.ReviewForm(request.POST)
    if form.is_valid():
        try:
            transition(
                kind,
                pk,
                request.user,
                form.cleaned_data["action"],
                form.cleaned_data["notes"],
                form.cleaned_data["verified"],
            )
            messages.success(request, "Review decision recorded in the audit trail.")
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(
            request, "Provide a review action and at least 15 characters of findings."
        )
    return redirect(destination(kind, pk))


@require_safe
def assessment_detail(request, pk):
    item = get_object_or_404(
        visible(Assessment, request.user).select_related("indicator", "dataset"), pk=pk
    )
    result = report_result(item)
    chart = None
    if result["comparable"]:
        points = [
            dict(
                label=label,
                value=str(result[key]),
                unit=result["unit"],
                mocked=result["mocked"],
                source=source,
            )
            for label, key, source in [
                ("Baseline", "baseline", item.indicator.source_reference),
                ("Current", "actual", result["row"]["source_reference"]),
                ("Target", "target", item.indicator.source_reference),
            ]
        ]
        chart = bar_chart(
            "Where we are and where we want to be",
            result["unit"],
            points,
            "Same indicator, population, geography and unit. Source periods are listed in the report.",
        )
    if request.GET.get("download") == "text":
        content, _, _, _ = draft_brief(
            item,
            "Record a responsible owner, review feasible actions with a specialist, and monitor the next comparable observation.",
        )
        response = HttpResponse(
            f"Status: {item.get_status_display()}\n\n" + content,
            content_type="text/plain; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="apasa-comparison-{pk}'
            + (
                "-MOCKED"
                if result["mocked"]
                else "-DRAFT" if item.status != State.APPROVED else ""
            )
            + '.txt"'
        )
        return response
    approved_model = (
        item.forecast_models.filter(
            status__in=[State.APPROVED, State.DEMO], specification__passes=True
        )
        .order_by("-created_at")
        .first()
    )
    return render(
        request,
        "planning/assessment.html",
        {
            "item": item,
            "result": result,
            "chart": chart,
            "model_form": forms.ModelForm(),
            "models": item.forecast_models.all(),
            "approved_model": approved_model,
            "scenario_form": forms.ScenarioForm(
                initial={"years": max(1, min(2, result.get("years_remaining", 2)))}
            ),
            "brief_form": forms.BriefForm(assessment=item),
            "question_form": forms.QuestionForm(assessment=item),
            "explanations": visible(AIExplanation, request.user).filter(
                assessment=item
            ),
            "briefs": visible(ActionBrief, request.user).filter(assessment=item),
            "followups": item.followups.select_related("owner"),
            "can_followup": item.status == State.DEMO
            or (
                item.status == State.APPROVED
                and item.briefs.filter(status=State.APPROVED).exists()
            ),
            "followup_form": forms.FollowUpForm(initial={"owner": request.user}),
            "events": ReviewEvent.objects.filter(
                record_type="assessment", record_id=pk
            ).select_related("actor"),
            "review_form": forms.ReviewForm(),
            "can_author": item.created_by_id == request.user.pk,
            "can_review": trusted(request.user)
            and item.created_by_id != request.user.pk,
        },
    )


@planner
@require_POST
def model_create(request, pk):
    item = get_object_or_404(visible(Assessment, request.user), pk=pk)
    form = forms.ModelForm(request.POST)
    if form.is_valid():
        try:
            spec = fit_forecast(item, form.cleaned_data["acceptable_rmse"])
            model = ForecastModel.objects.create(
                assessment=item,
                created_by=request.user,
                is_mocked=item.is_mocked,
                acceptable_rmse=form.cleaned_data["acceptable_rmse"],
                specification=spec,
                training_sha256=fingerprint(
                    json.dumps(spec["points"], sort_keys=True).encode()
                ),
                status=State.DEMO if item.is_mocked else State.DRAFT,
            )
            return redirect("planning:record", kind="model", pk=model.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Choose a non-negative model-error tolerance.")
    return redirect("planning:assessment", pk=pk)


@planner
@require_POST
def scenario_run(request, pk):
    model = get_object_or_404(
        visible(ForecastModel, request.user).select_related("assessment"), pk=pk
    )
    form = forms.ScenarioForm(request.POST)
    if form.is_valid():
        try:
            output = scenario(
                model, form.cleaned_data["years"], form.cleaned_data["adjustment"]
            )
            run = ScenarioRun.objects.create(
                model=model,
                created_by=request.user,
                is_mocked=model.is_mocked,
                years=form.cleaned_data["years"],
                adjustment=form.cleaned_data["adjustment"],
                output=output,
                status=State.DEMO if model.is_mocked else State.DRAFT,
            )
            return redirect("planning:scenario-detail", pk=run.pk)
        except ValueError as exc:
            form.add_error(None, str(exc))
    return render(request, "planning/scenario.html", {"item": model, "form": form})


@require_safe
def scenario_detail(request, pk):
    run = get_object_or_404(
        visible(ScenarioRun, request.user).select_related(
            "model__assessment__indicator"
        ),
        pk=pk,
    )
    model, output = run.model, run.output
    if request.GET.get("download") == "text":
        text = f"APASA scenario {run.pk} — {run.get_status_display()}\nMOCKED: {run.is_mocked}\nModel: {model.pk}; source comparison: {model.assessment_id}\n"
        text += json.dumps(output, indent=2, sort_keys=True) + "\n" + output["warning"]
        response = HttpResponse(text, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="apasa-scenario-{run.pk}'
            + (
                "-MOCKED"
                if run.is_mocked
                else "-DRAFT" if run.status != State.APPROVED else ""
            )
            + '.txt"'
        )
        return response
    unit = model.assessment.indicator.unit
    points = [
        dict(
            label="Current",
            value=str(report_result(model.assessment)["actual"]),
            unit=unit,
            mocked=model.is_mocked,
            source="Reviewed comparison",
        ),
        dict(
            label="Trend baseline",
            value=str(output["baseline"]),
            unit=unit,
            mocked=model.is_mocked,
            source="Reviewed linear-trend model",
        ),
        dict(
            label="Assumed scenario",
            value=str(output["adjusted"]),
            unit=unit,
            mocked=model.is_mocked,
            source="User-assumed yearly adjustment",
        ),
    ]
    if output.get("at_deadline"):
        points.append(
            dict(
                label="Policy target",
                value=str(model.assessment.indicator.target_value),
                unit=unit,
                mocked=model.is_mocked,
                source=model.assessment.indicator.source_reference,
            )
        )
    chart = bar_chart(
        "Conditional scenario — not a promised result", unit, points, output["warning"]
    )
    return render(
        request,
        "planning/scenario.html",
        {
            "item": model,
            "run": run,
            "output": output,
            "chart": chart,
            "form": forms.ScenarioForm(
                initial={"years": run.years, "adjustment": run.adjustment}
            ),
            "events": ReviewEvent.objects.filter(
                record_type="scenario", record_id=pk
            ).select_related("actor"),
            "can_author": run.created_by_id == request.user.pk,
            "can_review": trusted(request.user)
            and run.created_by_id != request.user.pk,
        },
    )


@planner
@require_POST
def brief_create(request, pk):
    item = get_object_or_404(visible(Assessment, request.user), pk=pk)
    form = forms.BriefForm(request.POST, assessment=item)
    if form.is_valid():
        content, method, notice, metadata = draft_brief(
            item,
            form.cleaned_data["proposed_action"],
            form.cleaned_data["use_ai"],
            form.cleaned_data["scenario"],
            actor=request.user,
        )
        record = ActionBrief.objects.create(
            assessment=item,
            content=content,
            method=method,
            ai_metadata=metadata,
            proposed_action=form.cleaned_data["proposed_action"],
            created_by=request.user,
            is_mocked=item.is_mocked,
            scenario=form.cleaned_data["scenario"],
            status=State.DEMO if item.is_mocked else State.DRAFT,
        )
        if notice:
            messages.info(request, notice)
        return redirect("planning:record", kind="brief", pk=record.pk)
    messages.error(request, "Describe the proposed action in at least 15 characters.")
    return redirect("planning:assessment", pk=pk)


@planner
@require_POST
@transaction.atomic
def followup_save(request, pk, task_pk=None):
    item = get_object_or_404(visible(Assessment, request.user), pk=pk)
    if item.status != State.DEMO and not (
        item.status == State.APPROVED
        and item.briefs.filter(status=State.APPROVED).exists()
    ):
        raise PermissionDenied(
            "Approve the evidence report and action brief before tracking implementation."
        )
    task = get_object_or_404(FollowUp, pk=task_pk, assessment=item) if task_pk else None
    if task and task.owner_id != request.user.pk:
        raise PermissionDenied("Only the responsible person can update this follow-up.")
    previous_task_state = task.status if task else "not_assigned"
    form = forms.FollowUpForm(request.POST, instance=task)
    if form.is_valid():
        record = form.save(commit=False)
        record.assessment = item
        record.save()
        ReviewEvent.objects.create(
            record_type="assessment",
            record_id=pk,
            actor=request.user,
            previous_state=previous_task_state,
            new_state=record.status,
            notes=f"Follow-up {record.pk}: owner {record.owner.username}, due {record.due_date}; {record.action}; outcome: {record.outcome_notes}; reported value: {record.observed_value}; source: {record.outcome_source_url}",
        )
        messages.success(
            request,
            "Follow-up recorded. Reported outcomes do not replace reviewed evidence.",
        )
    else:
        messages.error(
            request, "Check the follow-up fields: " + str(form.errors.as_text())
        )
    return redirect("planning:assessment", pk=pk)


@require_safe
def csv_template(request):
    response = HttpResponse(
        "measure,crop,value,unit,period,geography_code,geography,population,source_reference,standard_error,is_mocked\nproduction,Maize,120000,MT,2026 Season B,RW,Rwanda,All farmer types,MOCKED example only,,true\n",
        content_type="text/csv",
    )
    response["Content-Disposition"] = (
        'attachment; filename="apasa-aggregate-template-MOCKED.csv"'
    )
    return response


@planner
def ai_status(request):
    from .ai import local_status, check_access, AIUnavailable

    status = local_status()
    access = None
    notice = ""
    if request.method == "POST":
        try:
            access = check_access(request.user)
        except AIUnavailable as exc:
            notice = str(exc)
    from .models import AIRequestLog

    logs = AIRequestLog.objects.filter(user=request.user).order_by("-created_at")[:15]
    return render(
        request,
        "planning/ai_status.html",
        {"status": status, "access": access, "notice": notice, "logs": logs},
    )


@planner
@require_POST
def question_create(request, pk):
    item = get_object_or_404(visible(Assessment, request.user), pk=pk)
    form = forms.QuestionForm(request.POST, assessment=item)
    if form.is_valid():
        text, method, notice, metadata = explain_evidence(
            item,
            form.cleaned_data["question"],
            form.cleaned_data["scenario"],
            request.user,
        )
        answer = AIExplanation.objects.create(
            assessment=item,
            scenario=form.cleaned_data["scenario"],
            question=form.cleaned_data["question"],
            answer=text,
            method=method,
            ai_metadata=metadata,
            created_by=request.user,
            is_mocked=item.is_mocked,
            status=State.DEMO if item.is_mocked else State.DRAFT,
        )
        if notice:
            messages.info(request, notice)
        return redirect("planning:record", kind="answer", pk=answer.pk)
    messages.error(
        request,
        "Ask a question of 10–1,500 characters and select only a reviewed scenario.",
    )
    return redirect("planning:assessment", pk=pk)
