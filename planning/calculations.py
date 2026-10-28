"""Descriptive comparisons and explicitly validated trend projections; no causal claims."""

from decimal import Decimal
import math
from scipy import stats
from .validation import period_key, number
from .models import State

ENGINE_VERSION = "comparison-v1"


def report_result(assessment):
    if assessment.status == State.APPROVED and assessment.result_snapshot:
        return assessment.result_snapshot
    return comparison(assessment)


CONVERSIONS = {
    ("Kg/Ha", "MT/ha"): Decimal("0.001"),
    ("MT/ha", "Kg/Ha"): Decimal("1000"),
}


def unit_factor(source, target):
    if source == target:
        return Decimal(1)
    return CONVERSIONS.get((source, target))


def comparison(assessment):
    indicator, dataset = assessment.indicator, assessment.dataset
    reasons = []
    if assessment.calculation_version != ENGINE_VERSION:
        reasons.append(
            "This comparison uses an older calculation specification; create and review a new comparison version."
        )
    demo = assessment.is_mocked or indicator.is_mocked or dataset.is_mocked
    if dataset.status not in {State.APPROVED, State.DEMO}:
        reasons.append("The observation dataset has not passed independent review.")
    if indicator.status not in {State.APPROVED, State.DEMO}:
        reasons.append(
            "The target and its policy citation have not passed independent review."
        )
    if demo and not (
        indicator.is_mocked and dataset.is_mocked and assessment.is_mocked
    ):
        reasons.append("Mocked and official inputs cannot be mixed in a comparison.")
    try:
        row = dataset.rows[assessment.row_index]
    except (IndexError, TypeError):
        return {
            "comparable": False,
            "reasons": ["Choose a valid observation."],
            "mocked": demo,
        }
    for field, label in [
        ("measure", "measure definition"),
        ("crop", "crop or crop group"),
        ("population", "farmer population"),
        ("geography_code", "geography"),
    ]:
        if row[field] != getattr(indicator, field):
            reasons.append(f"The {label} does not match the target definition.")
    if (
        dataset.methodology != indicator.methodology
        or not assessment.methodology_confirmed
    ):
        reasons.append(
            "Verify matching survey methods and denominators, and record the mapping review."
        )
    factor = unit_factor(row["unit"], indicator.unit)
    if factor is None:
        reasons.append(
            f"Units differ ({row['unit']} and {indicator.unit}); no reviewed conversion is supported."
        )
    try:
        actual_period = period_key(row["period"])
        target_period = period_key(indicator.target_period)
        baseline_period = period_key(indicator.baseline_period)
        if not actual_period[0] == target_period[0] == baseline_period[0]:
            reasons.append(
                "Reporting periods differ: seasons A/B/C, annual years and fiscal years must remain separate."
            )
        if not baseline_period[1] <= actual_period[1] <= target_period[1]:
            reasons.append(
                "The observation must be between the policy baseline and target deadline."
            )
    except ValueError as exc:
        reasons.append(str(exc))
    if reasons:
        return {"comparable": False, "reasons": reasons, "mocked": demo, "row": row}
    actual = number(row["value"], "Observed value") * factor
    baseline, target = indicator.baseline_value, indicator.target_value
    sign = Decimal(1) if indicator.direction == "higher" else Decimal(-1)
    signed_gap = (target - actual) * sign
    remaining = max(Decimal(0), signed_gap)
    years = target_period[1] - actual_period[1]
    distance = (target - baseline) * sign
    progress = (actual - baseline) * sign / distance * 100 if distance > 0 else None
    result = {
        "comparable": True,
        "reasons": [],
        "mocked": demo,
        "row": row,
        "unit": indicator.unit,
        "actual": float(actual),
        "baseline": float(baseline),
        "target": float(target),
        "gap": float(remaining),
        "signed_gap": float(signed_gap),
        "met": signed_gap <= 0,
        "gap_label": "percentage points" if indicator.unit == "%" else indicator.unit,
        "relative_change": (
            float((target - actual) / actual * 100)
            if actual > 0 and remaining > 0
            else 0.0 if actual > 0 else None
        ),
        "target_gap_percent": (
            float(remaining / abs(target) * 100) if target != 0 else None
        ),
        "progress": float(progress) if progress is not None else None,
        "visual_progress": (
            float(max(0, min(100, progress))) if progress is not None else None
        ),
        "years_remaining": years,
        "annual_change": (
            float(sign * remaining / years)
            if years > 0 and remaining > 0
            else 0.0 if years > 0 else None
        ),
        "required_rate": (
            (
                math.expm1(math.log(float(target / actual)) / years) * 100
                if target > 0
                else -100.0
            )
            if actual > 0 and years > 0 and remaining > 0
            else None
        ),
        "conversion": (
            f"{row['unit']} × {factor} = {indicator.unit}"
            if factor != 1
            else "No unit conversion"
        ),
        "sampling_interval": None,
    }
    if row.get("standard_error"):
        se = number(row["standard_error"], "Standard error") * factor
        lower = max(Decimal(0), actual - Decimal("1.96") * se)
        upper = actual + Decimal("1.96") * se
        if indicator.unit == "%":
            upper = min(Decimal(100), upper)
        result["sampling_interval"] = {
            "lower": float(lower),
            "upper": float(upper),
            "gap_lower": float(
                max(0, (target - upper) * sign if sign > 0 else (lower - target))
            ),
            "gap_upper": float(
                max(0, (target - lower) * sign if sign > 0 else (upper - target))
            ),
            "label": "Approximate 95% sampling interval, using the supplied standard error and a normal approximation.",
        }
    history = history_for(assessment)
    result["history"] = history
    result["trend"] = trend_statistics(history) if len(history) >= 3 else None
    result["next_steps"] = [
        (
            "The target is met in this observation. Verify continued performance in the next comparable release."
            if result["met"]
            else f"Close a gap of {result['gap']:,.2f} {result['gap_label']}; use this as a planning need, not a promised intervention effect."
        ),
        (
            f"There are {years} comparable yearly reporting steps to the target deadline."
            if years
            else "The target deadline is this reporting period; a future growth rate is not calculated."
        ),
        "Choose a responsible person and due date, check feasible actions with an agronomist or policy specialist, and attach evidence before approving advice.",
        "Record the next published observation and review the gap again. Scenario assumptions do not establish causality.",
    ]
    if indicator.measure in {"production", "yield"}:
        result["next_steps"].insert(
            2,
            "Review harvested area and yield separately to locate the constraint before choosing a production intervention.",
        )
    elif indicator.measure in {"improved_seeds", "inorganic_fertilizer"}:
        result["next_steps"].insert(
            2,
            "Verify the farmer denominator, access constraints and local agronomic advice before proposing an input intervention.",
        )
    return result


def history_for(assessment):
    indicator = assessment.indicator
    selected = assessment.dataset.rows[assessment.row_index]
    kind, current = period_key(selected["period"])
    points = []
    for row in assessment.dataset.rows:
        if any(
            row[k] != getattr(indicator, k)
            for k in ["measure", "crop", "population", "geography_code"]
        ):
            continue
        factor = unit_factor(row["unit"], indicator.unit)
        if factor is None:
            continue
        period = period_key(row["period"])
        if period[0] != kind or period[1] > current:
            continue
        points.append(
            {
                "year": period[1],
                "period": row["period"],
                "value": float(number(row["value"], "History value") * factor),
                "source": row["source_reference"],
            }
        )
    return sorted(points, key=lambda p: p["year"])


def trend_statistics(points):
    xs = [p["year"] for p in points]
    ys = [p["value"] for p in points]
    fit = stats.linregress(xs, ys)
    critical = float(stats.t.ppf(0.975, len(xs) - 2))
    residuals = [y - (fit.intercept + fit.slope * x) for x, y in zip(xs, ys)]
    return {
        "n": len(xs),
        "slope": float(fit.slope),
        "slope_lower": float(fit.slope - critical * fit.stderr),
        "slope_upper": float(fit.slope + critical * fit.stderr),
        "r_squared": float(fit.rvalue**2) if math.isfinite(fit.rvalue) else 0.0,
        "p_value": float(fit.pvalue) if math.isfinite(fit.pvalue) else 1.0,
        "residual_rmse": math.sqrt(sum(r * r for r in residuals) / (len(xs) - 2)),
        "warning": "Exploratory unweighted linear association across comparable reporting years; not an intervention effect, a survey-design estimate or a validated forecast.",
    }


def fit_forecast(assessment, acceptable_rmse):
    result = comparison(assessment)
    if not result["comparable"]:
        raise ValueError("Resolve comparison requirements before fitting a model.")
    points = result["history"]
    if len(points) < 6:
        raise ValueError(
            f"At least 6 comparable yearly observations are needed, including 2 held-out observations; only {len(points)} are available."
        )
    if len({p["year"] for p in points}) != len(points):
        raise ValueError("Duplicate years cannot be fitted.")
    train, test = points[:-2], points[-2:]
    fit = stats.linregress([p["year"] for p in train], [p["value"] for p in train])
    errors = [p["value"] - (fit.intercept + fit.slope * p["year"]) for p in test]
    rmse = math.sqrt(sum(v * v for v in errors) / len(errors))
    naive = math.sqrt(
        sum((p["value"] - train[-1]["value"]) ** 2 for p in test) / len(test)
    )
    full = stats.linregress([p["year"] for p in points], [p["value"] for p in points])
    residual_variance = sum(
        (p["value"] - full.intercept - full.slope * p["year"]) ** 2 for p in points
    ) / (len(points) - 2)
    mean = sum(p["year"] for p in points) / len(points)
    return {
        "engine_version": ENGINE_VERSION,
        "model": "OLS linear trend; observational, not causal",
        "n": len(points),
        "train_n": len(train),
        "test_n": 2,
        "holdout_years": [p["year"] for p in test],
        "holdout_rmse": rmse,
        "holdout_mae": sum(abs(v) for v in errors) / 2,
        "naive_rmse": naive,
        "acceptable_rmse": float(acceptable_rmse),
        "passes": rmse <= float(acceptable_rmse) and rmse <= naive,
        "slope": float(full.slope),
        "intercept": float(full.intercept),
        "residual_variance": residual_variance,
        "mean_year": mean,
        "sxx": sum((p["year"] - mean) ** 2 for p in points),
        "last_year": points[-1]["year"],
        "points": points,
        "df": len(points) - 2,
        "validated_horizon": 2,
    }


def scenario(model, years, adjustment):
    if model.status not in {State.APPROVED, State.DEMO} or not model.specification.get(
        "passes"
    ):
        raise ValueError(
            "An independently approved model with acceptable held-out error is required."
        )
    if years > model.specification.get("validated_horizon", 2):
        raise ValueError(
            "This model has only been tested for a two-year horizon; longer projections need a new validation design."
        )
    if not 1 <= years <= 20 or not -50 <= adjustment <= 100:
        raise ValueError(
            "Choose 1–20 years and an illustrative annual adjustment between -50% and 100%."
        )
    if not comparison(model.assessment)["comparable"] or (
        not model.is_mocked and model.assessment.status != State.APPROVED
    ):
        raise ValueError(
            "The underlying evidence comparison must remain approved and comparable."
        )
    import json
    from .validation import fingerprint

    if (
        fingerprint(json.dumps(history_for(model.assessment), sort_keys=True).encode())
        != model.training_sha256
    ):
        raise ValueError(
            "Training evidence changed; validate and review a new model version."
        )
    spec = model.specification
    year = spec["last_year"] + years
    projected = spec["intercept"] + spec["slope"] * year
    spread = float(stats.t.ppf(0.975, spec["df"])) * math.sqrt(
        spec["residual_variance"]
        * (1 + 1 / spec["n"] + (year - spec["mean_year"]) ** 2 / spec["sxx"])
    )
    multiplier = (1 + adjustment / 100) ** years
    ceiling = 100.0 if model.assessment.indicator.unit == "%" else float("inf")
    bound = lambda value: min(ceiling, max(0, value))
    sensitivity = [
        {"rate": rate, "value": bound(max(0, projected) * (1 + rate / 100) ** years)}
        for rate in [max(-50, adjustment - 5), adjustment, min(100, adjustment + 5)]
    ]
    kind = period_key(
        model.assessment.dataset.rows[model.assessment.row_index]["period"]
    )[0]
    label = (
        f"{year} {kind}"
        if kind.startswith("Season")
        else f"{year}/{(year+1)%100:02d}" if kind == "fiscal" else str(year)
    )
    target_year = period_key(model.assessment.indicator.target_period)[1]
    sign = 1 if model.assessment.indicator.direction == "higher" else -1
    target = float(model.assessment.indicator.target_value)
    return {
        "year": year,
        "period_label": label,
        "at_deadline": year == target_year,
        "baseline_gap": (
            max(0, (target - bound(projected)) * sign) if year == target_year else None
        ),
        "adjusted_gap": (
            max(0, (target - bound(max(0, projected) * multiplier)) * sign)
            if year == target_year
            else None
        ),
        "baseline": bound(projected),
        "lower": bound(projected - spread),
        "upper": bound(projected + spread),
        "adjusted": bound(max(0, projected) * multiplier),
        "adjustment": adjustment,
        "years": years,
        "sensitivity": sensitivity,
        "mocked": model.is_mocked,
        "warning": "Prediction intervals are conditional on a linear-trend model and its residual assumptions. The adjusted scenario is user-assumed, not a predicted intervention effect; its uncertainty is not covered by the baseline interval. Negative projections are bounded at zero, and percentages at 100.",
    }
