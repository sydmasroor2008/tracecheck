"""Reading documents into fields: one interface, three modes.

MANUAL  values typed by a person in the review screen.
CACHED  values saved in data/<folder>/cached_fields.json (works offline).
LIVE    optional AI service; only if TRACECHECK_LIVE_KEY is set. Not built in this prototype.
"""

import os

from tracecheck.data import folder_path, read_json

MODES = ("MANUAL", "CACHED", "LIVE")
LIVE_KEY_ENV = "TRACECHECK_LIVE_KEY"


class LiveNotConfigured(RuntimeError):
    pass


def extract(doc: str, mode: str, folder: str = "clean", manual_values: dict = None) -> list:
    """Fields for one document file. manual_values maps field key -> typed value (MANUAL)."""
    if mode == "CACHED":
        return [f for f in extract_folder(folder, "CACHED") if f["source_file"] == doc]
    if mode == "MANUAL":
        return [{"key": key, "doc": doc, "label": key, "value": value, "unit": None,
                 "source_file": doc, "page": 1, "mode": "MANUAL", "confidence": 1.0,
                 "needs_review": False, "reviewer": "entered by user", "reviewed_at": None}
                for key, value in (manual_values or {}).items()]
    if mode == "LIVE":
        return extract_live(doc)
    raise ValueError(f"unknown extraction mode {mode!r}; use one of {MODES}")


def extract_folder(folder: str, mode: str = "CACHED") -> list:
    if mode != "CACHED":
        raise ValueError("only CACHED mode reads a whole folder")
    cache = read_json(folder_path(folder) / "cached_fields.json", {})
    return [dict(f) for f in cache.get("fields", [])]


def extract_live(doc: str) -> list:
    if not os.environ.get(LIVE_KEY_ENV):
        raise LiveNotConfigured(f"LIVE mode not configured: set the environment variable {LIVE_KEY_ENV}.")
    raise LiveNotConfigured("LIVE mode is not built in this prototype. Use CACHED or MANUAL.")
