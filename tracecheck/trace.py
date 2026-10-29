"""Trace: shipment -> production month -> heat (lot) -> supplier -> mill, and precursor status.

Precursor status follows docs/REGULATORY_NOTES.md note 5: actual data from a
mill may be used only if a verification report covers the year the steel was
produced; otherwise the default value applies.
"""

ACTUAL_ALLOWED = "ACTUAL_ALLOWED"
DEFAULT_REPORT_PERIOD = "DEFAULT_REPORT_PERIOD"
DEFAULT_NO_EMISSIONS_DATA = "DEFAULT_NO_EMISSIONS_DATA"
NO_MILL_LINK = "NO_MILL_LINK"

STATUS_TEXT = {
    ACTUAL_ALLOWED: "Actual data allowed",
    DEFAULT_REPORT_PERIOD: "Default applies: report does not cover the production year",
    DEFAULT_NO_EMISSIONS_DATA: "Default applies: no emissions data from the mill",
    NO_MILL_LINK: "Default applies: no mill link",
}


def _year(date):
    try:
        return int(str(date)[:4])
    except ValueError:
        return None


def precursor_status(mill, year, reports, supplier, via=None):
    """(status, next action) for one lot."""
    if not mill:
        return NO_MILL_LINK, f"Ask {supplier} for a delivery note naming the mill and heat numbers."
    mill_reports = [r for r in reports if r and r.get("mill") == mill]
    if year is not None and any(r.get("period_year") == year for r in mill_reports):
        return ACTUAL_ALLOWED, "Keep the verification report with the evidence pack."
    if mill_reports:
        return DEFAULT_REPORT_PERIOD, f"Ask {mill} for a verification report covering {year or 'the production year'}."
    if via:
        return DEFAULT_NO_EMISSIONS_DATA, f"Ask {mill} through {via} for verified emissions data, or accept the default."
    return DEFAULT_NO_EMISSIONS_DATA, f"Ask {mill} for verified emissions data, or accept the default."


def lots(fac: dict) -> list:
    """One record per steel lot (heat) consumed in the reporting year."""
    stock = fac.get("stock") or {}
    reports = [r for r in fac.get("verification_reports") or [] if r]
    certs = {c.get("heat"): c for c in fac.get("certificates") or [] if c}
    notes = [n for n in fac.get("delivery_notes") or [] if n]
    closing = {r.get("heat"): r.get("tonnes") or 0 for r in stock.get("closing") or [] if r}
    modes = fac.get("_modes", {})

    entries = [("opening stock", f"stock.opening[{i}]", r) for i, r in enumerate(stock.get("opening") or []) if r]
    entries += [("purchase", f"purchases[{i}]", p) for i, p in enumerate(fac.get("purchases") or []) if p]
    out = []
    for kind, key, row in entries:
        heat = row.get("heat")
        tonnes = row.get("tonnes")
        consumed = None if tonnes is None else tonnes - closing.get(heat, 0)
        via = None
        if kind == "opening stock":
            supplier, mill, link = "opening stock", row.get("mill"), "stock register names the mill"
        elif row.get("supplier_type") == "mill":
            supplier, mill, link = row.get("supplier"), row.get("supplier"), "bought direct from the mill"
        else:
            supplier = via = row.get("supplier")
            note = next((n for n in notes if heat in (n.get("heats") or [])), None)
            mill = note.get("mill") if note else None
            link = f"delivery note {note.get('note_no')} names the mill" if note else "link missing: no delivery note names this heat"
        cert = certs.get(heat) or {}
        year = _year(cert.get("production_date")) if cert else None
        status, action = precursor_status(mill, year, reports, supplier, via)
        see = None
        if status == ACTUAL_ALLOWED:
            see = next(r.get("precursor_see") for r in reports if r.get("mill") == mill and r.get("period_year") == year)
        out.append({"heat": heat, "kind": kind, "supplier": supplier, "mill": mill, "link": link,
                    "production_year": year, "tonnes": tonnes, "consumed_t": consumed,
                    "status": status, "status_text": STATUS_TEXT[status], "next_action": action,
                    "verified_see": see, "mode": modes.get(f"{key}.tonnes")})
    return [lot for lot in out if lot["consumed_t"] is None or lot["consumed_t"] > 0]


def chains(fac: dict, lot_list: list) -> list:
    """Flat rows shipment -> month -> heat -> supplier -> mill, with missing links named."""
    production = {r.get("month"): r for r in fac.get("production") or [] if r}
    by_heat = {lot["heat"]: lot for lot in lot_list}
    rows = []
    for s in fac.get("shipments") or []:
        if not s:
            continue
        base = {"Shipment": s.get("invoice_no"), "Date": s.get("date"), "To": s.get("destination"),
                "CN code": s.get("cn_code"), "Tonnes": s.get("tonnes")}
        months = s.get("production_months")
        if not months:
            rows.append(base | {"Month": "-", "Heat": "-", "Supplier": "-", "Mill": "-", "Status": "-",
                                "Link": "missing: production months not stated or awaiting review"})
            continue
        for m in months:
            heats = (production.get(m) or {}).get("heats")
            if not heats:
                rows.append(base | {"Month": m, "Heat": "-", "Supplier": "-", "Mill": "-", "Status": "-",
                                    "Link": "missing: no production register row lists heats for this month"})
                continue
            for h in heats:
                lot = by_heat.get(h)
                if not lot:
                    rows.append(base | {"Month": m, "Heat": h, "Supplier": "-", "Mill": "-", "Status": "-",
                                        "Link": "missing: heat not on any purchase or stock record"})
                    continue
                rows.append(base | {"Month": m, "Heat": h, "Supplier": lot["supplier"],
                                    "Mill": lot["mill"] or "-", "Status": lot["status"], "Link": lot["link"]})
    return rows
