"""APASA local dashboard: explicit public aggregate inputs only."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SUMMARY = ROOT / 'outputs/day3/maize_overall_summary.csv'
REPORT = ROOT / 'docs/day3_findings.md'
FIGURES = {
    'Seed types': 'seed_type_code.png',
    'Improved-seed sources': 'improved_seed_source_code.png',
    'Organic fertilizer use': 's4_q1.png',
    'Inorganic fertilizer use': 's4_q4.png',
    'Inorganic fertilizer type · first response': 's4_q6.png',
    'Pesticide / fungicide use': 's4_q12.png',
    'Anti-erosion activity present': 's4_q19.png',
    'Anti-erosion type · first response': 's4_q19_a1.png',
    'Anti-erosion type · second response': 's4_q19_a2.png',
    'Anti-erosion type · third response': 's4_q19_a3.png',
    'Anti-erosion activities done this season': 's4_q20.png',
}


def load_public_data():
    """Read only the approved overall CSV and published report; no analysis imports."""
    summary = pd.read_csv(SUMMARY).set_index('scenario')
    expected = {'all_reported', 'review_sensitivity_le_5000'}
    if set(summary.index) != expected or len(summary) != 2:
        raise ValueError('Expected the two approved overall scenarios.')
    for _, row in summary.iterrows():
        if row.records != row.harvest_nonmissing + row.harvest_missing:
            raise ValueError('Published summary denominators do not reconcile.')
        if row.harvest_nonmissing != sum(row[k] for k in
                ['reported_zero', 'positive_le_5000', 'flagged_gt_5000', 'negative']):
            raise ValueError('Published harvest categories do not reconcile.')
    rows = []
    # Reuse only these two already published report rows. No local support CSV.
    prefixes = {
        'Seed type (matching maize slot) — 1: Traditional seeds': 'Traditional seeds',
        'Seed type (matching maize slot) — 2: Improved seeds': 'Improved seeds',
    }
    for line in REPORT.read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if cells and cells[0] in prefixes:
            if len(cells) != 7:
                raise ValueError('Published seed comparison table has changed.')
            rows.append({
                'Seed category': prefixes[cells[0]],
                'Plot-season records': int(cells[1].replace(',', '')),
                'Missing harvest': int(cells[2].replace(',', '')),
                'Observed harvest': int(cells[3].replace(',', '')),
                'Observed median reported harvest (kg)': float(cells[4]),
            })
    seed = pd.DataFrame(rows)
    if len(seed) != 2 or seed['Seed category'].nunique() != 2:
        raise ValueError('Expected two published seed comparison rows.')
    if not (seed['Plot-season records'] == seed['Missing harvest'] + seed['Observed harvest']).all():
        raise ValueError('Published seed denominators do not reconcile.')
    return summary, seed


def main():
    st.set_page_config(page_title='APASA | Maize harvest explorer', layout='wide')
    st.markdown('''<style>
    .stApp {background: #f5f7f4;}
    .block-container {max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem;}
    h1,h2,h3 {letter-spacing: -.025em;}
    [data-testid="stCaptionContainer"] p {color: #52665e;}
    [data-testid="stMetric"] {background: white; border: 1px solid #d8e0da;
      border-radius: 12px; padding: 1rem; font-variant-numeric: tabular-nums;}
    [data-testid="stMetricValue"] {color: #163f35;}
    .hero {background: #142f2a; color: white; padding: 2rem; border-radius: 16px;
      border-top: 4px solid #b4ce80; margin-bottom: 1rem;}
    .hero .eyebrow {color: #d4e6b1; font-size: .8rem; letter-spacing: .14em; font-weight: 600;}
    .hero h1 {color: white; font-size: clamp(1.8rem,4vw,2.7rem); margin: .5rem 0; padding: 0;}
    .hero p {color: #e2ede8; max-width: 700px; margin-bottom: 0; line-height: 1.6;}
    @media(max-width: 640px) {.hero {padding: 1.3rem;} .block-container {padding: 1rem;}}
    </style>''', unsafe_allow_html=True)
    try:
        summary, seed = load_public_data()
    except (OSError, ValueError, KeyError, IndexError) as exc:
        st.error(f'The approved public research inputs could not be loaded: {exc}')
        st.stop()
    full = summary.loc['all_reported']
    with st.sidebar:
        st.title('APASA')
        st.caption('2026 NISR Big Data Hackathon')
        st.divider()
        st.markdown('**AHS 2024 · Section 3_4**\n\nMaize · observed plot-seasons')
        st.info('Exploratory, unweighted descriptions. These are not national estimates.')
        st.markdown('**Read this dashboard**\n\n1. Check the analyzed sample.\n2. Compare published seed medians.\n3. Review large-value sensitivity.')
        st.caption('AHS 2024 · Research evidence\n\nNo geographic breakdowns are available in the approved aggregates.')
    st.markdown('''<div class="hero"><div class="eyebrow">APASA / AGRICULTURAL CONDITIONS</div>
    <h1>Maize harvest, in context.</h1>
    <p>A descriptive view of reported harvest quantities across observed maize plot-season records.
    AHS 2024, Section 3_4 · Rwanda.</p></div>''', unsafe_allow_html=True)
    st.caption('RESEARCH EVIDENCE  /  UNWEIGHTED OBSERVED RECORDS  /  NOT NATIONAL ESTIMATES')
    st.subheader('The analyzed sample')
    cols = st.columns(4)
    for col, label, value in zip(cols,
            ['Maize plot-seasons', 'With reported harvest', 'Median reported harvest', 'Mean reported harvest'],
            [f'{int(full.records):,}', f'{int(full.harvest_nonmissing):,}', f'{full.median_kg:.0f} kg', f'{full.mean_kg:.2f} kg']):
        col.metric(label, value)
    st.caption('All-record view: 9,017 distinct plot-seasons; no duplicate plot keys. '
               'Harvest statistics use 8,908 non-missing reports, including reported zeros.')
    with st.container(border=True):
        st.markdown('#### Every record stays visible')
        status = pd.DataFrame({
            'Reported harvest status': ['Positive, up to 5,000 kg', 'Reported zero', 'Above 5,000 kg · review flag', 'Missing harvest'],
            'Plot-season records': [int(full.positive_le_5000), int(full.reported_zero), int(full.flagged_gt_5000), int(full.harvest_missing)],
        })
        st.dataframe(status, hide_index=True, width='stretch')
        st.caption('Denominator: all 9,017 maize plot-seasons. Categories are mutually exclusive; negative quantities: 0.')
        st.warning('215 records report zero harvest. Its meaning is unconfirmed; zero is retained as reported and is distinct from missing.')
    st.divider()
    st.subheader('Seed categories: observed median reported harvest')
    st.markdown('A comparison within the **all-record sample**, using the matching maize crop slot’s seed category.')
    median = 'Observed median reported harvest (kg)'
    chart = alt.Chart(seed).mark_bar(color='#28624f', cornerRadiusEnd=4, size=44).encode(
        x=alt.X(f'{median}:Q', title='Observed median reported harvest (kg)', scale=alt.Scale(domain=[0, 50]), axis=alt.Axis(tickCount=6)),
        y=alt.Y('Seed category:N', title=None, sort=['Traditional seeds', 'Improved seeds'], axis=alt.Axis(labelLimit=200)),
        tooltip=[alt.Tooltip('Seed category:N'), alt.Tooltip(f'{median}:Q', format='.0f'),
                 alt.Tooltip('Plot-season records:Q',format=','), alt.Tooltip('Observed harvest:Q',format=','),
                 alt.Tooltip('Missing harvest:Q',format=',')],
    )
    labels = chart.mark_text(align='left', dx=8, color='#142f2a', fontSize=15).encode(text=alt.Text(f'{median}:Q',format='.0f'))
    st.altair_chart((chart + labels).properties(height=180).configure_axis(labelColor='#42574e', titleColor='#42574e', labelFontSize=12, titleFontSize=12), width='stretch')
    st.dataframe(seed, hide_index=True, width='stretch')
    st.caption('Median denominators: traditional seeds, 3,555 observed harvests out of 3,564 records; '
               'improved seeds, 5,300 out of 5,311. Missing harvests are excluded from medians; reported zeros are included.')
    st.info('These are observational associations. Seed categories do not establish cause and effect; '
            'plot size, crop mix and other differences may explain the contrast. '
            'The 55 “Both” seed records and 87 records with missing seed type are omitted from this focused two-category comparison; '
            'they remain in the overall sample.')
    st.divider()
    st.subheader('How sensitive is the overall summary to large quantities?')
    st.markdown('**Five reports exceed 5,000 kg.** This threshold flags records for review; it does not establish that they are invalid. '
                'The main analysis retains them without capping or alteration.')
    scenarios = {'All records · main analysis': 'all_reported',
                 'Exclude >5,000 kg · sensitivity only': 'review_sensitivity_le_5000'}
    selected = st.radio('Overall summary view', list(scenarios), horizontal=True)
    row = summary.loc[scenarios[selected]]
    with st.container(border=True):
        a,b,c = st.columns(3)
        a.metric('Records in this view', f'{int(row.records):,}')
        b.metric('Median reported harvest', f'{row.median_kg:.0f} kg')
        c.metric('Mean reported harvest', f'{row.mean_kg:.2f} kg')
        st.caption(f'Denominator for harvest statistics: {int(row.harvest_nonmissing):,} non-missing reports. '
                   f'{int(row.harvest_missing):,} missing reports remain in the record count; '
                   f'{int(row.reported_zero):,} zeros remain in the statistics. This control changes only this overall-summary panel.')
    comparison = summary.reset_index().replace({'scenario': {
        'all_reported': 'All records', 'review_sensitivity_le_5000': 'Exclude >5,000 kg'}})
    comparison = comparison[['scenario','records','harvest_nonmissing','harvest_missing','reported_zero','median_kg','mean_kg']]
    comparison.columns = ['View','Records','Observed harvest','Missing harvest','Reported zeros','Median (kg)','Mean (kg)']
    st.dataframe(comparison, hide_index=True, width='stretch', column_config={
        'Mean (kg)': st.column_config.NumberColumn(format='%.2f'),
        'Median (kg)': st.column_config.NumberColumn(format='%.0f'),
    })
    st.caption('Both approved views have a 30 kg median. The mean changes from 92.12 to 86.91 kg. '
               'No seed-specific or practice-specific sensitivity summaries are exposed.')
    with st.expander('Explore the published research practice charts'):
        chosen = st.selectbox('Published comparison', list(FIGURES))
        st.image(str(ROOT/'outputs/day3/figures'/FIGURES[chosen]), width='stretch',
                 caption=f'{chosen} — all-record view. Median dot and Q1–Q3 line in kg; each row shows its own denominator.')
        st.caption('Only previously published images are shown. Groups with fewer than 30 observed harvests are omitted from charts. '
                   'Counts of omitted records are disclosed in their footnotes. The detailed CSV mentioned in image footnotes stays local and is not loaded here. '
                   'Response positions are separate categories, not an exhaustive count of practice users. Mechanical-equipment comparisons are withheld.')
    st.subheader('Methods & limitations')
    st.markdown('''
- **Source and unit:** AHS 2024 Section 3_4 only. Quantities are kilograms per maize crop-slot / plot-season record, not household totals. The reported seasonal total may include quantities remaining to be harvested.
- **Coverage:** 9,017 distinct observed maize plot-seasons. Results are descriptive and unweighted; they are not national estimates. Several plots may belong to one household.
- **Interpretation:** No crop-specific yield or productivity is calculated. Crop-specific area denominators and survey-design inference are not established. No confidence intervals or causal effects are reported.
- **Missingness and unusual values:** Missing harvests are excluded from harvest statistics. Reported zeros remain distinct. Values above 5,000 kg are retained in the main view and excluded only in the labeled sensitivity view.
- **Group boundaries:** Plot practices can apply to other crops on mixed-crop plots. Small or sensitive groups are suppressed or omitted, including complementary suppression where needed. No district or geographic filters are supported.
''')
    with st.expander('Sources and approved aggregate download'):
        st.markdown('Source: AHS 2024 Section 3_4. This research view uses approved published aggregate summaries and charts.')
        st.download_button('Download approved overall summary (CSV)', SUMMARY.read_bytes(),
                           file_name='apasa_maize_overall_summary.csv', mime='text/csv')
        st.caption('This research view reads only public report, overall-summary and chart files. No raw survey files, identifiers or row-level records are loaded.')
    st.divider()
    st.caption('APASA · AHS research evidence · Descriptive sample findings')


if __name__ == '__main__':
    main()
