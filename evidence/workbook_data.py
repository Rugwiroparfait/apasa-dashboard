"""Read the compact, checksummed workbook bundle; never open raw workbooks on requests."""

import hashlib
import json
from pathlib import Path
from functools import lru_cache

BUNDLE_PATH = Path("outputs/workbook_observations/evidence.json")


@lru_cache(maxsize=4)
def load_bundle(root):
    path = Path(root) / BUNDLE_PATH
    raw = path.read_bytes()
    expected = path.with_suffix(".sha256").read_text().strip()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Workbook bundle checksum mismatch")
    bundle = json.loads(raw)
    if bundle["schema_version"] != 1:
        raise ValueError("Unsupported workbook bundle")
    return bundle


def crop_observations(root, crop):
    # Exact source labels only: broad or ambiguous crop names are not merged.
    label = crop
    return [
        r
        for r in load_bundle(str(root))["observations"]
        if r["crop"].casefold() == label.casefold()
        and r["indicator"] in {"production", "yield"}
    ]
