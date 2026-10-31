# APASA demonstration script

Use this 10–15 minute walkthrough to show both roles. Keep the distinction simple: **Published evidence** uses supplied sources; **Demonstration data** uses invented values. A compact label identifies demo pages; expand **Data origin & details** only when explaining provenance.

## Prepare locally

Use a development database, not a production database. From the repository root:

```bash
npm ci
npm run build
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py provision_accounts --demo
venv/bin/python manage.py seed_planning_demo
venv/bin/python manage.py generate_observation_demo
venv/bin/python manage.py runserver 127.0.0.1:8000
```

Account/demo seeding requires development mode. Existing passwords are preserved; use your existing credentials if accounts already exist. The development provisioner’s account details are in the repository README. Do not copy development credentials or database files to production. Demo generation/seeding is never a deployment step.

Prepare two browser profiles or sign out between roles. An NVIDIA key is optional. Without one, explain the assistant’s unavailable state; never describe a local template or unavailable response as live AI.

## 1. National policymaker: progress and evidence (4 minutes)

1. Sign in as the national policymaker. **Goal progress** opens by default. If there are no comparable reviewed observations, a labelled demonstration appears automatically. Say: “This example shows how the workflow works; it is not a measured Rwanda policy result.”
2. To create a comparison with an empty planning database, choose **Compare a goal → Use demonstration datasets**. This explicit action loads only the two synthetic example datasets and their matching targets. Dataset selection then loads observations automatically. Select the matching target and observation, enter mapping notes, confirm the definitions, and choose **Check comparison**. No records load merely by opening the page.
3. Open a demonstration comparison. Read its **current value and reporting period**, target and remaining gap. Different saved comparisons may select different years; do not assume the displayed observation is 2026. Open **View chart**, then **Exact values & sources**, and close with Escape.
4. Use **Overview** for published national observations, then **National Policy**. Expand **Find an indicator or change selection**, select an outcome/output and Maize where available, and inspect an indicator. The selected outcome, indicator, target period and source are visible together.
5. Explain the visible **Context only** or **Not currently comparable** result: a matching crop does not prove that target definitions or periods match. Expand source details and open the evidence note/download.
6. Open **National statistics**. Choose crop production, Maize, and a reporting period. Choices update automatically; dependent menus show available combinations. **All** reporting periods shows the available series, not an annual total. Open a chart and download the selection if useful. Missing values remain unavailable rather than zero.

## 2. District agriculture officer: place, crop and season (4 minutes)

1. Sign in as the district officer. **Local goals** emphasizes local comparisons and follow-ups; open **District evidence**.
2. In **Published evidence**, select City of Kigali → Nyarugenge → Maize. Each selection reloads the available choices. If automatic updates are unavailable, **Apply** still loads the next set of choices; repeat after selecting a district/crop. Select a measure and use **Apply** to open its chart. If the chart script is unavailable, Apply opens the chart and exact values directly on the page. The published extract provides **2026 Season B only**; the selector does not invent other official seasons.
3. Switch to **Demonstration data**. Compatible place/crop selections stay selected. Choose Southern Province → Huye → Maize. Change between **2025 B**, **2026 A** and **2026 B**; the crop and location stay selected and values update automatically.
4. Open **Apply** for the selected measure’s crop-comparison chart. Below the value cards, open the illustrative period-comparison chart. Source tables keep periods and units separate.
5. Optionally demonstrate missing versus zero: Huye → Bush bean → 2026 A has intentionally unavailable yield/production; Nyarugenge → Cassava → 2025 B has illustrative zero yield/production. They remain different states.
6. Expand **Data origin & details** once. Explain that these examples are generated aggregates, not official NISR/MINAGRI statistics or district policy achievements. Switch back to **Published evidence** to return to sourced observations.

## 3. Add an observation dataset (3 minutes)

Open **Manage evidence & review → Add an observation dataset** (`/planning/sources/upload/`). Upload `data/demo/synthetic_rwanda_crop_observations_v1.csv` using:

| Field | Enter |
| --- | --- |
| Dataset name | DEMO — Synthetic Rwanda crop observations (not official) |
| Synthetic demonstration dataset | Checked |
| Publication URL | Leave blank |
| Publication/release | APASA interface demonstration dataset, version 1.0; generated 31 October 2026 |
| Methodology | APASA-SYNTH-DEMO-2026-V1 |
| Data origin | Synthetic illustrative data generated for APASA demonstration; not official NISR or MINAGRI statistics. |
| Aggregate-only declaration | Checked |

Click **Save for validation**. Show the demonstration source, origin and original row values. The file has 1,536 aggregate rows for 2019–2026. Annual rows and seasonal rows are distinct; never add both together. Re-uploading identical content/metadata as the same user reuses the demo record. It cannot be approved as official evidence and does not populate official charts.

For a new comparison, use only a synthetic target with matching geography, crop, measure, unit, population, methodology and period type. The two seeded examples have a different methodology from this upload CSV; do not combine them. Exact recipes and metadata are in [the demo README](../data/demo/README.md).

## 4. Assistant and close (1 minute)

On a selected policy or district chart, open the assistant in the lower-left corner and ask: “Explain this chart and its source limitations.” Point to its selected-page context and source references. A real configured request shows a thinking state. Provider failures and rate limits show an error/retry state; no answer is invented. Do not retry repeatedly during a live demonstration.

Close with the distinction: APASA helps inspect evidence and plan follow-up; progress requires a reviewed, compatible target/observation pairing. Demo labels and source details remain available without interrupting navigation.
