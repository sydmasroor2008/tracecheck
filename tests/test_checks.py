"""Tests for the reconciliation checks."""

import copy

import pytest

from tracecheck import checks, data

CFG = data.load_config()


def facility(folder, approve_all=False):
    fields = data.load_fields(folder, saved=False)
    if approve_all:
        for f in fields:
            f["approved"] = True
    return data.build_facility(fields, CFG)


def expected(folder):
    return data.read_json(data.folder_path(folder) / "expected_results.json")


@pytest.mark.parametrize("approve_all", [False, True])
@pytest.mark.parametrize("folder", data.FOLDERS)
def test_folders_match_expected_flags(folder, approve_all):
    flags = checks.run_all(facility(folder, approve_all), CFG)
    assert sorted(f["id"] for f in flags) == expected(folder)["flags"]


def test_clean_and_trader_have_zero_flags():
    assert checks.run_all(facility("clean"), CFG) == []
    assert checks.run_all(facility("trader"), CFG) == []


def test_problem_messages_and_sources():
    flags = {f["id"]: f for f in checks.run_all(facility("problem"), CFG)}
    assert flags["MASS_BALANCE"]["message"].startswith(
        "200 t of steel was used, but product and scrap explain 185 t. 15 t is unexplained.")
    assert "covers 2025" in flags["PRECURSOR_EVIDENCE"]["message"]
    assert "produced in 2026" in flags["PRECURSOR_EVIDENCE"]["message"]
    assert flags["FUEL_UNIT"]["message"].startswith("The August natural gas invoice is in kg; the others are in GJ.")
    assert "Heat A2 shows Mn 0.02% and Cr 0.85%" in flags["CHEMISTRY_RANGE"]["message"]
    assert "X9" in flags["CERT_NO_PURCHASE"]["message"] and "Link missing" in flags["CERT_NO_PURCHASE"]["message"]
    for f in flags.values():
        assert f["sources"], f["id"]
        assert f["severity"] in ("high", "medium", "low")
        assert f["status"] == "open"


# ---- one small hand-built case per check

def small():
    return {
        "reporting_year": 2026,
        "stock": {"opening": [{"heat": "H0", "tonnes": 10}], "closing": [{"heat": "H1", "tonnes": 5}]},
        "purchases": [{"invoice_no": "P1", "supplier": "Mill X", "supplier_type": "mill", "heat": "H1",
                       "tonnes": 100, "emissions_claim": "actual"}],
        "delivery_notes": [],
        "certificates": [
            {"cert_no": "C0", "heat": "H0", "grade": "G", "production_date": "2026-01-01",
             "chemistry": {"Mn": 0.8, "Cr": 0.1, "Ni": 0.1, "other": 0.02}},
            {"cert_no": "C1", "heat": "H1", "grade": "G", "production_date": "2026-02-01",
             "chemistry": {"Mn": 0.8, "Cr": 0.1, "Ni": 0.1, "other": 0.02}}],
        "verification_reports": [{"mill": "Mill X", "period_year": 2026}],
        "production": [{"month": "2026-01", "tonnes": 90}],
        "scrap": {"tonnes": 15, "pre_consumer_share": 1.0},
        "fuel": [{"invoice_no": "G1", "month": "2026-01", "fuel": "gas", "unit": "GJ"},
                 {"invoice_no": "G2", "month": "2026-02", "fuel": "gas", "unit": "GJ"}],
        "shipments": [{"invoice_no": "E1", "date": "2026-03-01"}],
    }


SMALL_CFG = {"mass_balance_tolerance": 0.02, "grade_ranges": {"G": {"Mn": [0.7, 1.0], "Cr": [0, 0.2]}}}


def test_small_case_is_clean():
    assert checks.run_all(small(), SMALL_CFG) == []


def test_mass_balance_gap_and_ratio_below_one():
    fac = small()
    fac["scrap"]["tonnes"] = 0
    assert [f["id"] for f in checks.check_mass_balance(fac, SMALL_CFG)] == ["MASS_BALANCE"]
    fac = small()
    fac["production"][0]["tonnes"] = 110
    fac["scrap"]["tonnes"] = -5
    msgs = [f["message"] for f in checks.check_mass_balance(fac, SMALL_CFG)]
    assert any("below 1" in m for m in msgs)


def test_mass_balance_within_tolerance():
    fac = small()
    fac["scrap"]["tonnes"] = 14       # 1 t gap on 105 t, under 2 percent
    assert checks.check_mass_balance(fac, SMALL_CFG) == []


def test_mass_balance_missing_value():
    fac = small()
    fac["scrap"]["tonnes"] = None
    assert checks.check_mass_balance(fac, SMALL_CFG)[0]["severity"] == "low"


def test_cert_links_both_ways():
    fac = small()
    fac["certificates"].append(copy.deepcopy(fac["certificates"][0]) | {"cert_no": "C9", "heat": "H9"})
    fac["purchases"].append({"invoice_no": "P2", "heat": "H2", "tonnes": 1})
    ids = sorted(f["id"] for f in checks.check_cert_links(fac))
    assert ids == ["CERT_NO_PURCHASE", "PURCHASE_NO_CERT"]


def test_delivery_note_resolves_cert_link():
    fac = small()
    fac["certificates"].append(copy.deepcopy(fac["certificates"][0]) | {"cert_no": "C9", "heat": "H9"})
    fac["delivery_notes"].append({"supplier": "Trader", "mill": "Mill Y", "heats": ["H9"]})
    assert checks.check_cert_links(fac) == []


def test_precursor_evidence_wrong_year():
    fac = small()
    fac["verification_reports"][0]["period_year"] = 2025
    out = checks.check_precursor_evidence(fac)
    assert [f["id"] for f in out] == ["PRECURSOR_EVIDENCE"] and "covers 2025" in out[0]["message"]


def test_precursor_evidence_no_claim_no_flag():
    fac = small()
    fac["purchases"][0]["emissions_claim"] = None
    fac["verification_reports"] = []
    assert checks.check_precursor_evidence(fac) == []


def test_reporting_period():
    fac = small()
    fac["production"][0]["month"] = "2025-12"
    fac["shipments"][0]["date"] = "2027-01-02"
    assert len(checks.check_reporting_period(fac)) == 2


def test_fuel_unit():
    fac = small()
    fac["fuel"][1]["unit"] = "kg"
    out = checks.check_fuel_unit(fac)
    assert out[0]["message"].startswith("The February gas invoice is in kg; the others are in GJ.")


def test_chemistry_range():
    fac = small()
    fac["certificates"][1]["chemistry"].update(Mn=0.02, Cr=0.85)
    out = checks.check_chemistry(fac, SMALL_CFG)
    assert len(out) == 1 and "Heat H1 shows Mn 0.02% and Cr 0.85%" in out[0]["message"]


def test_params_missing():
    fac = small()
    fac["certificates"][0]["chemistry"]["Ni"] = None
    fac["scrap"]["pre_consumer_share"] = None
    out = checks.check_params_missing(fac)
    assert len(out) == 1 and "Ni % for heat H0" in out[0]["message"]
    assert "pre-consumer" in out[0]["message"]


def test_accept_with_note():
    fac = small()
    fac["scrap"]["tonnes"] = 0
    flags = checks.apply_notes(checks.run_all(fac, SMALL_CFG), {"MASS_BALANCE:1": "scrap counted late"})
    assert flags[0]["status"] == "accepted with note" and flags[0]["note"] == "scrap counted late"
