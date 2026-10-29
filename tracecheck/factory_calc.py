"""Illustrative specific embedded emissions for the synthetic factory, using calc.py.

Own direct = approved gas GJ / product t, times the emission factor.
Precursor SEE = mass-weighted average over consumed lots (note 6): lots with
ACTUAL_ALLOWED use the verified value, all others need a default value.
Default values are not shipped with the app. Until the user types one, the
result is "input missing". Illustrative, for evidence preparation.
"""

from tracecheck.calc import (Result, mass_ratio, own_direct_per_tonne, round_specific,
                             specific_embedded_emissions, weighted_average_see)
from tracecheck.trace import ACTUAL_ALLOWED


def factory_see(fac: dict, lot_list: list, defaults: dict = None) -> dict:
    """{'result': Result, 'steps': [(label, value, unit)], 'lot_values': [...]}

    defaults: heat -> default value typed by the user (MANUAL, "entered by user").
    """
    defaults = defaults or {}
    missing, steps = [], []

    production = [r for r in fac.get("production") or [] if r]
    product = [r.get("tonnes") for r in production]
    if not product or None in product:
        missing.append("production tonnes (missing or awaiting review)")

    gj = 0.0
    sources = fac.get("_sources", {})
    for i, f in enumerate(fac.get("fuel") or []):
        if not f:
            continue
        name = f.get("invoice_no") or sources.get(f"fuel[{i}].quantity") or "a fuel invoice"
        if f.get("quantity") is None:
            missing.append(f"fuel quantity on {name} (missing or awaiting review)")
        elif f.get("unit") != "GJ":
            missing.append(f"fuel quantity on {name} in GJ (stated in {f.get('unit') or 'no unit'}; confirm the unit)")
        else:
            gj += f["quantity"]
    factors = {f.get("emission_factor_t_per_tj") for f in fac.get("fuel") or [] if f} - {None}
    if len(factors) != 1:
        missing.append("one confirmed fuel emission factor in t CO2 per TJ")

    lot_values, no_default = [], []
    for lot in lot_list:
        if lot["status"] == ACTUAL_ALLOWED:
            value, basis = lot["verified_see"], ("value from the mill's verification report "
                                                 "(synthetic stand-in: Commission example value)")
        else:
            value, basis = defaults.get(lot["heat"]), "default value entered by user"
        if value is None:
            no_default.append(lot["heat"])
        if lot["consumed_t"] is None:
            missing.append(f"consumed tonnes for heat {lot['heat']}")
        lot_values.append({"heat": lot["heat"], "consumed_t": lot["consumed_t"], "see": value,
                           "basis": basis, "status": lot["status"]})
    if no_default:
        missing.append("default value not entered for " + ", ".join(no_default))
    if not lot_list:
        missing.append("at least one steel lot")

    if missing:
        return {"result": Result(None, "input missing: " + "; ".join(missing)), "steps": steps,
                "lot_values": lot_values}

    product_t = sum(product)
    consumed_t = sum(v["consumed_t"] for v in lot_values)
    ef = factors.pop()
    gj_per_t = gj / product_t
    own = own_direct_per_tonne(gj_per_t, ef)
    mi = mass_ratio(consumed_t, product_t)
    avg = weighted_average_see([(v["heat"], v["consumed_t"], v["see"]) for v in lot_values])
    for r in (own, mi, avg):
        if not r.ok:
            return {"result": r, "steps": steps, "lot_values": lot_values}
    see = specific_embedded_emissions(own.value, [("steel rod", mi.value, avg.value)])
    steps += [
        ("Product made", product_t, "t"),
        ("Natural gas used", gj, "GJ"),
        ("Gas per tonne of product", round_specific(gj_per_t), "GJ/t"),
        ("Emission factor", ef, "t CO2/TJ"),
        ("Own direct emissions per tonne", round_specific(own.value), "t CO2/t"),
        ("Steel consumed (including the part that became scrap)", consumed_t, "t"),
        ("Mass ratio mi", round_specific(mi.value), "t/t"),
        ("Precursor SEE, mass-weighted average", round_specific(avg.value), "t CO2/t"),
    ]
    if not see.ok:
        return {"result": see, "steps": steps, "lot_values": lot_values}
    return {"result": Result(round_specific(see.value)), "steps": steps, "lot_values": lot_values}
