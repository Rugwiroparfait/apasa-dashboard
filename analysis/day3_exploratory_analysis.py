#!/usr/bin/env python3
"""Unweighted maize descriptions; reads local Section 3_4 inputs, exports aggregates only."""
from pathlib import Path
import hashlib
import os
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'apasa-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prepare_section3_4 import DATA_PATH, VARIABLES_CSV, VALUE_LABELS_CSV, load_value_labels

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'day3'
LOCAL_OUT = ROOT / 'local_data' / 'day3'
MIN_STATS = 20
MIN_CHART = 30
FIELDS = {
    'seed_type_code': 'Seed type (matching maize slot)',
    'improved_seed_source_code': 'Improved-seed source (matching maize slot)',
    's4_q1': 'Organic fertilizer use',
    's4_q4': 'Inorganic fertilizer use',
    's4_q6': 'Inorganic fertilizer type (first response position)',
    's4_q12': 'Pesticide/fungicide use',
    's4_q27': 'Mechanical equipment use',
    's4_q28': 'Mechanical equipment type',
    's4_q19': 'Anti-erosion activity present',
    's4_q19_a1': 'Anti-erosion type (first response position)',
    's4_q19_a2': 'Anti-erosion type (second response position)',
    's4_q19_a3': 'Anti-erosion type (third response position)',
    's4_q20': 'Anti-erosion activities done this season',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(frame):
    h = frame.harvest_quantity_kg
    valid = h.dropna()
    n = len(frame)
    result = dict(records=n, plots=n, harvest_nonmissing=len(valid),
                  harvest_missing=int(h.isna().sum()), missing_pct=100*h.isna().sum()/n if n else np.nan,
                  reported_zero=int(h.eq(0).sum()), positive_le_5000=int((h.gt(0)&h.le(5000)).sum()),
                  flagged_gt_5000=int(h.gt(5000).sum()), negative=int(h.lt(0).sum()),
                  statistics_denominator=len(valid), statistics_suppressed=len(valid)<MIN_STATS)
    assert sum(result[k] for k in ['harvest_missing','reported_zero','positive_le_5000','flagged_gt_5000','negative']) == n
    for key, value in [('median_kg',valid.median()), ('q1_kg',valid.quantile(.25)),
                       ('q3_kg',valid.quantile(.75)), ('iqr_kg',valid.quantile(.75)-valid.quantile(.25)),
                       ('mean_kg',valid.mean())]:
        result[key] = value if len(valid)>=MIN_STATS else np.nan
    return result


def main():
    # Verify every raw file and Day 2 artifact remains unchanged during this run.
    protected = list((ROOT/'data').rglob('*')) + list((ROOT/'docs').glob('day2*')) + list((ROOT/'audit_tmp').glob('day2*')) + list((ROOT/'outputs/aggregates').glob('day2*')) + [ROOT/'analysis/prepare_section3_4.py',ROOT/'local_data/section3_4/section3_4_plot_crop_slots.csv']
    before = {p:digest(p) for p in protected if p.is_file()}
    prepared = pd.read_csv(ROOT/'local_data/section3_4/section3_4_plot_crop_slots.csv',low_memory=False)
    variables = pd.read_csv(VARIABLES_CSV).fillna('').set_index('var')
    labels = load_value_labels(VALUE_LABELS_CSV)
    raw = pd.read_stata(DATA_PATH,convert_categoricals=False)
    assert raw.shape == (32616,331) and len(prepared)==74549
    h=prepared.harvest_quantity_kg
    assert (h.notna().sum(),h.isna().sum(),h.eq(0).sum(),h.lt(0).sum(),h.gt(5000).sum()) == (59991,14558,708,0,75)
    assert not prepared.duplicated(['source_row_index','slot']).any()
    # Reconstruct all valid slots from the source and reconcile the prepared grain.
    expected = {(i,s) for s in range(1,8) for i in raw.index[raw[f's3_q4_{s}'].notna()]}
    assert set(zip(prepared.source_row_index,prepared.slot))==expected
    for s in range(1,8):
        part=prepared[prepared.slot==s]
        idx=part.source_row_index.astype(int)
        for dest,src in [('crop_code',f's3_q4_{s}'),('harvest_quantity_kg',f's3_q20_{s}'),('seed_type_code',f's3_q9_{s}'),('improved_seed_source_code',f's3q10_{s}')]:
            assert np.allclose(part[dest].to_numpy(float),raw.loc[idx,src].to_numpy(float),equal_nan=True)
        assert labels[variables.loc[f's3_q4_{s}','value_label_set']][101].strip().lower()=='maize'
    maize=prepared[prepared.crop_code==101].copy()
    idx=maize.source_row_index.astype(int)
    keys=['Season','Cluster_ID','hhid','s2q1']
    keydata=raw.loc[idx,keys]
    assert keydata.notna().all().all(), 'Incomplete plot keys: stop before comparison'
    duplicates=int(keydata.duplicated().sum())
    assert duplicates==0, 'Repeated maize plot-season keys: requires explicit counting resolution'
    assert not raw.duplicated(keys).any()
    assert maize.source_row_index.nunique()==len(maize)==9017
    assert maize.harvest_quantity_kg.isna().sum()==109
    assert maize.harvest_quantity_kg.eq(0).sum()==215
    assert maize.harvest_quantity_kg.gt(5000).sum()==5
    assert maize.harvest_quantity_kg.lt(0).sum()==0
    category_rows=[]
    for field in FIELDS:
        if field.startswith('s4_'):
            assert np.allclose(maize[field].to_numpy(float),raw.loc[idx,field].to_numpy(float),equal_nan=True)
        display=[]
        for slot,code in zip(maize.slot,maize[field]):
            src=f's3_q9_{int(slot)}' if field=='seed_type_code' else f's3q10_{int(slot)}' if field=='improved_seed_source_code' else field
            labelset=variables.loc[src,'value_label_set']
            label=labels.get(labelset,{}).get(code)
            # Questionnaire Section 3.2 (printed page 4) explicitly says 3 = Both.
            if field=='seed_type_code' and code==3: label='Both (traditional and improved seeds)'
            display.append('Missing / not recorded' if pd.isna(code) else f'{code:g}: {label.strip()}' if label else f'{code:g}: UNCONFIRMED')
        maize[field+'_category']=display
        for category in sorted(set(display)):
            category_rows.append(dict(field=field,description=FIELDS[field],category=category,
                grain='crop slot' if field in ['seed_type_code','improved_seed_source_code'] else 'plot-season',
                evidence='Local Section 3_4 variable/value labels; seed code 3 confirmed by questionnaire p.4'))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'figures').mkdir(exist_ok=True)
    all_rows=[]; overall=[]
    for scenario,frame in [('all_reported',maize),('review_sensitivity_le_5000',maize[~maize.harvest_quantity_kg.gt(5000)])]:
        overall.append(dict(scenario=scenario,**describe(frame)))
        for field in FIELDS:
            rows=[]
            for category,group in frame.groupby(field+'_category',dropna=False,sort=True):
                rows.append(dict(scenario=scenario,field=field,category=category,**describe(group)))
            assert sum(r['records'] for r in rows)==len(frame)
            assert sum(r['harvest_missing'] for r in rows)==frame.harvest_quantity_kg.isna().sum()
            all_rows.extend(rows)
    summary=pd.DataFrame(all_rows)
    # Full category counts include singletons; scenario differencing can reveal
    # individual flagged quantities. Keep this detailed aggregate local only.
    LOCAL_OUT.mkdir(parents=True,exist_ok=True)
    summary.to_csv(LOCAL_OUT/'maize_support_summary.csv',index=False,float_format='%.6f')
    pd.DataFrame(overall).to_csv(OUT/'maize_overall_summary.csv',index=False,float_format='%.6f')
    pd.DataFrame(category_rows).to_csv(OUT/'category_dictionary.csv',index=False)
    # Charts contain aggregate quantiles only, never points or extreme values.
    for field,title in FIELDS.items():
        groups=summary[(summary.field==field)&(summary.scenario=='all_reported')]
        shown=groups[groups.harvest_nonmissing>=MIN_CHART]
        if len(shown)<2: continue
        fig,ax=plt.subplots(figsize=(11,max(4,len(shown)*.55+2)))
        y=np.arange(len(shown))
        ax.hlines(y,shown.q1_kg,shown.q3_kg,color='#2878a0',lw=5)
        ax.plot(shown.median_kg,y,'o',color='#122c45')
        ax.set_yticks(y,[f'{r.category}\nN={r.records:,}; observed={r.harvest_nonmissing:,}; missing={r.harvest_missing:,}; zero={r.reported_zero:,}' for r in shown.itertuples()],fontsize=8)
        ax.invert_yaxis();ax.set_xlim(left=0);ax.set_xlabel('Reported maize harvest quantity (kg): median dot; Q1–Q3 line')
        ax.set_title(title+'\nObserved plot-crop records; unweighted',fontsize=12)
        ax.grid(axis='x',alpha=.2)
        omitted=groups[groups.harvest_nonmissing<MIN_CHART]
        note='All values retained, including zeros and >5,000 kg. No causal interpretation.'
        if len(omitted): note+=f'\n{len(omitted)} categories omitted (<30 observed); {omitted.records.sum():,} records, {omitted.harvest_missing.sum():,} missing. See CSV.'
        fig.text(.02,.02,note,fontsize=8)
        fig.tight_layout(rect=(0,.12,1,1));fig.savefig(OUT/'figures'/f'{field}.png',dpi=160);plt.close(fig)
    a,b=overall
    lines=['# Day 3: descriptive maize exploration','',
      '## Findings',
      f"Among {a['records']:,} observed maize plot-crop records, {a['harvest_nonmissing']:,} have reported harvest quantities and {a['harvest_missing']:,} are missing ({a['missing_pct']:.2f}%). There are {a['reported_zero']:,} reported zeros, whose meaning is unconfirmed, and {a['flagged_gt_5000']} values above the 5,000 kg review threshold.",
      f"The median is {a['median_kg']:.1f} kg (Q1–Q3 {a['q1_kg']:.1f}–{a['q3_kg']:.1f}; IQR {a['iqr_kg']:.1f} kg); the mean is {a['mean_kg']:.2f} kg. Excluding only the five review-flagged records in a sensitivity view gives {b['records']:,} records, {b['harvest_nonmissing']:,} observed harvests, median {b['median_kg']:.1f} kg and mean {b['mean_kg']:.2f} kg. The main analysis retains all records.",'',
      '### Main category comparisons (all reported values)',
      'Each row counts observed maize records and distinct plot-seasons equally. Harvest statistics use only the observed-harvest denominator, including reported zeros. Missing category values remain a separate group. Q1/Q3 use pandas linear quantile interpolation.','',
      '| Category | Records / plots | Missing harvest | Observed harvest | Median kg | Q1–Q3 kg | Mean kg |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for field in ['seed_type_code','improved_seed_source_code','s4_q1','s4_q4','s4_q12','s4_q27','s4_q19']:
        for r in summary[(summary.field==field)&(summary.scenario=='all_reported')].itertuples():
            stat='suppressed' if r.statistics_suppressed else f'{r.median_kg:.1f} | {r.q1_kg:.1f}–{r.q3_kg:.1f} | {r.mean_kg:.2f}'
            if r.statistics_suppressed or field=='s4_q27': stat='suppressed | suppressed | suppressed'
            lines.append(f'| {FIELDS[field]} — {r.category} | {r.records:,} | {r.harvest_missing:,} | {r.harvest_nonmissing:,} | {stat} |')
    def main_stat(field,category):
        return summary[(summary.field==field)&(summary.scenario=='all_reported')&summary.category.str.startswith(category)].iloc[0]
    traditional=main_stat('seed_type_code','1:')
    improved=main_stat('seed_type_code','2:')
    fert_yes=main_stat('s4_q4','1:'); fert_no=main_stat('s4_q4','2:')
    pest_yes=main_stat('s4_q12','1:'); pest_no=main_stat('s4_q12','2:')
    lines+=['','### Interpretation',
      f"Median reported maize harvest is {improved.median_kg:.0f} kg for improved-seed records versus {traditional.median_kg:.0f} kg for traditional-seed records. Inorganic fertilizer use categories have medians of {fert_yes.median_kg:.0f} kg (Yes) and {fert_no.median_kg:.0f} kg (No); pesticide/fungicide categories have medians of {pest_yes.median_kg:.0f} and {pest_no.median_kg:.0f} kg. These are associations among observed records, with different group compositions and potentially different plot sizes.",
      'Organic fertilizer categories differ little in median (30 versus 24 kg), while both anti-erosion presence categories have a 30 kg median. Means tell a different story for these categories and are sensitive to the upper tail. The local-only support CSV gives the full median, quartile and mean comparison for every category with the flagged records excluded.',
      'The Both-seed category has only 55 records (53 observed harvests); treat its higher median cautiously. Only seven records report mechanical equipment use, so no numerical harvest comparison or equipment chart is produced for that group. The report also withholds harvest statistics for equipment nonusers to prevent recovery of the small group total by subtraction from the overall mean. All 87 records with missing seed type also lack harvest quantity. Improved-seed source is missing in 3,651 records; source-group comparisons require attention to seed-question routing and cannot represent all maize growers.',
      '', '## Methods and counting',
      'Inputs: unchanged Day 2 prepared CSV and Section 3_4 raw file, plus local variable/value-label CSVs. The local questionnaire `audit_tmp/docs/AHS2024_questionnaire.pdf`, printed pages 3–6, supports plot number, crop-slot harvest units, seed categories and plot practices. Section 3.20 is total reported seasonal crop-slot harvest quantity in kg, with already-harvested and remaining-quantity questions preceding it; it is not a household total or necessarily a final measured harvest.',
      'The prepared file deliberately excludes direct IDs. Source row index was used only in memory to recover identifiers from the same Section 3_4 file, not to merge survey sections. The available composite key is Season + Cluster_ID + hhid + s2q1 (plot number). All key components are present; zero duplicate composite keys occur in the 32,616 source rows or 9,017 maize records. There are zero repeated source rows among maize slots. Thus each maize slot corresponds to one distinct observed plot-season; no deduplication or summing is required. Multiple plots from one household may remain; independence is not assumed. The script stops if this uniqueness condition changes.',
      'For all seven slots the script reconciles crop, harvest, seed type and improved-seed source against matching source suffixes, and checks plot-level values against the source row. Labels are resolved per slot rather than borrowed from another slot. No code meaning is guessed; unmapped codes are marked UNCONFIRMED.',
      'The local-only grouped CSV (`local_data/day3/maize_support_summary.csv`) covers every listed Day 2 support field, including every observed category and missing category, for both the full and sensitivity samples. Each field partitions its scenario total; the different fields must not be added together. The sensitivity view excludes only values >5,000 kg and retains missing harvest records and zeros. This threshold is a review flag, not a validated error definition.',
      'Inorganic fertilizer type is the first response position, not an exhaustive fertilizer-use category: the raw file has additional positions absent from the prepared data. Anti-erosion types are three separate response positions, not mutually exclusive overall activity types. Their counts must not be summed as unique activity users. Plot-level practices may apply to crops other than maize on mixed-crop plots.',
      'Missing improved-seed sources, equipment/fertilizer types and anti-erosion follow-ups can reflect questionnaire routing or nonresponse. They are not interpreted as nonuse. The questionnaire routing has some inconsistent references; no structural-missing recoding is attempted. No plot area is used: the prepared data omit it, and no crop-specific area denominator is established.',
      '', '## Outputs, safeguards and limitations',
      'Public outputs `outputs/day3/maize_overall_summary.csv` and `category_dictionary.csv` contain overall aggregate descriptions and category metadata only. The detailed support CSV is local-only: singleton category counts and differencing of scenario means can disclose individual flagged harvest quantities, even when small-group statistics are suppressed. The legacy `outputs/day3/maize_support_summary.csv` is also retained locally and explicitly ignored. `outputs/day3/figures/` contains median and interquartile-range charts with group counts, missingness and zeros annotated. Categories with fewer than 30 observed harvests are omitted from charts with their omitted counts disclosed. Statistics for fewer than 20 observed harvests are suppressed in the local support CSV; its counts remain available locally. Chart footnotes referring to the CSV refer to this local-only support file. These are exploratory presentation safeguards, not an official disclosure clearance.',
      'All statistics are descriptive and unweighted. Differences describe these observed records only; they do not measure practice effects, yield, productivity or national agricultural conditions. Plot size, crop mix, geography, selection into support categories, household clustering, missingness and reporting error may explain differences. No significance tests, confidence intervals, regressions or survey-design inference are produced. Small categories warrant particular caution; means can be sensitive to large quantities.',
      'Raw inputs and Day 2 artifacts are read-only and hash-checked during execution. No household IDs, plot IDs, record UIDs, source row indices, individual observations or extreme-value lists are exported. Raw and processed microdata remain local and ignored. No NISR contact, other-section merge or dashboard work is performed.',
      '', '## Reproduce',
      'From the repository root, with the same local Day 2 inputs and Python 3.10+:','',
      '```bash','python3 -m pip install -r requirements.txt matplotlib','python3 analysis/day3_exploratory_analysis.py','```','',
      'The script asserts source/prepared shape, slot alignment, plot-key uniqueness, maize missing/zero/flag counts, and group-denominator reconciliation.']
    (ROOT/'docs/day3_findings.md').write_text('\n'.join(lines)+'\n')
    assert all(digest(p)==h for p,h in before.items()), 'Protected input or Day 2 artifact changed'
    print(f'PASS: {len(maize):,} unique maize plot-seasons; {len(summary)} grouped aggregate rows; all denominators reconcile; protected files unchanged.')


if __name__=='__main__':
    main()
