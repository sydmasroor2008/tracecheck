"""Excel evidence pack (openpyxl). Draft prepared for verifier review.

Six sheets: issue register, precursor status, missing documents, evidence
index, input sheet for the Commission's operator emissions report template,
and assumptions and versions.
"""

import io
import platform
from collections import defaultdict
from importlib import metadata

from openpyxl import Workbook
from openpyxl.styles import Font

from tracecheck.trace import ACTUAL_ALLOWED

HEADER = "Draft prepared for verifier review. Illustrative. Synthetic data."
MISSING = "input missing"


def _sheet(wb, title, columns, rows):
    ws = wb.create_sheet(title)
    ws.append([HEADER])
    ws["A1"].font = Font(bold=True, color="9C0006")
    ws.append(columns)
    for cell in ws[2]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(["" if v is None else (", ".join(map(str, v)) if isinstance(v, list) else v) for v in row])
    for i, col in enumerate(columns, start=1):
        ws.column_dimensions[ws.cell(row=2, column=i).column_letter].width = max(14, min(60, len(col) + 6))
    return ws


def _or_missing(v):
    return MISSING if v is None else v


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def evidence_rows(fields: list, defaults: dict) -> list:
    rows = []
    for f in fields:
        if is_number(f["value"]) and f["approved"]:
            rows.append([f["label"], f["key"], f["value"], f["unit"], f["source_file"], f["page"],
                         f["mode"], f["confidence"], f["reviewer"], f["reviewed_at"]])
    for heat, value in sorted(defaults.items()):
        if value is not None:
            rows.append([f"Default value for heat {heat}", f"defaults.{heat}", value, "t CO2/t",
                         "entered by user in the app", "-", "MANUAL", "-", "entered by user", None])
    return rows


def missing_documents(flags: list, lots: list, fac: dict) -> list:
    rows = []
    for lot in lots:
        if lot["status"] != ACTUAL_ALLOWED:
            rows.append([f"Heat {lot['heat']}", lot["status_text"], lot["next_action"]])
    for f in flags:
        if f["id"] in ("CERT_NO_PURCHASE", "PURCHASE_NO_CERT", "PRECURSOR_EVIDENCE", "PARAMS_MISSING"):
            rows.append([f["id"], f["message"], "See the issue register."])
    for key in fac.get("_pending", []):
        rows.append([key, "Field awaiting review", f"Approve or correct it in the review screen ({fac['_sources'].get(key)})."])
    return rows


def input_rows(fac: dict, lots: list, calc: dict) -> list:
    rows = []
    production = [r for r in fac.get("production") or [] if r]
    complete = production and all(r.get("tonnes") is not None and r.get("cn_code") for r in production)
    by_cn = defaultdict(float)
    for r in production if complete else []:
        by_cn[r["cn_code"]] += r["tonnes"]
    for cn, t in sorted(by_cn.items()) if complete else [("per code", None)]:
        rows.append(["Production", f"CN {cn}", _or_missing(t), "t", "production register"])
    product = None if not production or any(r.get("tonnes") is None for r in production) \
        else sum(r["tonnes"] for r in production)
    rows.append(["Production", "Total product made", _or_missing(product), "t", "production register"])

    consumed = None if any(lot["consumed_t"] is None for lot in lots) else sum(lot["consumed_t"] for lot in lots)
    rows.append(["Precursor", "Steel rod consumed (CN 7213)", _or_missing(consumed), "t", "stock register and purchases"])
    mi = dict((label, v) for label, v, _ in calc["steps"]).get("Mass ratio mi")
    rows.append(["Precursor", "Mass ratio mi", _or_missing(mi), "t/t", "calculated"])

    fuel = [f for f in fac.get("fuel") or [] if f]
    gj = None if any(f.get("quantity") is None or f.get("unit") != "GJ" for f in fuel) or not fuel \
        else sum(f["quantity"] for f in fuel)
    factors = {f.get("emission_factor_t_per_tj") for f in fuel} - {None}
    rows.append(["Fuel", "Natural gas (stationary combustion)", _or_missing(gj), "GJ", "gas invoices"])
    rows.append(["Fuel", "Emission factor", factors.pop() if len(factors) == 1 else MISSING, "t CO2/TJ",
                 "gas invoice footer (Commission example value, synthetic stand-in)"])

    certs = {c.get("heat"): c for c in fac.get("certificates") or [] if c}
    for lot in lots:
        chem = (certs.get(lot["heat"]) or {}).get("chemistry") or {}
        for el in ("Mn", "Cr", "Ni", "other"):
            rows.append(["Steel parameters", f"Heat {lot['heat']}: {el}", _or_missing(chem.get(el)), "% by mass",
                         "mill certificate"])
    scrap = fac.get("scrap") or {}
    per_t = None if scrap.get("tonnes") is None or not product else scrap["tonnes"] / product
    rows.append(["Steel parameters", "Scrap per tonne of product", _or_missing(per_t and round(per_t, 5)), "t/t",
                 "scrap register / production register"])
    rows.append(["Steel parameters", "Pre-consumer scrap share", _or_missing(scrap.get("pre_consumer_share")),
                 "fraction", "scrap register"])

    suppliers = defaultdict(list)
    for lot in lots:
        suppliers[(lot["supplier"], lot["mill"] or "-")].append(f"{lot['heat']}: {lot['status']}")
    for (supplier, mill), items in sorted(suppliers.items()):
        rows.append(["Supplier evidence", f"{supplier} / mill {mill}", "; ".join(items), "", "trace"])

    result = calc["result"]
    rows.append(["Result", "Specific embedded emissions (illustrative, for evidence preparation)",
                 result.value if result.ok else result.missing, "t CO2/t", "calculated"])
    return rows


def versions() -> list:
    rows = [["Python", platform.python_version()]]
    for pkg in ("streamlit", "pandas", "pydantic", "openpyxl", "reportlab", "pillow", "pyyaml"):
        try:
            rows.append([pkg, metadata.version(pkg)])
        except metadata.PackageNotFoundError:
            rows.append([pkg, "not installed"])
    return rows


def build_pack(folder: str, fields: list, fac: dict, flags: list, lots: list, calc: dict,
               cfg: dict, defaults: dict = None) -> bytes:
    defaults = defaults or {}
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "1 Issue register", ["Flag", "Severity", "Message", "Sources", "Status", "Note"],
           [[f["id"], f["severity"], f["message"], f["sources"], f["status"], f["note"]] for f in flags])
    _sheet(wb, "2 Precursor status",
           ["Heat", "Supplier", "Mill", "Production year", "Consumed t", "Status", "Next action", "Mode"],
           [[lot["heat"], lot["supplier"], lot["mill"], lot["production_year"], lot["consumed_t"],
             lot["status"], lot["next_action"], lot["mode"]] for lot in lots])
    _sheet(wb, "3 Missing documents", ["Item", "What is missing", "What to ask for"],
           missing_documents(flags, lots, fac))
    _sheet(wb, "4 Evidence index", ["Field", "Key", "Value", "Unit", "Source file", "Page", "Mode",
                                    "Confidence", "Reviewer", "Reviewed at"], evidence_rows(fields, defaults))
    _sheet(wb, "5 Input sheet", ["Section", "Field", "Value", "Unit", "From"], input_rows(fac, lots, calc))
    assumptions = [
        ["Demo folder", folder],
        ["Reporting year", cfg["reporting_year"]],
        ["Mass-balance tolerance (illustrative)", cfg["mass_balance_tolerance"]],
        ["Review confidence threshold", cfg["review_confidence_threshold"]],
        ["Grade ranges (illustrative, synthetic)", str(cfg.get("grade_ranges"))],
        ["Verified precursor value", "Commission worked-example value used as a synthetic stand-in; "
                                     "not a real mill, not a default value"],
        ["Default values", "Not shipped with the app. Any value shown was entered by the user."],
        ["Scope", "Direct emissions only; stationary combustion only; electricity not tracked."],
    ] + versions()
    _sheet(wb, "6 Assumptions", ["Item", "Value"], assumptions)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
