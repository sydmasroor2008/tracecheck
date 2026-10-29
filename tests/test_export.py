"""Tests for the Excel evidence pack."""

import io

import pytest
from openpyxl import load_workbook

from tracecheck import checks, data, export
from tracecheck.factory_calc import factory_see
from tracecheck.trace import lots

CFG = data.load_config()


def pack(folder, defaults=None):
    fields = data.load_fields(folder, saved=False)
    fac = data.build_facility(fields, CFG)
    lot_list = lots(fac)
    flags = checks.run_all(fac, CFG)
    calc = factory_see(fac, lot_list, defaults)
    return load_workbook(io.BytesIO(export.build_pack(folder, fields, fac, flags, lot_list, calc, CFG, defaults)))


@pytest.mark.parametrize("folder", data.FOLDERS)
def test_pack_opens_with_header_on_every_sheet(folder):
    wb = pack(folder)
    assert len(wb.sheetnames) == 6
    for ws in wb.worksheets:
        assert ws["A1"].value == export.HEADER


def test_every_number_in_evidence_index_has_a_source():
    wb = pack("clean", defaults={"A0": 2.0})
    ws = wb["4 Evidence index"]
    head = [c.value for c in ws[2]]
    rows = [dict(zip(head, (c.value for c in r))) for r in ws.iter_rows(min_row=3)]
    assert len(rows) > 50
    for r in rows:
        assert isinstance(r["Value"], (int, float))
        assert r["Source file"] and r["Mode"] in ("CACHED", "MANUAL", "LIVE")
    assert any(r["Source file"] == "entered by user in the app" for r in rows)


def test_problem_issue_register_and_input_missing():
    wb = pack("problem")
    ids = [r[0].value for r in wb["1 Issue register"].iter_rows(min_row=3)]
    assert sorted(ids) == sorted(["MASS_BALANCE", "CERT_NO_PURCHASE", "PRECURSOR_EVIDENCE",
                                  "FUEL_UNIT", "CHEMISTRY_RANGE"])
    values = {r[1].value: r[2].value for r in wb["5 Input sheet"].iter_rows(min_row=3)}
    assert values["Natural gas (stationary combustion)"] == "input missing"
    result = values["Specific embedded emissions (illustrative, for evidence preparation)"]
    assert result.startswith("input missing")


def test_precursor_status_sheet_lists_all_lots():
    heats = [r[0].value for r in pack("clean")["2 Precursor status"].iter_rows(min_row=3)]
    assert heats == ["A0", "A1", "A2", "A3", "B1", "B2"]
