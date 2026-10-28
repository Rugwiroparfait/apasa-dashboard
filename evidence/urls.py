"""Read-only planning and research routes; authentication is enforced by middleware."""

from django.urls import path

from . import views
from .district_views import district_statistics
from .policy_views import policy_evidence, policy_workspace
from .workbook_views import workbook_evidence

app_name = "evidence"
urlpatterns = [
    path("workspace/overview/", views.home, name="home"),
    path("national-policy-evidence/", policy_evidence, name="policy"),
    path(
        "national-policy-evidence/crop/",
        policy_workspace,
        {"section": "crop"},
        name="policy-crop",
    ),
    path(
        "national-policy-evidence/note/",
        policy_workspace,
        {"section": "note"},
        name="policy-note",
    ),
    path("district-crop-statistics/", district_statistics, name="district-statistics"),
    path("workbook-evidence/", workbook_evidence, name="workbooks"),
    path("evidence/maize/", views.pilot, name="pilot"),
    path("evidence/figures/<str:filename>/", views.figure, name="figure"),
    path("evidence/maize/summary.csv", views.summary_download, name="summary"),
]
