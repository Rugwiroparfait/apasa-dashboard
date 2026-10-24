# Public evidence data layer

APASA can serve the national policy and district statistics pages from PostgreSQL,
or run locally from approved public CSVs without any database. The AHS research
page retains its separate approved-aggregate workflow. No new statistics, target
progress, programme-delivery measures or crop analyses are calculated.

## Inputs and boundaries

| Present input | Representation in this first import |
| --- | --- |
| `docs/day6_indicator_comparability.csv` (126 rows) | Versioned policy source records, with separate baseline, target-reference, final-target, latest-actual and recorded seasonal observations. The 18 contextual and 108 not-currently-comparable classifications are preserved. |
| `outputs/day7/official_sas_2026_b_district.csv` (1,800 rows) | Versioned district source records and observations; four measures, original units, source blanks, zeros, district identifiers and worksheet/cell references retained. |
| `docs/apasa_crop_indicator_catalogue.csv`, `docs/crop_coverage_matrix.csv` | Preserved policy/reference material; not imported as duplicate actual observations. |
| Day 11 requirements and Day 12 evidence/history/2016 audit tables | Preserved audit material; not automatically promoted to application observations. |
| Day 2/3/5 approved AHS aggregates | Preserved research workflow; outside this initial database import. |
| Local published SAS workbooks and reference reports | Unchanged source references; this importer does not open or convert them. |
| Raw `.dta`, local prepared records and detailed support CSVs | Restricted, ignored, never read, exported or loaded by this workflow. |

`evidence/public_sources.json` is the fixed path/checksum allowlist. There is no
arbitrary CSV or directory import. A source change fails closed until it has been
reviewed and its approved checksum explicitly updated. Source CSVs and workbooks
are never rewritten. Public normalized tables are under a content-addressed
`outputs/public_evidence/<bundle>/` directory:

- `source_records.csv`: original source-row JSON, original labels and curated links.
- `observations.csv`: one source value per row, including its state, measure,
  period, unit, geography, source label, URL and reference.
- `curated_crops.csv` and `curated_policy_nodes.csv`: reviewed filter dimensions.
- `manifest.json`: source paths/checksums, transform version, full curation
  snapshot/checksum, exported table checksums and row counts.

The two inputs produce **1,926 source records and 2,358 observations** (558 policy
observations and 1,800 district observations). Blank policy values are retained;
these counts do not imply that every observation has a verified actual.
Numbers remain source text to avoid rounding or silent unit conversion.

## Curation and provenance

`evidence/curation.json` is an explicit registry, not a runtime list of distinct
source strings. Policy aliases with a bare code and a longer label resolve to
one curated code/name. The 21 outcome/output names are verified against PSTA5
Annex 1, with PDF references in the registry. `PSTA5-I…` indicator identifiers are
APASA registry codes, not official indicator numbers. Original indicator wording
is retained, including definition-review labels.

Individual crops and broad groups have different entries and a stored `kind`.
Case/plural aliases are explicit. Ambiguous labels such as Rice, Potato and Soya
are marked for review rather than automatically merged with more specific crops.
Unresolved records remain inspectable in the unfiltered policy view, with their
source wording and review note; they do not become selectable crop entries.
A curated match does not establish target/actual comparability. No Day 6 status
is changed by normalization.

Django models are `Crop`, `PolicyNode`, `DatasetVersion`, `SourceRecord` and
`Observation`. Foreign keys, unique source keys and one-active-version-per-dataset
constraints protect the import. A fingerprint includes source checksum, registry
checksum and transform version. Reimporting the same version adds no records.
Changed versions retain old records and activate the new version atomically.
Shared dimension labels reflect current curation; each version's manifest retains
its historical registry and each source record retains its original text.
Database pages refuse a registry/version mismatch until reimported.

## Local setup and import

Use the project's Python environment and install `requirements.txt` (Django 5.2
and psycopg 3). PostgreSQL 14 or later is supported by Django 5.2. Create a local
database and database user using your PostgreSQL installation; do not use a
restricted microdata database. Supply connection settings through the environment:

```bash
export APASA_DB_NAME=apasa
export APASA_DB_USER=apasa
export APASA_DB_HOST=localhost
export APASA_DB_PORT=5432
# Supply APASA_DB_PASSWORD privately if your PostgreSQL authentication needs it.
python manage.py export_public_evidence
python manage.py migrate
python manage.py import_public_evidence
APASA_EVIDENCE_MODE=database python manage.py runserver
```

The export command needs no database. Both commands accept `--output PATH` for
the bundle parent directory. The database import reads the verified generated
CSV tables inside a transaction. A failed import rolls back. Keep generated bundles
as provenance; do not edit them. A changed transformation should increment
`TRANSFORM_VERSION`. Review any new source or alias before adding it to the
allowlist/registry; do not indiscriminately ingest every policy or crop string.

With `APASA_EVIDENCE_MODE` unset (or `csv`), startup and pages do not query
PostgreSQL, even if it is offline. Explicit database mode reports unavailable
evidence rather than silently falling back to a different source. The server is
still a local prototype, without accounts, uploads, production deployment or
new programme functionality. Environment files and database dumps are ignored;
settings do not automatically load `.env` files.

## Checks

```bash
python manage.py check
python manage.py test evidence
python manage.py test evidence.database_checks --settings=apasa.test_settings
# With the PostgreSQL environment above, explicitly run the same integration suite:
python manage.py test evidence.database_checks
python manage.py makemigrations --check --dry-run
```

The default suite is database-free. The explicit integration suite uses in-memory
SQLite only with `apasa.test_settings`, or a temporary Django test database on
PostgreSQL (the test role must be allowed to create that test database). It checks
idempotence, provenance, curated labels/groups, atomic rollback, constraints and
pages served from imported records. Startup tests use a public-files-only copy,
without raw files, prepared records or local reference folders.

The workflow never scans or reads `data/` or `local_data/`. Public geographic IDs
are district/province identifiers, not household or plot identifiers. Restricted
files, credentials, database directories and dumps must remain outside tracked
public evidence. No institution was contacted and no deployment is configured.
