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
                dict(question=x.question, answer=x.answer)
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
    status = local_status()
    return dict(
        request=request,
        context=data,
        context_token=token,
        assistant_history=history,
        assistant_endpoint=endpoint,
        assistant_allowed=allowed,
        assistant_configured=status["configured"],
        assistant_is_report=isinstance(item, Assessment),
    )
