"""Explicit public inputs; independent of Streamlit and private analysis workflows."""
import csv
from decimal import Decimal
from pathlib import Path

FIGURES = {'Seed types': 'seed_type_code.png', 'Improved-seed sources': 'improved_seed_source_code.png', 'Organic fertilizer use': 's4_q1.png', 'Inorganic fertilizer use': 's4_q4.png', 'Inorganic fertilizer type · first response': 's4_q6.png', 'Pesticide / fungicide use': 's4_q12.png', 'Anti-erosion activity present': 's4_q19.png', 'Anti-erosion type · first response': 's4_q19_a1.png', 'Anti-erosion type · second response': 's4_q19_a2.png', 'Anti-erosion type · third response': 's4_q19_a3.png', 'Anti-erosion activities done this season': 's4_q20.png'}
SCENARIOS = {'all_reported': 'All records · main analysis', 'review_sensitivity_le_5000': 'Exclude >5,000 kg · sensitivity only'}
SUMMARY_PATH = Path('outputs/day3/maize_overall_summary.csv')
REPORT_PATH = Path('docs/day3_findings.md')


def load_pilot(root):
    root = Path(root)
    with (root / SUMMARY_PATH).open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    summaries = {}
    for raw in rows:
        key = raw['scenario']
        row = {k: Decimal(v) for k, v in raw.items() if k not in ['scenario', 'statistics_suppressed']}
        if key in summaries or row['records'] != row['harvest_nonmissing'] + row['harvest_missing']:
            raise ValueError('Published summary denominators do not reconcile.')
        if row['harvest_nonmissing'] != sum(row[k] for k in ['reported_zero', 'positive_le_5000', 'flagged_gt_5000', 'negative']):
            raise ValueError('Published harvest categories do not reconcile.')
        summaries[key] = dict(row, key=key, label=SCENARIOS[key])
    if set(summaries) != set(SCENARIOS):
        raise ValueError('Expected both approved overall scenarios.')
    prefixes = {'Seed type (matching maize slot) — 1: Traditional seeds': 'Traditional seeds', 'Seed type (matching maize slot) — 2: Improved seeds': 'Improved seeds'}
    seed = []
    for line in (root / REPORT_PATH).read_text(encoding='utf-8').splitlines():
        cells = [x.strip() for x in line.strip().strip('|').split('|')]
        if cells[0] in prefixes:
            if len(cells) != 7:
                raise ValueError('Published seed table changed.')
            records, missing, observed = [int(x.replace(',', '')) for x in cells[1:4]]
            if records != missing + observed:
                raise ValueError('Published seed denominators do not reconcile.')
            seed.append(dict(label=prefixes[cells[0]], records=records, missing=missing, observed=observed, median=Decimal(cells[4])))
    if len(seed) != 2 or len({r['label'] for r in seed}) != 2:
        raise ValueError('Expected two published seed categories.')
    return summaries, seed
