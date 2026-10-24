"""Explicit CSV or versioned database adapter. No private-data fallback."""
from django.conf import settings
from .curation import REGISTRY_PATH, annotate
from .normalization import digest


def database_records(slug):
    from .models import DatasetVersion
    version = DatasetVersion.objects.get(slug=slug, active=True)
    if version.registry_sha256 != digest(REGISTRY_PATH.read_bytes()):
        raise ValueError('Curation changed; reimport evidence before database display')
    return list(version.records.order_by('key').values_list('original', flat=True))


def policy_rows(root):
    from .policy_data import load_policy_evidence, prepare_policy_rows
    if settings.PUBLIC_EVIDENCE_MODE == 'csv': return load_policy_evidence(root)
    return prepare_policy_rows(database_records('psta5_day6'))


def district_rows(root):
    from .district_data import load_district_statistics
    if settings.PUBLIC_EVIDENCE_MODE == 'csv': rows = load_district_statistics(root)
    else:
        rows = database_records('sas_2026_b_district')
        # The input is an immutable approved import; retain the display contract.
        from .district_data import MEASURES
        if len(rows) != 1800: raise ValueError('Incomplete database dataset')
        for row in rows:
            title, unit, _, _ = MEASURES[row['measure']]
            state = row['source_value_status']
            display = (row['value'] + (' — reported zero' if state == 'numeric_zero' else '')
                       if state in ['numeric','numeric_zero'] else 'Unavailable — '+('blank in source' if state=='blank' else state+' in source'))
            row.update(title=title, display_unit=unit, value_display=display)
    return annotate(rows, 'district')
