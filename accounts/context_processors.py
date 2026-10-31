"""Presentation roles; authorization remains in the planning services."""

def workspace_role(request):
    if not request.user.is_authenticated:
        return {}
    groups = set(request.user.groups.values_list("name", flat=True))
    district = "District agriculture officer" in groups and "National policymaker" not in groups and not request.user.is_superuser
    return {"is_district_workspace": district, "workspace_role_label": "District agriculture officer" if district else "National policymaker" if request.user.is_superuser or "National policymaker" in groups else "Evidence workspace"}
