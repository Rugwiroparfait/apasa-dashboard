from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.db import DatabaseError
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .repository import policy_rows
from .curation import registry, crop_options, resolve_crop
from .workbook_data import crop_observations
from .charts import seasonal_charts
from .policy_presentation import presentation, choose_record, note_text


@require_safe
def policy_evidence(request):
    try:
        rows = policy_rows(settings.PUBLIC_EVIDENCE_ROOT)
        curated, _, nodes, _, node_aliases = registry()
        indicators = {x["code"]: x for x in curated["indicators"]}
        indicator_aliases = {
            a: x["code"] for x in indicators.values() for a in x["aliases"]
        }
        for row in rows:
            row["indicator_code"] = indicator_aliases[row["indicator_name"]]
    except (
        OSError,
        ValueError,
        KeyError,
        DatabaseError,
        ObjectDoesNotExist,
        ImproperlyConfigured,
    ):
        return render(request, "evidence/policy_unavailable.html", status=503)

    # Validate against the complete registry first. Known but stale dependent
    # choices are then cleared in order, rather than producing impossible menus.
    values = {
        field: request.GET.get(field, "")
        for field in [
            "outcome_output",
            "crop",
            "indicator_name",
            "comparability_status",
        ]
    }
    if values["outcome_output"]:
        value = values["outcome_output"]
        values["outcome_output"] = (
            value if value in nodes else node_aliases.get(value, "INVALID")
        )
    if values["crop"]:
        try:
            values["crop"] = resolve_crop(values["crop"], rows)
        except ValueError:
            raise Http404("Unknown curated crop")
    if values["indicator_name"]:
        value = values["indicator_name"]
        values["indicator_name"] = (
            value if value in indicators else indicator_aliases.get(value, "INVALID")
        )

    matching, filters, cleared = rows, [], []
    definitions = [
        ("outcome_output", "PSTA5 outcome/output", "policy_code"),
        ("crop", "Crop or crop group", "crop_code"),
        ("indicator_name", "Indicator", "indicator_code"),
        ("comparability_status", "Comparability status", "comparability_status"),
    ]
    for field, label, key in definitions:
        present = {r[key] for r in matching}
        global_present = {r[key] for r in rows}
        if field == "outcome_output":
            options = sorted(
                [(code, nodes[code]["name"]) for code in present], key=lambda x: x[1]
            )
        elif field == "crop":
            options = crop_options(matching)
        elif field == "indicator_name":
            options = [
                (code, x["name"]) for code, x in indicators.items() if code in present
            ]
        else:
            options = [
                (s, s)
                for s in ["Context only", "Not currently comparable"]
                if s in present
            ]
        value = values[field]
        if value and value not in global_present:
            raise Http404("Unknown evidence filter")
        if value and value not in dict(options):
            cleared.append(label)
            value = ""
        filters.append(dict(name=field, label=label, value=value, options=options))
        if value:
            matching = [r for r in matching if r[key] == value]

    key = request.GET.get("record", "")
    selected = (
        next((r for r in matching if r["key"] == key), None)
        if key
        else next(iter(matching), None)
    )
    if key and selected is None:
        raise Http404("Indicator is not in the selected evidence list")
    if selected:
        selected = presentation(selected, request.GET.get("mock") == "1")
        try:
            selected["workbook_observations"] = crop_observations(
                settings.PUBLIC_EVIDENCE_ROOT, selected["crop"]
            )
        except (OSError, ValueError, KeyError):
            selected["workbook_observations"] = []
    charts = []
    if selected:
        measure = (
            "yield"
            if "productivity" in selected["indicator_name"].lower()
            else "production"
        )
        charts, _ = seasonal_charts(
            [
                r
                for r in selected.get("workbook_observations", [])
                if r["indicator"] == measure
            ]
        )
    return render(
        request,
        "evidence/policy.html",
        dict(
            charts=charts,
            filters=filters,
            rows=matching,
            selected=selected,
            cleared_filters=cleared,
            default_selection=bool(selected and not key),
        ),
    )


@require_safe
def policy_workspace(request, section):
    try:
        rows = policy_rows(settings.PUBLIC_EVIDENCE_ROOT)
    except (
        OSError,
        ValueError,
        KeyError,
        DatabaseError,
        ObjectDoesNotExist,
        ImproperlyConfigured,
    ):
        return render(request, "evidence/policy_unavailable.html", status=503)
    selected = choose_record(rows, request.GET.get("record", ""))
    if selected is None:
        return render(request, "evidence/policy_unavailable.html", status=503)
    selected = presentation(selected, request.GET.get("mock") == "1")
    try:
        selected["workbook_observations"] = crop_observations(
            settings.PUBLIC_EVIDENCE_ROOT, selected["crop"]
        )
    except (OSError, ValueError, KeyError):
        selected["workbook_observations"] = []
    if section == "note" and request.GET.get("download") == "text":
        response = HttpResponse(
            note_text(selected), content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="apasa-evidence-note'
            + ("-MOCK" if selected["mock"] else "")
            + '.txt"'
        )
        return response
    text = note_text(selected) if section == "note" else ""
    sections = (
        [
            dict(heading=block.splitlines()[0], lines=block.splitlines()[1:])
            for block in text.strip().split("\n\n")[1:]
        ]
        if text
        else []
    )
    charts, _ = seasonal_charts(selected.get("workbook_observations", []))
    return render(
        request,
        "evidence/policy_" + section + ".html",
        dict(selected=selected, charts=charts, note_text=text, note_sections=sections),
    )
