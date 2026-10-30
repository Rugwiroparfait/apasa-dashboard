from django.urls import path
from . import views

app_name = "planning"
urlpatterns = [
    path("ai/ask/", views.question_create, name="dashboard-question"),
    path("ai/", views.ai_status, name="ai-status"),
    path("comparisons/<int:pk>/ask/", views.question_create, name="question"),
    path("", views.index, name="index"),
    path("evidence/", views.manage, name="manage"),
    path("sources/upload/", views.upload, name="upload"),
    path("sources/existing/", views.import_existing, name="existing"),
    path("sources/template.csv", views.csv_template, name="template"),
    path("targets/new/", views.indicator_create, name="indicator-create"),
    path("comparisons/new/", views.assessment_create, name="assessment-create"),
    path("comparisons/<int:pk>/", views.assessment_detail, name="assessment"),
    path("records/<str:kind>/<int:pk>/", views.record, name="record"),
    path("review/<str:kind>/<int:pk>/", views.review, name="review"),
    path("comparisons/<int:pk>/model/", views.model_create, name="model-create"),
    path("models/<int:pk>/scenario/", views.scenario_run, name="scenario"),
    path("scenarios/<int:pk>/", views.scenario_detail, name="scenario-detail"),
    path("comparisons/<int:pk>/brief/", views.brief_create, name="brief-create"),
    path("comparisons/<int:pk>/followup/", views.followup_save, name="followup"),
    path(
        "comparisons/<int:pk>/followup/<int:task_pk>/",
        views.followup_save,
        name="followup-update",
    ),
]
