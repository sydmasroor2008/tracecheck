"""Tests for the synthetic factory (tools/make_factory.py)."""

import json

import pytest

from tools import make_factory as mf
from tracecheck.data import DATA


def gt(folder):
    with open(DATA / folder / "ground_truth.json", encoding="utf-8") as f:
        return json.load(f)


def test_seed_gives_identical_ground_truth():
    for folder in mf.FOLDERS:
        assert mf.build_ground_truth(folder) == mf.build_ground_truth(folder)


def test_committed_data_matches_generator():
    for folder in mf.FOLDERS:
        fresh = mf.build_ground_truth(folder)
        fresh["documents"] = [d["file"] for d in mf.document_specs(fresh)]
        assert gt(folder) == fresh, f"run python tools/make_factory.py to refresh data/{folder}"


@pytest.mark.parametrize("folder", ["clean", "trader"])
def test_totals(folder):
    g = gt(folder)
    opening = sum(r["tonnes"] for r in g["stock"]["opening"])
    closing = sum(r["tonnes"] for r in g["stock"]["closing"])
    bought = sum(p["tonnes"] for p in g["purchases"])
    assert opening + bought - closing == 200
    assert sum(r["tonnes"] for r in g["production"]) == 170
    assert len(g["production"]) == 12
    assert sum(f["quantity"] for f in g["fuel"]) == pytest.approx(595)
    assert len(g["fuel"]) == 12
    assert sum(s["tonnes"] for s in g["shipments"]) == 160
    assert len(g["shipments"]) == 8
    assert g["scrap"]["tonnes"] == 30


def test_clean_lots_and_mill_links():
    g = gt("clean")
    assert sorted(c["heat"] for c in g["certificates"]) == ["A0", "A1", "A2", "A3", "B1", "B2"]
    assert g["delivery_notes"][0]["mill"] == mf.MILL_B
    assert g["delivery_notes"][0]["heats"] == ["B1", "B2"]
    assert g["stock"]["closing"] == [{"heat": "B2", "tonnes": 10, "mill": mf.MILL_B}]


def test_trader_folder():
    g = gt("trader")
    assert {p["heat"] for p in g["purchases"]} == {"T1", "T2", "T3", "T4", "T5"}
    assert all(p["supplier"] == mf.TRADER for p in g["purchases"])
    noted = {h for n in g["delivery_notes"] for h in n["heats"]}
    assert noted == {"T1", "T2", "T3", "T4", "T5"}


def chem(g, heat):
    return next(c for c in g["certificates"] if c["heat"] == heat)["chemistry"]


def test_planted_issues_present_in_problem_absent_in_clean():
    clean, problem = gt("clean"), gt("problem")
    # MASS_BALANCE
    assert clean["scrap"]["tonnes"] == 30 and problem["scrap"]["tonnes"] == 15
    # CERT_NO_PURCHASE
    assert "X9" not in {c["heat"] for c in clean["certificates"]}
    assert "X9" in {c["heat"] for c in problem["certificates"]}
    assert "X9" not in {p["heat"] for p in problem["purchases"]}
    # PRECURSOR_EVIDENCE
    assert clean["verification_reports"][0]["period_year"] == 2026
    assert problem["verification_reports"][0]["period_year"] == 2025
    # FUEL_UNIT
    assert {f["unit"] for f in clean["fuel"]} == {"GJ"}
    assert [f["month"] for f in problem["fuel"] if f["unit"] != "GJ"] == ["2026-08"]
    # CHEMISTRY_RANGE: Mn and Cr swapped on A2
    assert chem(clean, "A2")["Mn"] > chem(clean, "A2")["Cr"]
    assert (chem(problem, "A2")["Mn"], chem(problem, "A2")["Cr"]) == (0.02, 0.85)
    assert problem["planted_issues"] == mf.PLANTED and clean["planted_issues"] == []


def test_problem_changes_nothing_else():
    clean, problem = gt("clean"), gt("problem")
    for key in ["purchases", "delivery_notes", "production", "stock", "shipments"]:
        assert clean[key] == problem[key]


@pytest.mark.parametrize("folder", mf.FOLDERS)
def test_documents_exist_and_say_synthetic(folder):
    g = gt(folder)
    assert len(g["documents"]) > 30
    for name in g["documents"]:
        path = DATA / folder / "docs" / name
        assert path.exists(), name
        if path.suffix == ".pdf":
            assert b"SYNTHETIC" in path.read_bytes(), name
    assert sum(name.endswith(".jpg") for name in g["documents"]) == 2


def test_three_certificate_layouts():
    layouts = {c["layout"] for c in gt("clean")["certificates"]}
    assert layouts == {"across", "down", "two_column"}


def test_expected_results_generated():
    with open(DATA / "clean" / "expected_results.json", encoding="utf-8") as f:
        exp = json.load(f)
    assert exp["flags"] == []
    assert exp["statuses"] == {"A0": "DEFAULT_REPORT_PERIOD", "A1": "ACTUAL_ALLOWED",
                               "A2": "ACTUAL_ALLOWED", "A3": "ACTUAL_ALLOWED",
                               "B1": "DEFAULT_NO_EMISSIONS_DATA", "B2": "DEFAULT_NO_EMISSIONS_DATA"}
