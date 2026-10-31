from django import template
from django.urls import reverse
from planning.dashboard_assistant import snapshot
from planning.ai import local_status
from planning.services import trusted
from planning.models import Assessment, State

register = template.Library()


@register.inclusion_tag("evidence/assistant_panel.html", takes_context=True)
def workspace_assistant(context):
    request = context["request"]
    data, key, token = snapshot(context)
    history = request.session.get("dashboard_assistant_threads", {}).get(key, [])
    endpoint = reverse("planning:dashboard-question")
    allowed = bool(data["charts"] or data.get("policy_reference")) and trusted(
        request.user
    )
    if data.get("mocked") and not data.get("demonstration"):
        allowed = False
    item = context.get("item")
    if isinstance(item, Assessment):
        allowed = item.status in {State.APPROVED, State.DEMO} and trusted(request.user)
        data["page"] = "Reviewed comparison · " + item.indicator.name
        data["filters"] = {
            "crop": item.indicator.crop,
            "target period": item.indicator.target_period,
            "status": item.get_status_display(),
        }
        endpoint = reverse("planning:question", args=[item.pk])
        history = (
            [
                dict(
                    question=x.question,
                    answer=x.answer,
                    url=reverse("planning:record", kwargs={"kind": "answer", "pk": x.pk}),
                )
                for x in reversed(
                    list(
                        item.explanations.filter(created_by=request.user).order_by(
                            "-created_at"
                        )[:4]
                    )
                )
            ]
            if hasattr(item, "explanations")
            else []
        )
    # Display context is independent of signed evidence facts. Do not show empty labels.
    fields = []
    labels = {
        "crop_name": "Crop", "crop": "Crop", "period": "Reporting period",
        "province_name": "Province", "district_name": "District",
        "chart_measure": "Measure", "population": "Coverage", "target period": "Target period", "status": "Status",
    }
    for name, value in data.get("filters", {}).items():
        if value is not None and str(value).strip() not in {"", "None"}:
            label = labels.get(name, name.replace("_", " ").capitalize())
            fields.append((label, str(value).strip()))
    indicator = data.get("policy_reference", {}).get("indicator_name")
    if indicator and str(indicator).strip() not in {"", "None"}:
        fields.append(("Indicator", str(indicator).strip()))
    policy_fields = [
        (name.replace("_", " ").capitalize(), str(value).strip())
        for name, value in data.get("policy_reference", {}).items()
        if value is not None and str(value).strip() not in {"", "None"}
    ]
    sources = list(dict.fromkeys(
        value["source"]
        for chart in data.get("charts", [])
        for value in chart["values"] if value.get("source")
    ))
    history = [dict(turn, sources=sources) for turn in history]
    status = local_status()
    return dict(
        request=request,
        context=data,
        context_token=token,
        assistant_history=history,
        assistant_context_page=data.get("page") or "General APASA question",
        assistant_context_fields=fields,
        assistant_policy_fields=policy_fields,
        assistant_enabled=allowed and status["configured"],
        assistant_endpoint=endpoint,
        assistant_allowed=allowed,
        assistant_configured=status["configured"],
        assistant_is_report=isinstance(item, Assessment),
        assistant_demo=bool(data.get("mocked") or getattr(item, "is_mocked", False)),
    )
