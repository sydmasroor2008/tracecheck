"""Load a demo folder: settings, extracted fields, and the reviewed facility data.

Approvals, accepted flags and LIVE choices are not stored here: the app keeps
them for the browser session and passes them in.

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
ACCURACY = DATA / "accuracy.json"     # written by tools/measure_extraction.py
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


def load_fields(folder: str, approvals: dict = None, live_use: list = ()) -> list:
    """Cached fields with review state. With no arguments this is the original demo start.

    approvals: field key -> approval entry. live_use: documents whose saved LIVE fields replace the CACHED ones."""
    from tracecheck.extract import extract_folder, load_live

    threshold = load_config()["review_confidence_threshold"]
    approvals = approvals or {}
    cached = extract_folder(folder, "CACHED")
    if live_use:
        live = load_live(folder)
        use = [d for d in live_use if d in live]
        known = {f["key"] for f in cached}
        cached = [f for f in cached if f["source_file"] not in use]
        # a null for a field the document does not carry is not a value to review
        cached += [f for d in use for f in live[d]["fields"] if f["value"] is not None or f["key"] in known]
    fields = []
    for f in cached:
        f = dict(f)
        f["needs_review"] = f["confidence"] < threshold or (f["mode"] == "LIVE" and f["needs_review"])
        f["approved"] = not f["needs_review"]
        f["reviewer"] = AUTO_REVIEWER if f["approved"] else None
        f["reviewed_at"] = None
        f.update(approvals.get(f["key"], {}))
        fields.append(f)
    return fields


def accuracy_line(path: Path = None) -> str:
    """The saved measurement as one sentence, or '' if there is none yet."""
    m = read_json(path or ACCURACY)
    if not m or not m["total"]:
        return ""
    return (f"Gemini field accuracy on {m['documents']} synthetic documents: "
            f"{100 * m['correct'] / m['total']:.1f}% ({m['date']}, {m['model']})")


def approval_entry(value=None, edited: bool = False, reviewer: str = "reviewer (demo)") -> dict:
    entry = {"approved": True, "reviewer": reviewer,
             "reviewed_at": datetime.datetime.now().isoformat(timespec="seconds")}
    if edited:
        entry["value"] = value
        entry["mode"] = "MANUAL"
    return entry


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


def load_facility(folder: str) -> dict:
    return build_facility(load_fields(folder), load_config())


def sources_for(fac: dict, *prefixes: str) -> list:
    """Unique source documents for every field whose key starts with one of the prefixes."""
    found = []
    for key, src in fac.get("_sources", {}).items():
        if key.startswith(prefixes) and src not in found:
            found.append(src)
    return found
