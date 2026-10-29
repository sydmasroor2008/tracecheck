"""Reconciliation checks. Each check is a pure function: facility data in, flags out.

A flag says what looks wrong in plain English and names the source documents.
A missing link is a "link missing", never an accusation.
"""

import calendar
from collections import Counter

from tracecheck.data import sources_for


def flag(flag_id: str, severity: str, message: str, sources: list) -> dict:
    return {"id": flag_id, "severity": severity, "message": message,
            "sources": list(sources), "status": "open", "note": ""}


def t(x: float) -> str:
    return f"{round(x, 3):g} t"


def _list(fac: dict, *path) -> list:
    obj = fac
    for p in path:
        obj = (obj or {}).get(p)
    return [x for x in (obj or []) if x is not None]


def _src(fac: dict, key: str) -> list:
    src = fac.get("_sources", {}).get(key)
    return [src] if src else []


def check_mass_balance(fac: dict, cfg: dict) -> list:
    opening = [r.get("tonnes") for r in _list(fac, "stock", "opening")]
    closing = [r.get("tonnes") for r in _list(fac, "stock", "closing")]
    bought = [p.get("tonnes") for p in _list(fac, "purchases")]
    product = [r.get("tonnes") for r in _list(fac, "production")]
    scrap = (fac.get("scrap") or {}).get("tonnes")
    src = sources_for(fac, "stock.opening", "stock.closing", "purchases", "production", "scrap")
    if not product or any(v is None for v in opening + closing + bought + product + [scrap]):
        return [flag("MASS_BALANCE", "low",
                     "The steel balance cannot be checked yet: some stock, purchase, production "
                     "or scrap figures are missing or awaiting review.", src)]
    consumed = sum(opening) + sum(bought) - sum(closing)
    explained = sum(product) + scrap
    gap = consumed - explained
    flags = []
    if abs(gap) > cfg["mass_balance_tolerance"] * consumed:
        what = "is unexplained" if gap > 0 else "more is explained than was used"
        flags.append(flag("MASS_BALANCE", "high",
                          f"{t(consumed)} of steel was used, but product and scrap explain {t(explained)}. "
                          f"{t(abs(gap))} {what}. Check the scrap register and stock counts.", src))
    if consumed < sum(product):
        flags.append(flag("MASS_BALANCE", "high",
                          f"Less steel was used ({t(consumed)}) than product made ({t(sum(product))}), so the "
                          "mass ratio is below 1. Check the production register and stock counts.", src))
    return flags


def check_cert_links(fac: dict) -> list:
    certs = [(i, c) for i, c in enumerate(fac.get("certificates") or []) if c and c.get("heat")]
    purchase_heats = {p.get("heat") for p in _list(fac, "purchases")}
    note_heats = {h for n in _list(fac, "delivery_notes") for h in (n.get("heats") or [])}
    stock_heats = {r.get("heat") for r in _list(fac, "stock", "opening") + _list(fac, "stock", "closing")}
    flags = []
    for i, c in certs:
        if c["heat"] not in purchase_heats | note_heats | stock_heats:
            flags.append(flag("CERT_NO_PURCHASE", "medium",
                              f"Mill certificate {c.get('cert_no')} for heat {c['heat']} matches no purchase "
                              "invoice, delivery note or stock register. Link missing: find the purchase "
                              "record, or set the certificate aside.", _src(fac, f"certificates[{i}].heat")))
    cert_heats = {c["heat"] for _, c in certs}
    for i, p in enumerate(fac.get("purchases") or []):
        if p and p.get("heat") and p["heat"] not in cert_heats:
            flags.append(flag("PURCHASE_NO_CERT", "medium",
                              f"Heat {p['heat']} on purchase invoice {p.get('invoice_no')} has no mill "
                              "certificate. Link missing: ask the supplier for the certificate.",
                              _src(fac, f"purchases[{i}].heat")))
    for side in ("opening", "closing"):
        for i, r in enumerate((fac.get("stock") or {}).get(side) or []):
            if r and r.get("heat") and r["heat"] not in cert_heats:
                flags.append(flag("PURCHASE_NO_CERT", "medium",
                                  f"Heat {r['heat']} in the {side} stock has no mill certificate. "
                                  "Link missing: find the certificate.", _src(fac, f"stock.{side}[{i}].heat")))
    return flags


def _year(date) -> int:
    try:
        return int(str(date)[:4])
    except ValueError:
        return None


def check_precursor_evidence(fac: dict) -> list:
    reports = _list(fac, "verification_reports")
    cert_year = {c.get("heat"): _year(c.get("production_date")) for c in _list(fac, "certificates")}
    gaps = {}
    for i, p in enumerate(fac.get("purchases") or []):
        if not p or str(p.get("emissions_claim") or "").lower() != "actual":
            continue
        mill, year = p.get("supplier"), cert_year.get(p.get("heat"))
        if not any(r.get("mill") == mill and r.get("period_year") == year for r in reports):
            heats, src = gaps.setdefault((mill, year), ([], []))
            heats.append(p.get("heat"))
            src += _src(fac, f"purchases[{i}].emissions_claim")
    flags = []
    for (mill, year), (heats, src) in gaps.items():
        years = sorted({r.get("period_year") for r in reports if r.get("mill") == mill})
        src += sources_for(fac, "verification_reports")
        when = year if year is not None else "the production year"
        if years:
            msg = (f"The verification report from {mill} covers {', '.join(map(str, years))}, but this steel "
                   f"(heats {', '.join(heats)}) was produced in {when}. The default value applies until a "
                   f"{when} report is received.")
        else:
            msg = (f"{mill} states actual emissions for heats {', '.join(heats)}, but no verification report "
                   f"was found. The default value applies until a report covering {when} is received.")
        flags.append(flag("PRECURSOR_EVIDENCE", "high", msg, src))
    return flags


def check_reporting_period(fac: dict) -> list:
    year = fac.get("reporting_year")
    flags = []
    for i, r in enumerate(fac.get("production") or []):
        if r and r.get("month") and _year(r["month"]) != year:
            flags.append(flag("REPORTING_PERIOD", "medium",
                              f"Production row {r['month']} is outside the reporting year {year}. "
                              "Remove it or move it to the right year.", _src(fac, f"production[{i}].month")))
    for i, s in enumerate(fac.get("shipments") or []):
        if s and s.get("date") and _year(s["date"]) != year:
            flags.append(flag("REPORTING_PERIOD", "medium",
                              f"Export invoice {s.get('invoice_no')} is dated {s['date']}, outside the "
                              f"reporting year {year}.", _src(fac, f"shipments[{i}].date")))
    return flags


def _month_name(f: dict) -> str:
    """'2026-08' -> 'August'; falls back to the invoice number for anything else."""
    try:
        return calendar.month_name[int(str(f.get("month"))[5:7])]
    except (ValueError, IndexError):
        return str(f.get("invoice_no") or "one")


def check_fuel_unit(fac: dict) -> list:
    by_fuel = {}
    for i, f in enumerate(fac.get("fuel") or []):
        if f and f.get("fuel") and f.get("unit"):
            by_fuel.setdefault(f["fuel"], []).append((i, f))
    flags = []
    for fuel, rows in by_fuel.items():
        units = Counter(f["unit"] for _, f in rows)
        if len(units) < 2:
            continue
        main = units.most_common(1)[0][0]
        odd = [(i, f) for i, f in rows if f["unit"] != main]
        months = " and ".join(_month_name(f) for _, f in odd)
        unit = ", ".join(sorted({f["unit"] for _, f in odd}))
        verb = "invoice is" if len(odd) == 1 else "invoices are"
        flags.append(flag("FUEL_UNIT", "high",
                          f"The {months} {fuel} {verb} in {unit}; the others are in {main}. "
                          "Confirm the unit before using it.",
                          [s for i, _ in odd for s in _src(fac, f"fuel[{i}].unit")]))
    return flags


def check_chemistry(fac: dict, cfg: dict) -> list:
    ranges = cfg.get("grade_ranges") or {}
    flags = []
    for i, c in enumerate(fac.get("certificates") or []):
        if not c or c.get("grade") not in ranges:
            continue
        chem = c.get("chemistry") or {}
        out = [(el, chem[el]) for el, (lo, hi) in ranges[c["grade"]].items()
               if chem.get(el) is not None and not lo <= chem[el] <= hi]
        if out:
            shown = " and ".join(f"{el} {v:g}%" for el, v in out)
            flags.append(flag("CHEMISTRY_RANGE", "medium",
                              f"Heat {c.get('heat')} shows {shown}, outside the {c['grade']} range. The values "
                              "may have been read under the wrong element. Check the original certificate.",
                              _src(fac, f"certificates[{i}].chemistry.Mn")))
    return flags


def check_params_missing(fac: dict) -> list:
    missing, src = [], []
    for i, c in enumerate(fac.get("certificates") or []):
        chem = (c or {}).get("chemistry") or {}
        for el in ("Mn", "Cr", "Ni", "other"):
            if chem.get(el) is None:
                missing.append(f"{el} % for heat {(c or {}).get('heat') or i}")
                src += _src(fac, f"certificates[{i}].chemistry.{el}")
    scrap = fac.get("scrap") or {}
    if scrap.get("tonnes") is None:
        missing.append("scrap tonnes (needed for scrap per tonne of product)")
        src += _src(fac, "scrap.tonnes")
    if scrap.get("pre_consumer_share") is None:
        missing.append("pre-consumer scrap share")
        src += _src(fac, "scrap.pre_consumer_share")
    if not missing:
        return []
    return [flag("PARAMS_MISSING", "medium",
                 "Values the importer needs are missing or awaiting review: " + "; ".join(missing) + ".",
                 list(dict.fromkeys(src)))]


def run_all(fac: dict, cfg: dict) -> list:
    flags = (check_mass_balance(fac, cfg) + check_cert_links(fac) + check_precursor_evidence(fac)
             + check_reporting_period(fac) + check_fuel_unit(fac) + check_chemistry(fac, cfg)
             + check_params_missing(fac))
    counts = Counter()
    for f in flags:
        counts[f["id"]] += 1
        f["key"] = f"{f['id']}:{counts[f['id']]}"
    return flags


def apply_notes(flags: list, notes: dict) -> list:
    """Mark flags the user accepted with a note."""
    for f in flags:
        if notes.get(f["key"]):
            f["status"] = "accepted with note"
            f["note"] = notes[f["key"]]
    return flags
