"""Public chart context, signed by the server; never accept browser-supplied facts."""

import hashlib
import json
from django.core import signing
from django.http import JsonResponse
from .ai import AIUnavailable
from .briefs import explain_dashboard

SALT = "apasa-dashboard-context-v1"
PAGES = {
    "home": "Planning overview",
    "workbooks": "National statistics",
    "district-statistics": "District statistics",
    "policy": "National policy evidence",
    "policy-crop": "Crop evidence",
    "policy-note": "Evidence note",
}
NOTES = "Published observations are not policy progress or causal effects. Seasons remain separate; no annual totals. Missing values are unavailable, not zero. Policy references and context-only/not-comparable actuals are not authenticated target comparisons."


def snapshot(context):
    request = context["request"]
    route = request.resolver_match
    data = {
        "page": PAGES.get(route.url_name, "Reviewed planning workspace"),
        "filters": {},
        "charts": [],
        "notes": NOTES,
    }
    for item in context.get("filters", []):
        data["filters"][item["label"]] = str(item["value"])[:200]
    for key in (
        "crop",
        "crop_name",
        "period",
        "province_name",
        "district_name",
        "chart_measure",
    ):
        if context.get(key):
            data["filters"][key] = str(context[key])[:200]
    # Only the read-only published evidence routes may contribute general chart context.
    if route.namespace == "evidence" and route.url_name in PAGES:
        charts = (
            [context["grouped_chart"]]
            if context.get("grouped_chart")
            else context.get("charts", [])
        )
        if context.get("chart"):
            charts = [context["chart"]]
        for chart in charts:
            data["charts"].append(
                dict(
                    title=chart["title"],
                    unit=chart["unit"],
                    description=chart["description"],
                    values=[
                        dict(
                            label=str(b["label"]),
                            value=str(b["value"]) if b["available"] else None,
                            state=b["state"],
                            source=b.get("source", ""),
                        )
                        for b in chart["bars"]
                    ],
                )
            )
        selected = context.get("selected")
        if isinstance(selected, dict):
            data["policy_reference"] = {
                k: str(selected.get(k, ""))[:500]
                for k in (
                    "indicator_name",
                    "crop",
                    "comparability_status",
                    "baseline_value",
                    "baseline_year",
                    "target_value",
                    "target_year",
                    "target_unit",
                    "policy_source_url",
                    "policy_page",
                    "official_actual_value",
                    "actual_year_or_period",
                    "actual_unit",
                    "source_url",
                    "page_or_table",
                    "reason",
                )
            }
            data["mocked"] = bool(selected.get("mock"))
            data[
                "notes"
            ] += " Selected policy references are contextual; do not infer target attainment."
    # Session history is keyed by exact canonical context; changing filters starts a new thread.
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    if len(raw.encode()) > 17000:
        data["charts"] = []
        data[
            "notes"
        ] += " This view is too broad for a bounded assistant request. Narrow the filters."
    key = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:24]
    token = signing.dumps(
        {"user": request.user.pk, "context": data, "key": key}, salt=SALT, compress=True
    )
    return data, key, token


def dashboard_question(request):
    question = request.POST.get("question", "").strip()
    if not 10 <= len(question) <= 1500:
        return JsonResponse(
            {"error": "Ask a question of 10–1,500 characters."}, status=400
        )
    try:
        if len(request.POST.get("context_token", "")) > 32000:
            raise signing.BadSignature()
        payload = signing.loads(
            request.POST.get("context_token", ""), salt=SALT, max_age=1800
        )
        if payload["user"] != request.user.pk:
            raise signing.BadSignature()
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        return JsonResponse(
            {
                "error": "This dashboard context expired or is invalid. Refresh the page and try again."
            },
            status=400,
        )
    context = payload["context"]
    if not context.get("charts") and not context.get("policy_reference"):
        return JsonResponse(
            {
                "error": "No published chart context is available here. Select evidence or use the existing reviewed comparison question form."
            },
            status=422,
        )
    if context.get("mocked") or any(
        v["state"] == "MOCKED" for c in context["charts"] for v in c["values"]
    ):
        return JsonResponse(
            {
                "error": "This chart includes mocked previews. Turn them off before asking about published evidence."
            },
            status=422,
        )
    threads = request.session.get("dashboard_assistant_threads", {})
    key = payload["key"]
    history = threads.get(key, [])
    try:
        answer, metadata = explain_dashboard(context, question, history, request.user)
    except AIUnavailable as exc:
        return JsonResponse({"error": str(exc), "unavailable": True}, status=503)
    history = (history + [{"question": question, "answer": answer}])[-4:]
    threads.pop(key, None)
    threads[key] = history
    request.session["dashboard_assistant_threads"] = dict(list(threads.items())[-3:])
    return JsonResponse(
        {
            "answer": answer,
            "method": "ai",
            "label": "AI explanation · unreviewed",
            "sources": list(
                dict.fromkeys(
                    v["source"] for c in context["charts"] for v in c["values"]
                )
            ),
            "history": history,
        }
    )
