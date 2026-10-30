"""Reading documents into fields: one interface, three modes.

MANUAL  values typed by a person in the review screen.
CACHED  values saved in data/<folder>/cached_fields.json (works offline).
LIVE    the Gemini API reads the document image and returns JSON fields with a
        confidence each. Key from GEMINI_API_KEY only. AI reads; code calculates;
        a person approves. Every LIVE result is saved to data/<folder>/live_fields.json
        so it can be replayed offline.
"""

import datetime
import json
import os
import re
import typing
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ValidationError, create_model

from tracecheck.data import DATA, folder_path, load_config, load_documents, read_json, write_json
from tracecheck.model import (Certificate, DeliveryNote, FuelInvoice, ProductionRow, Purchase, Scrap,
                              Shipment, Stock, VerificationReport)

MODES = ("MANUAL", "CACHED", "LIVE")
KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "GEMINI_MODEL"
DEFAULT_MODEL = "gemini-3.5-flash"   # chosen on 2026-10-30 for response time, see DECISIONS.md
NOT_AVAILABLE = "LIVE mode not available, using CACHED results"
TIMEOUT_MS = 90_000   # one request; after this the app falls back instead of hanging
UPLOADS = DATA / "uploads"


class LiveNotConfigured(RuntimeError):
    pass


class ProductionRegister(BaseModel):
    factory: str
    production: List[ProductionRow]


# document type -> (key prefix, model, model fields not printed on the document, what to tell the model)
DOC_SPECS = {
    "purchase_invoice": ("purchases", Purchase, (),
                         "a steel purchase invoice. supplier_type is 'mill' or 'trader' as printed. "
                         "emissions_claim is the word printed after 'Embedded emissions data', or null if absent."),
    "delivery_note": ("delivery_notes", DeliveryNote, (),
                      "a delivery note from a steel trader naming the mill and the heat numbers."),
    "mill_certificate": ("certificates", Certificate, ("layout",),
                         "a steel mill test certificate. Chemistry values are mass percent; read every value "
                         "under its own element label (C, Mn, Si, Cr, Ni, other). 'other' is other alloy elements."),
    "verification_report": ("verification_reports", VerificationReport, (),
                            "a verification report for a steel mill. label is the note printed on the value."),
    "gas_invoice": ("fuel", FuelInvoice, (),
                    "a natural gas invoice. unit is the unit printed next to the quantity."),
    "export_invoice": ("shipments", Shipment, (),
                       "an export invoice. destination is the country code. production_months lists every month printed."),
    "production_register": ("", ProductionRegister, (),
                            "a monthly production register. Give one row per month in the order printed."),
    "stock_register": ("stock", Stock, (),
                       "a steel stock register with opening and closing stock rows and a handwritten count note."),
    "scrap_register": ("scrap", Scrap, (),
                       "a scrap register. pre_consumer_share is a fraction from 0 to 1."),
}

UNITS = {"tonnes": "t", "precursor_see": "t CO2/t", "emission_factor_t_per_tj": "t CO2/TJ",
         "pre_consumer_share": "fraction"}

PROMPT = """You are reading {what}
Return the fields in the JSON schema. For every field give:
- value: exactly as printed on the document. Dates as YYYY-MM-DD, months as YYYY-MM, numbers without units.
- confidence: from 0 to 1, how sure you are that you read this value correctly.
If a value is not visible or not readable, set value to null and confidence to 0.
Never guess. Never calculate. Never fill a value from other fields or from what is usual."""


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
        return read_with_ai(folder, doc)[0]
    raise ValueError(f"unknown extraction mode {mode!r}; use one of {MODES}")


def extract_folder(folder: str, mode: str = "CACHED") -> list:
    if mode != "CACHED":
        raise ValueError("only CACHED mode reads a whole folder")
    cache = read_json(folder_path(folder) / "cached_fields.json", {})
    return [dict(f) for f in cache.get("fields", [])]


# ---------- LIVE ----------

def model_name() -> str:
    return os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def pick_flash_model(names: list) -> Optional[str]:
    """Newest stable 'gemini-X.Y-flash' name (no lite, preview, image or tts)."""
    found = []
    for name in names:
        m = re.fullmatch(r"(?:models/)?gemini-(\d+)(?:\.(\d+))?-flash", name)
        if m:
            found.append(((int(m.group(1)), int(m.group(2) or 0)), name.removeprefix("models/")))
    return max(found)[1] if found else None


def make_client():
    key = os.environ.get(KEY_ENV)
    if not key:
        raise LiveNotConfigured(f"LIVE mode not configured: set the environment variable {KEY_ENV}.")
    from google import genai
    from google.genai import types
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))


def page_images(path: Path) -> list:
    """(bytes, mime type) for every page: a JPG as it is, a PDF rendered to PNG at 144 dpi."""
    if path.suffix.lower() in (".jpg", ".jpeg", ".png"):
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return [(path.read_bytes(), mime)]
    import io

    import pypdfium2
    pdf = pypdfium2.PdfDocument(str(path))
    out = []
    for page in pdf:
        buf = io.BytesIO()
        page.render(scale=2).to_pil().save(buf, format="PNG")
        out.append((buf.getvalue(), "image/png"))
    pdf.close()
    return out


def _inner(annotation):
    """Optional[X] -> X"""
    args = [a for a in typing.get_args(annotation) if a is not type(None)]
    return args[0] if typing.get_origin(annotation) is typing.Union and len(args) == 1 else annotation


def _is_model(t) -> bool:
    return isinstance(t, type) and issubclass(t, BaseModel)


def _list_model(t):
    if typing.get_origin(t) in (list, List):
        sub = typing.get_args(t)[0]
        return sub if _is_model(sub) else None
    return None


_LIVE_MODELS = {}


def live_model(model, skip=()):
    """The same fields as `model`, each leaf wrapped as {value (nullable), confidence}."""
    cache_key = (model, tuple(skip))
    if cache_key in _LIVE_MODELS:
        return _LIVE_MODELS[cache_key]
    fields = {}
    for name, info in model.model_fields.items():
        if name in skip:
            continue
        t = _inner(info.annotation)
        if _is_model(t):
            fields[name] = (live_model(t), ...)
        elif _list_model(t):
            fields[name] = (List[live_model(_list_model(t))], ...)
        else:
            leaf = create_model(f"Live_{model.__name__}_{name}", value=(Optional[t], None), confidence=(float, ...))
            fields[name] = (leaf, ...)
    _LIVE_MODELS[cache_key] = create_model(f"Live{model.__name__}", **fields)
    return _LIVE_MODELS[cache_key]


def _leaves(obj, model, prefix, skip=()):
    """[(key, value, confidence)] from a (possibly partial) dict shaped like live_model(model)."""
    out = []
    obj = obj if isinstance(obj, dict) else {}
    for name, info in model.model_fields.items():
        if name in skip:
            continue
        key = f"{prefix}.{name}" if prefix else name
        t = _inner(info.annotation)
        item = obj.get(name)
        if _is_model(t):
            out += _leaves(item, t, key)
        elif _list_model(t):
            for i, row in enumerate(item if isinstance(item, list) else []):
                out += _leaves(row, _list_model(t), f"{key}[{i}]")
        else:
            item = item if isinstance(item, dict) else {}
            conf = item.get("confidence")
            out.append((key, item.get("value"), float(conf) if isinstance(conf, (int, float)) else 0.0))
    return out


def parse_live(raw: str, kind: str, prefix: str) -> tuple:
    """(leaves, valid). Invalid JSON or a schema mismatch keeps what can be read and marks it invalid."""
    _, model, skip, _ = DOC_SPECS[kind]
    try:
        obj = live_model(model, skip).model_validate_json(raw).model_dump()
        return _leaves(obj, model, prefix, skip), True
    except (ValidationError, ValueError):
        try:
            obj = json.loads(raw)
        except (ValueError, TypeError):
            obj = {}
        return _leaves(obj, model, prefix, skip), False


def doc_prefix(folder: str, doc: str, kind: str) -> str:
    """Key prefix of a document, e.g. 'certificates[2]', taken from the folder's field list."""
    base = DOC_SPECS[kind][0]
    if not base or not _list_model_type(kind):
        return base
    keys = [f["key"] for f in extract_folder(folder) if f["source_file"] == doc]
    m = re.match(rf"({re.escape(base)}\[\d+\])", keys[0]) if keys else None
    if m:
        return m.group(1)
    used = {int(i) for k in (f["key"] for f in extract_folder(folder))
            for i in re.findall(rf"^{re.escape(base)}\[(\d+)\]", k)}
    return f"{base}[{max(used, default=-1) + 1}]"


def _list_model_type(kind: str) -> bool:
    """True for document types that are one row of a list in the facility data."""
    return kind not in ("production_register", "stock_register", "scrap_register")


def doc_kind(folder: str, doc: str) -> Optional[str]:
    return next((d["type"] for d in load_documents(folder) if d["file"] == doc), None)


def extract_live(folder: str, doc: str, kind: str = None, client=None, path: Path = None) -> dict:
    """Read one document with Gemini. Returns {model, read_at, valid, fields}. Raises on any failure."""
    kind = kind or doc_kind(folder, doc)
    if kind not in DOC_SPECS:
        raise ValueError(f"no LIVE reading for document type {kind!r}")
    path = path or folder_path(folder) / "docs" / doc
    client = client or make_client()
    _, model, skip, what = DOC_SPECS[kind]
    from google.genai import types
    parts = [types.Part.from_bytes(data=b, mime_type=mime) for b, mime in page_images(path)]
    name = model_name()
    resp = client.models.generate_content(
        model=name, contents=parts + [PROMPT.format(what=what)],
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           response_schema=live_model(model, skip)))
    prefix = doc_prefix(folder, doc, kind) if folder else DOC_SPECS[kind][0]
    leaves, valid = parse_live(resp.text or "", kind, prefix)
    read_at = datetime.datetime.now().isoformat(timespec="seconds")
    served = getattr(resp, "model_version", None)
    return {"model": name, "model_version": served if isinstance(served, str) else None,
            "read_at": read_at, "valid": valid, "kind": kind,
            "fields": live_fields(leaves, doc, folder, valid, name, read_at)}


def live_fields(leaves: list, doc: str, folder: str, valid: bool, name: str, read_at: str) -> list:
    """Field records like CACHED ones, with mode LIVE, model and time. Invalid output -> all need review."""
    threshold = load_config()["review_confidence_threshold"]
    labels = {f["key"]: (f["label"], f["unit"]) for f in extract_folder(folder)} if folder else {}
    out = []
    for key, value, conf in leaves:
        last = key.rsplit(".", 1)[-1]
        label, unit = labels.get(key, (last.replace("_", " ").capitalize(),
                                       "%" if ".chemistry." in key else UNITS.get(last)))
        out.append({"key": key, "doc": doc, "label": label, "value": value, "unit": unit,
                    "source_file": doc, "page": 1, "mode": "LIVE", "confidence": round(conf, 3),
                    "needs_review": (not valid) or value is None or conf < threshold,
                    "reviewer": None, "reviewed_at": None, "model": name, "read_at": read_at})
    return out


def live_cache_path(folder: str) -> Path:
    return folder_path(folder) / "live_fields.json" if folder else UPLOADS / "live_fields.json"


def load_live(folder: str) -> dict:
    return read_json(live_cache_path(folder), {}).get("documents", {})


def save_live(folder: str, doc: str, result: dict) -> None:
    path = live_cache_path(folder)
    cache = read_json(path, {"note": "LIVE results from the Gemini API, saved so they can be replayed offline.",
                             "documents": {}})
    cache["documents"][doc] = result
    write_json(path, cache)


def read_with_ai(folder: str, doc: str, kind: str = None, client=None, path: Path = None) -> tuple:
    """(fields, message). Never raises: falls back to the saved LIVE result, then to CACHED."""
    try:
        result = extract_live(folder, doc, kind, client, path)
    except Exception as exc:  # no key, no network, quota, bad file: the app must keep working
        reason = str(exc).splitlines()[0][:160] if str(exc) else type(exc).__name__
        saved = load_live(folder).get(doc)
        if saved:
            return saved["fields"], (f"LIVE mode not available ({reason}); replaying the LIVE result "
                                     f"saved on {saved['read_at']} with {saved['model']}.")
        return (extract(doc, "CACHED", folder) if folder else []), f"{NOT_AVAILABLE} ({reason})."
    save_live(folder, doc, result)
    note = "" if result["valid"] else " The answer did not match the schema, so every field needs review."
    return result["fields"], f"Read with AI ({result['model']}, {result['read_at']}).{note}"
