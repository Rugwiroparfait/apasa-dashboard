"""Versioned planning inputs, independent review, publication and follow-up."""

from django.conf import settings
from django.db import models


class State(models.TextChoices):
    DRAFT = "draft", "Draft"
    QUARANTINED = "quarantined", "Needs data corrections"
    SUBMITTED = "submitted", "Waiting for review"
    APPROVED = "approved", "Approved"
    CHANGES = "changes", "Changes requested"
    DEMO = "demo", "MOCKED demonstration"


class ReviewedRecord(models.Model):
    status = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_mocked = models.BooleanField(default=False)

    class Meta:
        abstract = True


class SourceBatch(ReviewedRecord):
    title = models.CharField(max_length=200)
    source_url = models.URLField(max_length=1000, blank=True)
    source_reference = models.TextField()
    methodology = models.CharField(max_length=200)
    content_sha256 = models.CharField(max_length=64)
    rows = models.JSONField(default=list)
    errors = models.JSONField(default=list)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class IndicatorVersion(ReviewedRecord):
    framework = models.CharField(
        max_length=10, choices=[("NST2", "NST2"), ("PSTA5", "PSTA5")]
    )
    code = models.CharField(max_length=80)
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=240)
    measure = models.SlugField(max_length=80)
    crop = models.CharField(max_length=120)
    unit = models.CharField(max_length=30)
    population = models.CharField(max_length=160)
    geography_code = models.CharField(max_length=40)
    geography = models.CharField(max_length=160)
    methodology = models.CharField(max_length=200)
    baseline_period = models.CharField(max_length=40)
    baseline_value = models.DecimalField(max_digits=24, decimal_places=8)
    target_period = models.CharField(max_length=40)
    target_value = models.DecimalField(max_digits=24, decimal_places=8)
    direction = models.CharField(
        max_length=10,
        choices=[("higher", "Higher is better"), ("lower", "Lower is better")],
        default="higher",
    )
    source_url = models.URLField(max_length=1000)
    source_reference = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "code", "version"],
                name="planning_indicator_version_unique",
            )
        ]
        ordering = ["framework", "code", "-version"]

    def __str__(self):
        return f"{self.framework} {self.code} v{self.version}: {self.name}"


class Assessment(ReviewedRecord):
    indicator = models.ForeignKey(IndicatorVersion, on_delete=models.PROTECT)
    dataset = models.ForeignKey(SourceBatch, on_delete=models.PROTECT)
    row_index = models.PositiveIntegerField()
    mapping_notes = models.TextField()
    calculation_version = models.CharField(max_length=40, default="comparison-v1")
    result_snapshot = models.JSONField(default=dict)
    methodology_confirmed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.indicator.name


class ForecastModel(ReviewedRecord):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="forecast_models"
    )
    acceptable_rmse = models.DecimalField(max_digits=24, decimal_places=8)
    specification = models.JSONField(default=dict)
    training_sha256 = models.CharField(max_length=64)

    def __str__(self):
        return f"Trend model for {self.assessment.indicator.name}"


class ScenarioRun(ReviewedRecord):
    model = models.ForeignKey(
        ForecastModel, on_delete=models.PROTECT, related_name="scenarios"
    )
    years = models.PositiveIntegerField()
    adjustment = models.FloatField()
    output = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.model.assessment.indicator.name} · {self.years} steps · {self.adjustment:+g}%/year · #{self.pk}"


class ActionBrief(ReviewedRecord):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="briefs"
    )
    scenario = models.ForeignKey(
        ScenarioRun, null=True, blank=True, on_delete=models.PROTECT
    )
    ai_metadata = models.JSONField(default=dict)
    content = models.TextField()
    method = models.CharField(max_length=40, default="template")
    proposed_action = models.TextField()

    def __str__(self):
        return f"Action brief for {self.assessment.indicator.name}"


class FollowUp(models.Model):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="followups"
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.TextField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("planned", "Planned"),
            ("active", "In progress"),
            ("completed", "Completed"),
        ],
        default="planned",
    )
    outcome_notes = models.TextField(blank=True)
    outcome_source_url = models.URLField(max_length=1000, blank=True)
    observed_value = models.DecimalField(
        max_digits=24, decimal_places=8, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def overdue(self):
        from django.utils import timezone

        return self.status != "completed" and self.due_date < timezone.localdate()


class ReviewEvent(models.Model):
    record_type = models.CharField(max_length=30)
    record_id = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    previous_state = models.CharField(max_length=20)
    new_state = models.CharField(max_length=20)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class AIExplanation(ReviewedRecord):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="explanations"
    )
    scenario = models.ForeignKey(
        ScenarioRun, null=True, blank=True, on_delete=models.PROTECT
    )
    question = models.TextField()
    answer = models.TextField()
    method = models.CharField(max_length=30, default="template")
    ai_metadata = models.JSONField(default=dict)

    def __str__(self):
        return f"Evidence explanation for {self.assessment.indicator.name}"


class AIQuotaLedger(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    touch = models.PositiveIntegerField(default=0)


class AIRequestLog(models.Model):
    ledger = models.ForeignKey(AIQuotaLedger, on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT
    )
    model = models.CharField(max_length=120)
    operation = models.CharField(max_length=30)
    estimated_tokens = models.PositiveIntegerField(default=0)
    usage = models.JSONField(default=dict)
    status = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
