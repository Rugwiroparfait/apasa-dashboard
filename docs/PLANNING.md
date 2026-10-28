# Reviewed planning workflow

The diagrams are implemented as a database-backed workflow at `/planning/`, linked from both evidence journeys and the overview. Both national policymakers and district officers see the same clear summary: **current value, target, remaining need, and next steps**. Advanced methods, model details, source tables and review history are expandable.

## Try it locally

```bash
python manage.py migrate --noinput
python manage.py provision_accounts --demo
python manage.py seed_planning_demo
```

The last two commands are development-only. Sign in, open **Compare & plan**, and choose the national or district mocked demonstration. Each has invented annual observations and a mocked model so the complete comparison and scenario interface can be exercised. No demonstration target, observation, model or advice can be approved as official evidence. Seeding is repeatable and does not reset passwords or create official approvals.

The national demonstration has an invented current value of 124,000 MT, a target of 150,000 MT, and a remaining gap of 26,000 MT over two yearly reporting steps. This illustrates the interface only; it is not a real PSTA5 target or Rwanda production series.

## Official evidence and publication

1. **Register a source version.** Use an existing national/district source snapshot, or upload a UTF-8 aggregate CSV. No farmer or household records are accepted by the schema. Record the publication URL, exact table/release and methodology identifier.
2. **Validate or quarantine.** Check schema, numeric values, known measure/unit combinations, periods, geography codes, missing fields and duplicate dimensions. One invalid row quarantines the entire batch. Store the original byte hash and errors; do not store the rejected raw upload. Correct it externally and upload a new version linked to the prior batch.
3. **Register an authenticated policy target.** Supply the NST2/PSTA5 code or explicitly local identifier, version, source URL/page, measure, crop, population, geography, unit, methodology, baseline, deadline and direction of improvement. The uploaded register is not automatically treated as authenticated policy: its apparent targets reproduce some observations and have unresolved provenance.
4. **Get another user's review.** Authors submit sources and targets; a different trusted planning user verifies citations, definitions, denominators, methods, units, periods and geography. A review note and verification confirmation are mandatory for approval. Both default planning roles can peer-review the other user's submissions; authors, including superusers, cannot approve their own work.
5. **Create a mapping/comparison.** Select an approved target, dataset and current observation. Check methods and explain the mapping. Exact measure, crop, population and geography code must match. Only explicitly supported unit conversions are allowed. Annual, fiscal and seasonal observations are not silently equated.
6. **Inspect the result.** Eligible comparisons calculate the gap, progress and needed pace. Incompatible evidence displays the available observation and the precise missing requirements; it receives no target-gap calculation. A source-backed evidence-gap report can still be reviewed and published.
7. **Review and publish.** A different user approves the comparison. Approval freezes the reviewed result and calculation specification (`comparison-v1`) in a publication snapshot. Drafts are visible to their author; submitted items become visible to peer reviewers. Approved reports are readable by authenticated users. Inputs are immutable through the interface; corrections create new source/target/mapping versions.
8. **Prepare and approve advice.** Describe a proposed action to investigate. Local factual template drafting always works; optional AI can draft wording from approved aggregate evidence. AI cannot calculate new facts or approve publication. A different person must approve the action brief after the underlying report is approved.
9. **Track implementation and feedback.** After report and advice approval, assign an owner, due date and action. Owners update status and source-linked reported outcomes. Due/overdue actions appear on their planning overview. Reported outcomes do not overwrite canonical observations or establish an intervention effect. State changes, findings, owners, dates, reported values and sources are retained in the audit trail.

The registry's methodology identifier is a declaration backed by human source review, not an automated proof of equivalence. Merely entering matching labels cannot authenticate a source or establish statistical comparability.

## CSV contract

Required columns:

```text
measure,crop,value,unit,period,geography_code,geography,population,source_reference
```

Optional columns: `standard_error,is_mocked`.

Supported units are `MT`, `Ha`, `Kg/Ha`, `MT/ha`, `%`, `count`, and `RWF`. Known measure/unit combinations are checked: production uses MT; yield uses Kg/Ha or MT/ha; improved-seed/inorganic-fertilizer adoption uses %; cultivated/harvested area uses Ha. Other stable measure codes require a reviewed target definition.

Periods are `2026`, `2026 Season B` (A/B/C), or `2026/27`. Seasons remain separate; fiscal years must have consecutive year labels. Geography codes are exact source identifiers (`RW` for the national snapshot; district codes such as `11` for district snapshots). Values must be finite, non-negative and at most 10^15; percentages are bounded at 100. Missing actuals must be omitted rather than zero-filled. Duplicate observations are rejected, including duplicate yield observations expressed in equivalent units.

Uploads are limited to 2 MB and 5,000 observations, with at most 30 row errors shown. Unknown columns, including personal-data fields, are rejected. `is_mocked=true` marks the entire valid batch as demonstration-only. The downloadable template contains one invented row and is named `-MOCKED.csv`.

Existing source snapshots preserve exact source references and numeric observations; they do not invent standard errors, target equivalences, or missing historical records. They start as drafts and must be reviewed. National adoption units `% of farmers` are explicitly represented as `%` plus the SSF/LSF population label; source provenance is retained.

## Models, simulation and expert review

A historical regression can be shown after three comparable observations, clearly labelled exploratory. A forecasting candidate requires at least six observations in the same measure/crop/population/geography/period class. The two most recent observations are held out. The trend model must satisfy a domain-defined maximum RMSE and perform no worse than carrying the latest training value forward. All training points, backtest metrics, coefficients, residual variance and hashes are stored.

Passing numerical validation is not approval. A different reviewer must approve the model and underlying comparison before real scenarios can run. The supported forecast horizon is at most two yearly reporting steps, matching the held-out validation window. Longer horizons need a new validation design rather than an unchecked extrapolation.

Every scenario is saved with its assumptions and conditional outputs. Baseline prediction intervals and a three-point assumption sensitivity table are shown. A separate person must review the scenario before it can be selected in an action brief. Changing assumptions creates a new saved scenario; it does not mutate a reviewed scenario. Scenario downloads identify draft/approved/mocked state.

The model is an observational linear trend, **not a causal intervention model**. Additional annual change is a user-specified illustration; it is not an estimated effect of providing fertilizer, seeds, irrigation or extension. The app suggests which constraints and sources to investigate, not agronomic prescriptions or guaranteed production effects. See [statistical methods](STATISTICS.md).

## AI configuration and fallback

Set `chat_openai_key` securely on your computer, or use `APASA_AI_API_KEY`/`OPENAI_API_KEY`. The ignored local `.env` is loaded without overriding injected process variables. Set `APASA_AI_MODEL=gpt-5.4-mini`, with the same model in `APASA_AI_ALLOWED_MODELS`. The connector uses the Responses API over HTTPS at `api.openai.com` and the inherited proxy/trust settings. No key is committed or requested in chat. The cloud environment draft contains an optional personal secret requirement and the exact API hostname; reviewing/publishing environment settings is separate from deploying the application.

AI use is opt-in per brief. It sends only approved aggregate facts, citations, the proposed action and any approved scenario. Mocked demonstrations may be explained by AI only after an explicit request, always with a server-applied MOCKED banner and no possibility of official approval. Unapproved reports cannot be sent for AI wording. Without a key, or if the provider fails, the app preserves the factual template and says no AI wording was obtained.

Generated text remains explicitly unapproved, and unchanged canonical input facts are appended. Output is rendered as escaped plain text. Reviewers must check generated wording and reject unsupported claims. No automated publication, email, external notification or implementation action is performed. Live provider access requires operator-supplied credentials; tests use a mocked provider response and verify the fallback and approval restrictions.

## Existing dashboards and updates

The existing national/district charts remain release-based public source views. Newly uploaded data appears in versioned planning reports after approval; it does not silently replace the original CSVs or workbook bundle. New releases and corrected targets require explicit source registration and peer review. Monitoring is manual through versioned sources and follow-up tasks; no external source scraper or automatic evidence promotion is installed.


### Evidence Q&A and API limits

The report's **Ask the evidence assistant** form can answer questions using the selected comparison and an optional reviewed scenario. Answers are stored as unapproved explanations with unchanged canonical input facts, prompt version, input hash, selected model and reported token usage. They follow the same independent review and mock-publication restrictions as briefs. No generated text becomes an authoritative calculation.

`/planning/ai/` shows only safe configuration/status and the requesting user's recent request metadata. Merely opening the page does not call OpenAI. An explicit model-access check reads `/v1/models`; visibility does not establish generation quota, credits or free billing. `manage.py check_ai` is local-only; `--check-access` reads model visibility; `--generate` explicitly sends one small test.

The default `gpt-5.4-mini` matches the user's shown API Free tier model listing. Locally enforced rolling limits are 8 requests/minute, 45 requests/24 hours, and a conservative 80,000-token/minute input/output budget. Each generation permits at most 1,200 output tokens with low reasoning effort. Reservations are serialized in the database per credential fingerprint/model and shared by both app users. Raw keys, prompts and provider error bodies are not stored in the quota log. Provider failures still count conservatively; there are no automatic retries, model upgrades or billing changes. Other applications' API traffic is outside this ledger.

Credential errors, insufficient quota, rate limits, unavailable models, invalid/incomplete output and network failures return explicit notices and preserve local factual drafting. Provider error messages that may echo a key are never displayed. Redirects are disabled so an Authorization header is not forwarded to a different endpoint. Normal proxy and CA trust remain enabled.

Provider protocol, success/error handling, token/request budgets, mock labels, fallback and user interfaces are tested with mocked HTTP responses. A live generation call has not been made in this cloud machine because the user's key is on their own computer. Do not interpret a mocked test as proof of live model entitlement or credits.
