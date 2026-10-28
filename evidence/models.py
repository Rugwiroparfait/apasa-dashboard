"""Versioned public evidence only; no microdata or personal identifiers."""

from django.db import models
from django.db.models import Q


class Crop(models.Model):
    code = models.CharField(max_length=80, primary_key=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(
        max_length=16,
        choices=[("individual", "Individual crop"), ("group", "Crop group")],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=["individual", "group"]), name="crop_kind_valid"
            )
        ]


class PolicyNode(models.Model):
    code = models.CharField(max_length=80, primary_key=True)
    name = models.CharField(max_length=300)
    framework_code = models.CharField(max_length=30)
    framework_name = models.CharField(max_length=200)
    name_status = models.CharField(max_length=30)


class DatasetVersion(models.Model):
    fingerprint = models.CharField(max_length=64, primary_key=True)
    slug = models.CharField(max_length=80)
    source_path = models.CharField(max_length=240)
    source_sha256 = models.CharField(max_length=64)
    registry_sha256 = models.CharField(max_length=64)
    transform_version = models.CharField(max_length=40)
    source_label = models.CharField(max_length=200)
    source_urls = models.JSONField(default=list)
    manifest = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(active=True),
                name="one_active_dataset_version",
            )
        ]


class SourceRecord(models.Model):
    dataset = models.ForeignKey(
        DatasetVersion, on_delete=models.PROTECT, related_name="records"
    )
    key = models.CharField(max_length=120)
    crop = models.ForeignKey(Crop, null=True, on_delete=models.PROTECT)
    crop_label_raw = models.TextField()
    crop_mapping_status = models.CharField(max_length=30)
    policy_node = models.ForeignKey(PolicyNode, null=True, on_delete=models.PROTECT)
    policy_label_raw = models.TextField(blank=True)
    original = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "key"], name="unique_source_record"
            )
        ]


class Observation(models.Model):
    record = models.ForeignKey(
        SourceRecord, on_delete=models.CASCADE, related_name="observations"
    )
    key = models.CharField(max_length=80)
    kind = models.CharField(max_length=40)
    measure = models.TextField()
    # Source text is authoritative: no fixed decimal scale can silently round it.
    value_text = models.TextField(blank=True)
    value_state = models.CharField(max_length=40)
    period = models.TextField()
    unit = models.TextField(blank=True)
    geography = models.TextField()
    geography_code = models.CharField(max_length=40, blank=True)
    source_label = models.TextField()
    source_url = models.TextField(blank=True)
    source_reference = models.TextField(blank=True)
    source_crop_label = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["record", "key"], name="unique_record_observation"
            )
        ]
