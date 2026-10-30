"""Tests for the extraction interface and the review state."""

import pytest

from tools.measure_extraction import measure
from tracecheck import data
from tracecheck.extract import LiveNotConfigured, extract, make_client


@pytest.mark.parametrize("folder", data.FOLDERS)
def test_cached_loads_every_document(folder):
    docs = data.load_documents(folder)
    assert len(docs) > 30
    for doc in docs:
        fields = extract(doc["file"], "CACHED", folder)
        assert fields, doc["file"]
        assert all(f["mode"] == "CACHED" for f in fields)


def test_low_confidence_fields_need_review():
    fields = {f["key"]: f for f in data.load_fields("clean", saved=False)}
    pending = sorted(k for k, f in fields.items() if f["needs_review"])
    assert "stock.count_note" in pending                   # handwritten note
    assert "shipments[2].tonnes" in pending                # under the stamp
    assert "fuel[2].quantity" in pending                   # rotated photo
    for key in pending:
        assert fields[key]["confidence"] < 0.85
        assert not fields[key]["approved"]
    others = [f for f in fields.values() if not f["needs_review"]]
    assert all(f["confidence"] >= 0.95 and f["approved"] for f in others)


def test_unapproved_field_is_missing_in_facility_data():
    fac = data.build_facility(data.load_fields("clean", saved=False), data.load_config())
    assert fac["fuel"][2]["quantity"] is None
    assert "fuel[2].quantity" in fac["_pending"]
    assert fac["fuel"][1]["quantity"] is not None


def test_manual_mode_marks_values():
    fields = extract("GI-03.jpg", "MANUAL", manual_values={"fuel[2].quantity": 49.0})
    assert fields[0]["mode"] == "MANUAL" and fields[0]["value"] == 49.0


def test_live_client_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LiveNotConfigured, match="LIVE mode not configured"):
        make_client()


def test_measure_extraction_cached():
    scores = measure("clean")
    assert all(correct == total for correct, total in scores.values())
