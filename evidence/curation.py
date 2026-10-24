"""Curated labels only. Unknown source strings never become filter entries."""
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name('curation.json')


def registry():
    data = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    crops = {r['code']: r for r in data['crops']}
    nodes = {r['code']: r for r in data['policy_nodes']}
    if len(crops) != len(data['crops']) or len(nodes) != len(data['policy_nodes']):
        raise ValueError('Duplicate curated code')
    aliases = {}
    for r in data['crop_aliases']:
        if r['raw_label'] in aliases or (r['crop_code'] and r['crop_code'] not in crops):
            raise ValueError('Invalid crop alias')
        aliases[r['raw_label']] = r
    policy_aliases = {}
    for code, node in nodes.items():
        for label in node['aliases']:
            if label in policy_aliases: raise ValueError('Duplicate policy alias')
            policy_aliases[label] = code
    return data, crops, nodes, aliases, policy_aliases


def annotate(rows, kind):
    _, crops, nodes, aliases, policy_aliases = registry()
    for r in rows:
        label = r['crop'] if kind == 'policy' else r['crop_sas_label']
        alias = aliases.get(label, {})
        code = alias.get('crop_code', '')
        r['crop_code'] = code
        r['crop_display'] = crops[code]['name'] if code else label
        r['crop_kind'] = crops[code]['kind'] if code else 'unconfirmed'
        r['crop_mapping_status'] = alias.get('status', 'review')
        r['crop_mapping_note'] = alias.get('note', 'No curated crop mapping; source scope requires review.')
        if kind == 'policy':
            r['policy_code'] = policy_aliases.get(r['outcome_output'], '')
            if not r['policy_code']: raise ValueError('Policy label needs explicit curation')
            r['policy_display'] = nodes[r['policy_code']]['name']
        else:
            if not code: raise ValueError('District crop requires explicit curation')
            r['display_crop'] = crops[code]['name']
    return rows


def crop_options(rows):
    _, crops, _, _, _ = registry()
    present = {r['crop_code'] for r in rows if r.get('crop_code')}
    return sorted([(code, crops[code]['name'] + (' · crop group' if crops[code]['kind'] == 'group' else ''))
                   for code in present], key=lambda x: x[1])


def resolve_crop(value, rows):
    _, crops, _, aliases, _ = registry()
    code = value if value in crops else aliases.get(value, {}).get('crop_code', '')
    if not code or code not in {r['crop_code'] for r in rows}: raise ValueError('Unknown curated crop')
    return code
