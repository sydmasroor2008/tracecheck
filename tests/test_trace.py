"""Tests for the trace chain and precursor status."""

import pytest

from tracecheck import data, trace


def facility(folder):
    return data.build_facility(data.load_fields(folder), data.load_config())


@pytest.mark.parametrize("folder", data.FOLDERS)
def test_statuses_match_expected(folder):
    exp = data.read_json(data.folder_path(folder) / "expected_results.json")
    lots = trace.lots(facility(folder))
    assert {lot["heat"]: lot["status"] for lot in lots} == exp["statuses"]
    assert {lot["heat"]: lot["consumed_t"] for lot in lots} == exp["consumed_t"]


def test_clean_shows_three_verdicts_with_actions():
    lots = {lot["heat"]: lot for lot in trace.lots(facility("clean"))}
    assert {lot["status"] for lot in lots.values()} == {
        trace.ACTUAL_ALLOWED, trace.DEFAULT_REPORT_PERIOD, trace.DEFAULT_NO_EMISSIONS_DATA}
    assert lots["A1"]["next_action"] == "Keep the verification report with the evidence pack."
    assert lots["A0"]["next_action"] == "Ask Example Steel Mill A, synthetic for a verification report covering 2025."
    assert lots["B1"]["next_action"] == ("Ask Example Steel Mill B, synthetic through Example Steel Traders, "
                                         "synthetic for verified emissions data, or accept the default.")
    assert lots["A1"]["mode"] == "CACHED"


def test_no_mill_link():
    fac = {"purchases": [{"invoice_no": "P1", "supplier": "Trader T", "supplier_type": "trader",
                          "heat": "H1", "tonnes": 10}],
           "certificates": [{"heat": "H1", "production_date": "2026-01-01"}]}
    lot = trace.lots(fac)[0]
    assert lot["status"] == trace.NO_MILL_LINK
    assert lot["next_action"] == "Ask Trader T for a delivery note naming the mill and heat numbers."


def test_chains_link_every_shipment():
    fac = facility("clean")
    rows = trace.chains(fac, trace.lots(fac))
    assert {r["Shipment"] for r in rows} == {f"EX-{n:02d}" for n in range(1, 9)}
    assert not [r for r in rows if r["Link"].startswith("missing")]
    assert {r["Heat"] for r in rows} == {"A0", "A1", "A2", "A3", "B1", "B2"}


def test_chain_names_missing_link():
    fac = facility("clean")
    fac["shipments"][0]["production_months"] = None
    rows = trace.chains(fac, trace.lots(fac))
    assert rows[0]["Link"].startswith("missing: production months")


def test_closing_count_awaiting_review_leaves_consumed_unknown():
    fac = facility("clean")
    fac["stock"]["closing"][0]["tonnes"] = None
    b2 = next(lot for lot in trace.lots(fac) if lot["heat"] == "B2")
    assert b2["consumed_t"] is None
