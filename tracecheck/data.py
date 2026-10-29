"""Load a demo folder: settings, extracted fields, approvals, and the reviewed facility data.

The facility data is a nested dict built only from approved fields. A field
that is not approved yet is stored as None, so checks and the calculator
treat it as missing.
"""

import datetime
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FOLDERS = ["clean", "problem", "trader"]
AUTO_REVIEWER = "auto-approved (confidence at or above threshold)"

_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def folder_path(folder: str) -> Path:
    return DATA / folder


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def parse_key(key: str) -> list:
    """'certificates[2].chemistry.Mn' -> ['certificates', 2, 'chemistry', 'Mn']"""
    return [int(idx) if idx else name for name, idx in _TOKEN.findall(key)]


def get_path(obj, key: str):
    for part in parse_key(key):
        if obj is None:
            return None
        if isinstance(part, int):
            obj = obj[part] if part < len(obj) else None
        else:
            obj = obj.get(part)
    return obj


def set_path(obj, key: str, value) -> None:
    parts = parse_key(key)
    for part, nxt in zip(parts, parts[1:]):
        empty = [] if isinstance(nxt, int) else {}
        if isinstance(part, int):
            while len(obj) <= part:
                obj.append(None)
            if obj[part] is None:
                obj[part] = empty
            obj = obj[part]
        else:
            obj = obj.setdefault(part, empty)
    last = parts[-1]
    if isinstance(last, int):
        while len(obj) <= last:
            obj.append(None)
    obj[last] = value


def load_documents(folder: str) -> list:
    cache = read_json(folder_path(folder) / "cached_fields.json", {})
    return cache.get("documents", [])


def load_fields(folder: str, saved: bool = True) -> list:
    """Cached fields with review state. saved=False ignores approvals.json (demo start)."""
    from tracecheck.extract import extract_folder

    threshold = load_config()["review_confidence_threshold"]
    approvals = read_json(folder_path(folder) / "approvals.json", {}) if saved else {}
    fields = []
    for f in extract_folder(folder, "CACHED"):
        f = dict(f)
        f["needs_review"] = f["confidence"] < threshold
        f["approved"] = not f["needs_review"]
        f["reviewer"] = AUTO_REVIEWER if f["approved"] else None
        f["reviewed_at"] = None
        f.update(approvals.get(f["key"], {}))
        fields.append(f)
    return fields


def save_approval(folder: str, key: str, value=None, edited: bool = False,
                  reviewer: str = "reviewer (demo)") -> None:
    path = folder_path(folder) / "approvals.json"
    approvals = read_json(path, {})
    entry = {"approved": True, "reviewer": reviewer,
             "reviewed_at": datetime.datetime.now().isoformat(timespec="seconds")}
    if edited:
        entry["value"] = value
        entry["mode"] = "MANUAL"
    approvals[key] = entry
    write_json(path, approvals)


def reset_approvals(folder: str) -> None:
    path = folder_path(folder) / "approvals.json"
    if path.exists():
        path.unlink()


def load_flag_notes(folder: str) -> dict:
    return read_json(folder_path(folder) / "flag_notes.json", {})


def save_flag_note(folder: str, flag_key: str, note: str) -> None:
    path = folder_path(folder) / "flag_notes.json"
    notes = read_json(path, {})
    notes[flag_key] = note
    write_json(path, notes)


def build_facility(fields: list, config: dict) -> dict:
    """Nested facility data from approved fields; unapproved values become None."""
    fac = {}
    sources, modes, pending = {}, {}, []
    for f in fields:
        set_path(fac, f["key"], f["value"] if f["approved"] else None)
        sources[f["key"]] = f"{f['source_file']} p.{f['page']}"
        modes[f["key"]] = f["mode"]
        if not f["approved"]:
            pending.append(f["key"])
    fac["reporting_year"] = config["reporting_year"]
    fac["_sources"] = sources
    fac["_modes"] = modes
    fac["_pending"] = pending
    return fac


def load_facility(folder: str, saved: bool = True) -> dict:
    return build_facility(load_fields(folder, saved), load_config())


def sources_for(fac: dict, *prefixes: str) -> list:
    """Unique source documents for every field whose key starts with one of the prefixes."""
    found = []
    for key, src in fac.get("_sources", {}).items():
        if key.startswith(prefixes) and src not in found:
            found.append(src)
    return found
