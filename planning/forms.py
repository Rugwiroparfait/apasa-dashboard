from django import forms
from .models import (
    SourceBatch,
    IndicatorVersion,
    Assessment,
    FollowUp,
    ScenarioRun,
    State,
)
from .validation import period_key, number, UNITS, MEASURE_UNITS


class SourceForm(forms.Form):
    title = forms.CharField(max_length=200, label="Dataset name")
    synthetic_demo = forms.BooleanField(required=False, label="Synthetic demonstration dataset — not official statistics", help_text="Check for invented illustrative data. It can never be approved as official evidence; every CSV row must have is_mocked=true.")
    source_url = forms.URLField(max_length=1000, required=False, label="Publication or source URL", help_text="Required for real evidence. Leave blank for synthetic demonstrations; do not invent a citation.")
    origin = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 2}), label="Data origin", help_text="Required for synthetic demonstrations. Explain who generated the illustrative data and that it is not official statistics.")
    source_reference = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Publication, table and release/version",
    )
    methodology = forms.CharField(
        max_length=200,
        label="Methodology identifier",
        help_text="Use the same reviewed identifier as the policy target when methods and denominators truly match.",
    )
    file = forms.FileField(label="Aggregate observations (UTF-8 CSV)")
    aggregate_only = forms.BooleanField(
        label="This file contains aggregate observations only, not individual farmer, household or person-level records."
    )

    def clean(self):
        data = super().clean()
        if data.get("synthetic_demo"):
            if not data.get("origin", "").strip():
                self.add_error("origin", "Describe the synthetic data origin; do not supply an invented publication URL.")
        elif not data.get("source_url"):
            self.add_error("source_url", "A publication or source URL is required for real evidence.")
        return data

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 2 * 1024 * 1024:
            raise forms.ValidationError("The file exceeds 2 MB.")
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Choose a CSV file.")
        return upload


class IndicatorForm(forms.ModelForm):
    source_url = forms.URLField(required=False, max_length=1000, label="Policy publication URL", help_text="Required for a real policy target. Leave blank for an invented demonstration target and describe its origin below.")
    source_reference = forms.CharField(
        max_length=5000, widget=forms.Textarea(attrs={"rows": 3})
    )
    unit = forms.ChoiceField(choices=[(x, x) for x in sorted(UNITS)])

    class Meta:
        model = IndicatorVersion
        fields = [
            "framework",
            "code",
            "version",
            "name",
            "measure",
            "crop",
            "unit",
            "population",
            "geography_code",
            "geography",
            "methodology",
            "baseline_period",
            "baseline_value",
            "target_period",
            "target_value",
            "direction",
            "source_url",
            "source_reference",
            "is_mocked",
        ]
        widgets = {"source_reference": forms.Textarea(attrs={"rows": 2})}
        labels = {
            "is_mocked": "This is a MOCKED demonstration target, not an official policy target."
        }
        help_texts = {
            "code": "Use the verified official code; local codes must be explicitly identified as local.",
            "measure": "Match the observation code, for example production, yield or improved_seeds.",
            "source_reference": "For real targets, cite the official document, page/table, approval and period. For synthetic targets, describe the invented origin and state that it is not official.",
            "geography_code": "RW for national Rwanda, or the exact district code in the selected dataset.",
            "baseline_period": "Example: 2024 Season B, 2024 or 2024/25.",
            "methodology": "A shared identifier is valid only after a human verifies definitions, denominators and coverage.",
        }

    def clean(self):
        data = super().clean()
        if not data.get("is_mocked") and not data.get("source_url"):
            self.add_error("source_url", "A policy publication URL is required for a real target.")
        try:
            a = period_key(data.get("baseline_period", ""))
            b = period_key(data.get("target_period", ""))
            if a[0] != b[0] or a[1] > b[1]:
                raise ValueError(
                    "Baseline and target must use the same reporting period type, with baseline before target."
                )
            if (
                data.get("measure") in MEASURE_UNITS
                and data.get("unit") not in MEASURE_UNITS[data["measure"]]
            ):
                raise ValueError("The target unit does not describe this measure.")
            for field in ["baseline_value", "target_value"]:
                value = number(data.get(field), field.replace("_", " "))
                if data.get("unit") == "%" and value > 100:
                    raise ValueError(
                        "Percentage targets and baselines cannot exceed 100."
                    )
            if (
                data.get("direction") == "higher"
                and data["target_value"] < data["baseline_value"]
            ):
                raise ValueError(
                    "A higher-is-better target cannot be below its baseline."
                )
            if (
                data.get("direction") == "lower"
                and data["target_value"] > data["baseline_value"]
            ):
                raise ValueError(
                    "A lower-is-better target cannot be above its baseline."
                )
        except (ValueError, TypeError) as exc:
            raise forms.ValidationError(str(exc))
        return data


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            "indicator",
            "dataset",
            "row_index",
            "mapping_notes",
            "methodology_confirmed",
        ]
        labels = {
            "indicator": "Policy target",
            "dataset": "Current evidence dataset",
            "row_index": "Observation",
            "mapping_notes": "Why these definitions and methods match",
            "methodology_confirmed": "I checked the original sources: methods, denominators, scope and periods are comparable.",
        }
        widgets = {"mapping_notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        dataset = kwargs.pop("dataset", None)
        super().__init__(*args, **kwargs)
        self.fields["indicator"].queryset = IndicatorVersion.objects.filter(
            status__in=[State.APPROVED, State.DEMO]
        )
        self.fields["dataset"].queryset = SourceBatch.objects.filter(
            status__in=[State.APPROVED, State.DEMO]
        )
        choices = []
        if dataset:
            for index, row in enumerate(dataset.rows):
                choices.append(
                    (
                        index,
                        f"{row['crop']} · {row['measure']} · {row['period']} · {row['geography']} · {row['population']} · {row['value']} {row['unit']}",
                    )
                )
        self.fields["row_index"] = forms.TypedChoiceField(
            coerce=int, choices=choices, label="Current observation"
        )


class ReviewForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            ("submit", "Send for review"),
            ("approve", "Approve for publication"),
            ("return", "Request corrections"),
        ]
    )
    notes = forms.CharField(
        min_length=15,
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Review findings or correction instructions",
    )
    verified = forms.BooleanField(
        required=False,
        label="I verified source authority, definitions, methods, units, periods, geography and any uncertainty claims.",
    )


class ModelForm(forms.Form):
    acceptable_rmse = forms.DecimalField(
        min_value=0,
        max_value=10**15,
        label="Maximum acceptable held-out error (same unit as the target)",
        help_text="A domain reviewer must justify this tolerance. Two recent observations are withheld during testing.",
    )


class ScenarioForm(forms.Form):
    years = forms.IntegerField(
        min_value=1,
        max_value=2,
        initial=2,
        label="Yearly reporting steps ahead",
        help_text="The held-out test validates a maximum two-step horizon.",
    )
    adjustment = forms.FloatField(
        min_value=-50,
        max_value=100,
        initial=0,
        label="Assumed additional yearly change (%)",
        help_text="Illustrative assumption, not an estimated effect of an intervention.",
    )


class BriefForm(forms.Form):
    scenario = forms.ModelChoiceField(
        queryset=ScenarioRun.objects.none(),
        required=False,
        label="Optional reviewed scenario",
    )

    def __init__(self, *args, **kwargs):
        assessment = kwargs.pop("assessment", None)
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["scenario"].queryset = ScenarioRun.objects.filter(
                model__assessment=assessment, status__in=[State.APPROVED, State.DEMO]
            )

    proposed_action = forms.CharField(
        min_length=15,
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Proposed action to investigate",
        help_text="Describe a feasible action for expert review. The app cannot infer intervention effectiveness from aggregate statistics.",
    )
    use_ai = forms.BooleanField(
        required=False,
        help_text="Sends approved aggregate facts, citations and your proposed action to the configured NVIDIA service. Leave off to draft locally.",
        label="Use the configured AI service to draft wording (if available); human approval is always required.",
    )


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = [
            "owner",
            "action",
            "due_date",
            "status",
            "outcome_notes",
            "outcome_source_url",
            "observed_value",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "action": forms.Textarea(attrs={"rows": 2}),
            "outcome_notes": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "observed_value": "Optional follow-up report only. This does not replace a reviewed source observation or establish an intervention effect."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        from django.db.models import Q

        self.fields["owner"].queryset = (
            get_user_model()
            .objects.filter(is_active=True)
            .filter(
                Q(is_superuser=True)
                | Q(
                    groups__name__in=[
                        "National policymaker",
                        "District agriculture officer",
                    ]
                )
            )
            .distinct()
        )

    def clean(self):
        data = super().clean()
        if data.get("observed_value") is not None:
            if data["observed_value"] < 0:
                raise forms.ValidationError("Observed values must not be negative.")
            if not data.get("outcome_source_url"):
                raise forms.ValidationError(
                    "Attach a source URL for an observed follow-up value."
                )
        if data.get("status") == "completed" and not data.get("outcome_notes"):
            raise forms.ValidationError(
                "Record an outcome note before marking an action completed."
            )
        return data


class QuestionForm(BriefForm):
    question = forms.CharField(
        min_length=10,
        max_length=1500,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="What would you like explained?",
        help_text="For example: What does this gap mean? Which information is missing before choosing an intervention?",
    )
    proposed_action = None
    use_ai = None
