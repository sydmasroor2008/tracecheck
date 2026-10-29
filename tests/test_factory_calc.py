"""Tests for the synthetic factory's illustrative SEE (tracecheck/factory_calc.py)."""

import pytest

from tracecheck import calc, data
from tracecheck.factory_calc import factory_see
from tracecheck.trace import lots

CFG = data.load_config()


def facility(folder, approve_all=False):
    fields = data.load_fields(folder, saved=False)
    if approve_all:
        for f in fields:
            f["approved"] = True
    return data.build_facility(fields, CFG)


def test_unapproved_field_blocks_calculation():
    fac = facility("clean")
    out = factory_see(fac, lots(fac), defaults={"A0": 2.0, "B1": 2.0, "B2": 2.0})
    assert out["result"].value is None
    assert out["result"].missing.startswith("input missing")
    assert "GI-03" in out["result"].missing and "awaiting review" in out["result"].missing


def test_defaults_not_entered_gives_input_missing():
    fac = facility("clean", approve_all=True)
    out = factory_see(fac, lots(fac))
    assert out["result"].value is None
    assert out["result"].missing == "input missing: default value not entered for A0, B1, B2"


def test_trader_folder_needs_every_default():
    fac = facility("trader", approve_all=True)
    out = factory_see(fac, lots(fac))
    assert out["result"].missing == "input missing: default value not entered for A0, T1, T2, T3, T4, T5"


def test_fuel_unit_problem_blocks_calculation():
    fac = facility("problem", approve_all=True)
    out = factory_see(fac, lots(fac), defaults={h: 2.0 for h in ["A0", "A1", "A2", "A3", "B1", "B2"]})
    assert "GI-08" in out["result"].missing and "kg" in out["result"].missing


def test_result_with_user_defaults_follows_formula():
    fac = facility("clean", approve_all=True)
    lot_list = lots(fac)
    defaults = {"A0": 2.0, "B1": 1.5, "B2": 1.5}       # test inputs, not real default values
    out = factory_see(fac, lot_list, defaults)
    assert out["result"].ok

    # Recompute independently from the facility data.
    product = sum(r["tonnes"] for r in fac["production"])
    gj = sum(f["quantity"] for f in fac["fuel"])
    ef = fac["fuel"][0]["emission_factor_t_per_tj"]
    values = {lot["heat"]: (lot["verified_see"] if lot["status"] == "ACTUAL_ALLOWED" else defaults[lot["heat"]])
              for lot in lot_list}
    consumed = {lot["heat"]: lot["consumed_t"] for lot in lot_list}
    avg = sum(consumed[h] * values[h] for h in values) / sum(consumed.values())
    expected = gj / product / 1000 * ef + sum(consumed.values()) / product * avg
    assert out["result"].value == pytest.approx(calc.round_specific(expected), abs=1e-9)
    assert dict((s[0], s[1]) for s in out["steps"])["Product made"] == 170
