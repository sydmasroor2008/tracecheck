"""LIVE extraction with a mocked Gemini client. No test needs the network or the key."""

import json
from types import SimpleNamespace

import pytest

from tracecheck import data, extract
from tracecheck.checks import run_all


class FakeClient:
    def __init__(self, text):
        self.calls = []

        def generate_content(**kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(text=text)
        self.models = SimpleNamespace(generate_content=generate_content)


class BrokenClient:
    def __init__(self):
        def generate_content(**kwargs):
            raise ConnectionError("network down")
        self.models = SimpleNamespace(generate_content=generate_content)


def wrap(values: dict, conf: float = 0.99) -> dict:
    return {k: wrap(v, conf) if isinstance(v, dict) else {"value": v, "confidence": conf}
            for k, v in values.items()}


GAS = {"invoice_no": "GI-01", "month": "2026-01", "fuel": "natural gas", "quantity": 49.0,
       "unit": "GJ", "emission_factor_t_per_tj": 56.1}


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    """Keep LIVE results out of the data folders."""
    monkeypatch.setattr(extract, "live_cache_path", lambda folder: tmp_path / f"{folder}_live.json")
    return tmp_path


def test_valid_json_is_stored_as_live():
    client = FakeClient(json.dumps(wrap(GAS)))
    fields, message = extract.read_with_ai("clean", "GI-01.pdf", client=client)
    assert "Read with AI" in message
    by_key = {f["key"]: f for f in fields}
    assert by_key["fuel[0].quantity"]["value"] == 49.0
    assert all(f["mode"] == "LIVE" and f["model"] == extract.model_name() and f["read_at"] for f in fields)
    assert not any(f["needs_review"] for f in fields)
    assert extract.load_live("clean")["GI-01.pdf"]["fields"] == fields
    sent = client.calls[0]["contents"]
    assert sent[0].inline_data.mime_type == "image/png"      # the PDF went as a rendered image


def test_invalid_json_sends_every_field_to_review():
    bad = wrap(GAS)
    bad["quantity"]["value"] = "forty-nine"
    fields, message = extract.read_with_ai("clean", "GI-01.pdf", client=FakeClient(json.dumps(bad)))
    assert fields and all(f["needs_review"] for f in fields)
    assert "needs review" in message
    fields, _ = extract.read_with_ai("clean", "GI-01.pdf", client=FakeClient("not json"))
    assert all(f["needs_review"] for f in fields)


def test_low_confidence_and_null_need_review():
    values = wrap(GAS)
    values["quantity"]["confidence"] = 0.4
    values["unit"] = {"value": None, "confidence": 0.0}
    fields, _ = extract.read_with_ai("clean", "GI-01.pdf", client=FakeClient(json.dumps(values)))
    review = {f["key"] for f in fields if f["needs_review"]}
    assert review == {"fuel[0].quantity", "fuel[0].unit"}


def test_missing_key_falls_back_to_cached(monkeypatch):
    monkeypatch.delenv(extract.KEY_ENV, raising=False)
    fields, message = extract.read_with_ai("clean", "GI-01.pdf")
    assert message.startswith(extract.NOT_AVAILABLE)
    assert fields and all(f["mode"] == "CACHED" for f in fields)
    assert all(f["mode"] == "CACHED" for f in extract.extract("GI-01.pdf", "LIVE", "clean"))


def test_network_failure_replays_saved_live_result():
    extract.read_with_ai("clean", "GI-01.pdf", client=FakeClient(json.dumps(wrap(GAS))))
    fields, message = extract.read_with_ai("clean", "GI-01.pdf", client=BrokenClient())
    assert "replaying" in message and all(f["mode"] == "LIVE" for f in fields)


def test_pick_flash_model():
    names = ["models/gemini-2.5-flash", "models/gemini-3.8-flash", "models/gemini-3.8-flash-lite",
             "models/gemini-3.9-flash-preview", "models/gemini-3.8-flash-tts", "models/gemini-3.5-pro"]
    assert extract.pick_flash_model(names) == "gemini-3.8-flash"
    assert extract.pick_flash_model(["models/gemini-pro"]) is None


def test_every_document_type_has_a_live_schema():
    for folder in data.FOLDERS:
        for doc in data.load_documents(folder):
            assert doc["type"] in extract.DOC_SPECS, doc


def test_live_fields_feed_the_checks(monkeypatch):
    """The swapped Mn/Cr certificate is still caught when its fields come from LIVE mode."""
    gt = data.read_json(data.folder_path("problem") / "ground_truth.json")
    cert = next(c for c in gt["certificates"] if c["cert_no"] == "MC-A2")
    values = {k: v for k, v in cert.items() if k != "layout"}
    extract.read_with_ai("problem", "MC-A2.pdf", client=FakeClient(json.dumps(wrap(values))))
    monkeypatch.setattr(data, "live_docs", lambda folder: ["MC-A2.pdf"])
    monkeypatch.setattr(data, "read_json", lambda path, default=None: default if path.name == "approvals.json"
                        else extract.read_json(path, default))
    fields = data.load_fields("problem", saved=True)
    live = [f for f in fields if f["source_file"] == "MC-A2.pdf"]
    assert live and all(f["mode"] == "LIVE" for f in live)
    assert not [f for f in fields if f["source_file"] == "MC-A2.pdf" and f["mode"] == "CACHED"]
    flags = run_all(data.build_facility(fields, data.load_config()), data.load_config())
    assert "CHEMISTRY_RANGE" in {f["id"] for f in flags}
