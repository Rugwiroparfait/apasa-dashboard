# Statistical specification — comparison-v1

## Eligibility first

Calculations require reviewed source and target versions, an explicit methodology confirmation, and matching measure, crop, population, geography code and methodology identifier. Only exact units or Kg/Ha ↔ MT/ha conversion (×0.001 or ×1000, including standard errors) are supported. Seasonal A/B/C, annual and fiscal series stay separate. The selected current observation must fall between the baseline and target reporting years and use the same period class.

Human review authenticates policy provenance and checks survey definitions/coverage. These metadata gates cannot by themselves prove source validity or estimator equivalence. Mocked and official inputs are not combined into an official comparison. Unsupported inputs produce reasons, not invented statistics.

## Gap, progress and needed pace

Let B be the baseline, A the current observation, T the target, n the number of yearly reporting steps until the deadline, and d = +1 when higher is better or −1 when lower is better.

- Signed gap: d × (T − A).
- Remaining need: G = max(0, d × (T − A)).
- Progress from baseline: 100 × d × (A − B) / [d × (T − B)], when the denominator is positive. This can be below 0% or above 100%; it is not current divided by target. Equal baseline and target means progress is undefined.
- Relative change needed: 100 × (T − A) / A for an unmet target with A > 0; zero additional change when already met. It is undefined at A = 0.
- Average yearly change needed: d × G / n for n > 0. No yearly pace is calculated at the target deadline. A met target has zero additional need.
- Constant compound rate needed: 100 × [(T/A)^(1/n) − 1] for an unmet target with A > 0 and n > 0. A zero target has the limiting −100% rate; this does not imply a feasible intervention path.

Percentage-indicator gaps and linear yearly changes are **percentage points**. Moving from 60% to 80% needs 20 percentage points, or a 33.33% relative increase from the current value. These quantities are not interchangeable.

For a lower-is-better loss rate with baseline 20%, current 12% and target 10%, the remaining gap is 2 percentage points and progress is 80%. Reaching it over two yearly steps requires an average change of −1 percentage point per year. This describes the need, not an intervention's effectiveness.

Reporting steps are years within the same seasonal/fiscal class. A 2026 Season B observation and 2028 Season B target are two yearly steps apart, not six seasonal observations. No A/B/C sums or fiscal alignment are inferred.

## Sampling uncertainty

When the source explicitly provides a non-negative standard error s for the selected observation, show the approximate interval A ± 1.96s. This is a normal approximation, not an automatically survey-design-correct interval. Bound it at zero, and at 100 for percentages. Policy targets are treated as stated fixed goals.

For higher-is-better goals, the remaining-gap interval is [max(0,T−upper), max(0,T−lower)]. For lower-is-better goals, it is [max(0,lower−T), max(0,upper−T)]. Without a source standard error, no sampling interval, sample size, synthetic variance or target-attainment probability is supplied.

## Historical regression

At least three distinct comparable yearly observations are needed. Use unweighted ordinary least squares y = intercept + slope × year. Display the slope, a two-sided 95% Student-t interval with n−2 degrees of freedom, R², p-value in the stored calculation output, and residual RMSE sqrt(SSE/(n−2)). Constant series receive finite fallback diagnostics rather than NaN output.

This assumes suitable error behavior and comparable annual observations. Temporal association is not causality; aggregate published estimates are not individual observations or a survey-design sample. Repeated-estimate covariance and source survey weights are not reconstructed. Small histories produce weak diagnostics and potentially very wide intervals. Regression is exploratory until the separate forecast-validation and review gates are satisfied.

## Forecast validation

Require at least six eligible observations, with unique years and no future points beyond the selected current observation. Hold out the two most recent observations. Fit only the earlier observations for the backtest. Compute held-out RMSE and MAE. Compare with a carry-forward baseline using the last training observation. Accept numerical validation only if RMSE is within the explicit reviewer-justified tolerance and no worse than the carry-forward RMSE. For percentage series, absolute prediction errors/RMSE are percentage points.

After the backtest, refit the same OLS specification to all currently available eligible observations for future conditional predictions. Store all points, train/test split, error metrics, coefficients, residual variance, Sxx, last year and training hash. Source changes invalidate the model. Independent human approval is mandatory. The supported horizon is at most two yearly steps, matching the validation window; no claim of validated longer-term forecasting is made.

For a future year x*, the baseline is a + b×x*. The conditional 95% prediction interval uses:

```text
prediction ± t(0.975, n−2) × sqrt(residual_variance × [1 + 1/n + (x*−mean_year)^2/Sxx])
```

The interval describes model residual uncertainty conditional on the OLS assumptions. It is not a probability of achieving a policy target and does not include all structural, policy, climate, survey-method or intervention uncertainty. Predictions are bounded at zero and percentages at 100; boundary truncation does not repair a misspecified model.

## Assumption scenarios and sensitivity

For an assumed additional annual change r over h steps, adjusted value = baseline forecast × (1+r/100)^h. The permitted assumption range is −50% to +100%; this is a UI bound, not an evidence-based plausible range. Show sensitivity at r−5, r and r+5 percentage points, clipped to those UI bounds. The baseline interval does not cover uncertainty about these user assumptions or their intervention effects.

When the scenario year equals the target deadline, show its conditional remaining gap alongside the baseline-model gap. Otherwise do not present a future scenario as a deadline comparison. Scenario periods retain their annual/seasonal/fiscal label. Save the assumptions/output as a versioned record and require separate review before advice uses it.

## Publication, reproducibility and interpretation

`Assessment.result_snapshot` freezes reviewed calculations under `comparison-v1` on approval. Source/target versions and saved scenario outputs have no in-place editing endpoint. Corrections create new versions. Review events record the author/reviewer boundary, decisions and findings; follow-up updates preserve reported values and source URLs without promoting them to canonical evidence.

SciPy performs regression and Student-t calculations; dependency versions are pinned in `requirements.lock`. Calculations use Decimal for target-gap arithmetic and double-precision floating point for regression/projection. Exact input strings remain in source records; displayed summaries are rounded. No automatic district ranking, national aggregation, intervention benefit, cost effectiveness, farmer eligibility decision or causal estimate is produced.
