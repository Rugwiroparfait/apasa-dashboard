"""Presentation-only previews. Mock values never enter evidence or imports."""
from django.http import Http404
from decimal import Decimal, InvalidOperation

REPLACEMENT_STEPS = [
    'Locate a published official observation using the policy indicator’s stated data source; record its URL and exact table, page or cell.',
    'Verify the crop or group definition, measure, unit, population, geography and reporting period. Keep ambiguous crop mappings under review.',
    'Check the original value, blanks and reported zeros against the source, then independently review the transcription and method.',
    'Update the reviewed public evidence inventory and comparability assessment, then approve its checksum and rerun the versioned import. Remove the mock preview only after verification.',
]


def presentation(row, mock_requested=False):
    # Copy: never mutate a source row or the original JSON stored in PostgreSQL.
    row = dict(row)
    row['replacement_steps'] = REPLACEMENT_STEPS
    row['mock'] = None
    for key, value in [('target_display', row['target_value']), ('actual_display', row['actual']['value'])]:
        try:
            number = Decimal(value)
            row[key] = format(number, ',.2f') if number.is_finite() else value
        except InvalidOperation:
            row[key] = value
    if mock_requested and not row['actual']['value']:
        row['mock'] = dict(value='1,000', unit=row['target_unit'] or 'Illustrative unit',
            period='Illustrative period — no reported season',
            geography='Illustrative geography — no official estimate',
            source='Mock layout fixture — no official source')
    return row


def choose_record(rows, key):
    if not key:
        return next(iter(rows), None)
    row = next((r for r in rows if r['key'] == key), None)
    if row is None:
        raise Http404('Unknown evidence record')
    return row


def note_text(row):
    lines = ['APASA | Evidence note' + (' — MOCK DATA PREVIEW' if row['mock'] else ''), '', 'Policy question',
        f"What evidence is available for {row['indicator_name']} — {row['crop']} under {row['policy_display']}?",
        '', 'Policy references']
    for ref in row['references']:
        lines.append(f"{ref['label']}: {ref['value'] or 'Not recorded'}; period: {ref['period'] or 'Not recorded'}; unit: {row['target_unit'] or 'Not recorded'}; geography: {row['target_geography'] or 'Not recorded'}.")
    lines += ['', 'Evidence found']
    if row['actual']['value']:
        lines += [f"Published observation: {row['actual']['value']}; period: {row['actual_year_or_period']}; unit: {row['actual_unit']}; geography: {row['actual_geography']}; source crop label: {row['actual_crop_label']}."]
    else:
        lines += ['No matching actual verified in the sources reviewed. Missing evidence is not zero.']
    if row['latest_annual_source_url']:
        lines += ['Separate seasonal observations (not combined):']
        for season in row['seasons']:
            lines.append(f"{season['period']}: {season['value'] or 'Not recorded'}; unit: {row['annual_actual_unit']}; geography: {row['actual_geography']}.")
    lines += ['', 'What can be concluded',
        'The policy references and any official observations above are recorded in the reviewed sources. Their periods, definitions and coverage must be read separately.',
        '', 'What cannot be concluded', row['comparability_status'] + ': ' + row['reason'],
        'No target progress, programme effect, district performance or causal conclusion can be established from this comparison.',
        '', 'Sources',f"{row['policy_name']}: {row['policy_source_url']} — printed page {row['policy_page']}; stated indicator data source: {row['policy_source_agency']}."]
    if row['source_url']:
        lines += [f"{row['source_title']}: {row['source_url']} — {row['page_or_table']}."]
    if row['latest_annual_source_url']:
        lines += [f"NISR SAS 2025 annual workbook: {row['latest_annual_source_url']} — {row['annual_table_reference']}."]
    lines += [f"Inventory checked: {row['checked_on']}. This is not a live release feed."]
    if not row['actual']['value']:
        lines += ['', 'How to replace the evidence gap'] + REPLACEMENT_STEPS
    if row['mock']:
        mock = row['mock']
        lines += ['', 'MOCK DATA — DESIGN PREVIEW ONLY; NOT OFFICIAL EVIDENCE',
            f"Illustrative value: {mock['value']}; illustrative unit: {mock['unit']} (borrowed from the policy target for layout only; actual unit unverified).",
            f"Period: {mock['period']}; geography: {mock['geography']}; source: {mock['source']}.",
            'Do not cite or use this placeholder for policy decisions, calculations or target progress. The official actual remains unverified.']
    return '\n'.join(lines) + '\n'
