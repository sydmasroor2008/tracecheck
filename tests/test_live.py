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


class QueueClient:
    """Returns the given answers in order, one per call."""

    def __init__(self, texts):
        answers = iter(texts)
        self.models = SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=next(answers)))


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


def test_measurement_counts_misreads_and_review():
    from tools.measure_extraction import compare, read_live, report
    gt = data.read_json(data.folder_path("problem") / "ground_truth.json")
    cert = {k: v for k, v in gt["certificates"][2].items() if k != "layout"}
    cert_answer = wrap(cert)
    cert_answer["chemistry"]["Mn"] = {"value": 0.20, "confidence": 0.5}     # misread, low confidence
    cert_answer["tonnes"] = {"value": 4.0, "confidence": 0.97}              # misread, confident
    docs = [d for d in data.load_documents("problem") if d["file"] in ("GI-01.pdf", "MC-A2.pdf")]
    answers = {"GI-01.pdf": json.dumps(wrap(GAS)), "MC-A2.pdf": json.dumps(cert_answer)}
    live = read_live("problem", docs, client=QueueClient([answers[d["file"]] for d in docs]))
    rows = compare("problem", docs, live)
    wrong = {r["field"]: r["review"] for r in rows if not r["correct"]}
    assert wrong == {"chemistry.Mn": True, "tonnes": False}
    assert sum(r["correct"] for r in rows) == len(rows) - 2
    text = "\n".join(report("problem", docs, live, rows))
    assert f"Field accuracy: {len(rows) - 2} / {len(rows)}" in text
    assert "sent to review: 1; not sent to review (auto-approved): 1" in text
    replayed = read_live("problem", docs, replay=True)
    assert compare("problem", docs, replayed) == rows


DAY_429 = ("429 RESOURCE_EXHAUSTED. {'error': {'message': 'Generate content requests per day limit exceeded "
           "on Free Tier.\\nPlease retry in 18m30.5s.', 'details': [{'quotaId': "
           "'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}, {'retryDelay': '1110s'}]}}")
MINUTE_429 = ("429 RESOURCE_EXHAUSTED. {'error': {'message': 'Please retry in 29.7s.', 'details': [{'quotaId': "
              "'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'}, {'retryDelay': '29s'}]}}")


class QuotaClient:
    """Answers the first `ok` calls, then raises the given quota error on every call."""

    def __init__(self, ok, error):
        self.count = 0

        def generate_content(**kwargs):
            self.count += 1
            if self.count > ok:
                raise RuntimeError(error)
            return SimpleNamespace(text=json.dumps(wrap(GAS)))
        self.models = SimpleNamespace(generate_content=generate_content)


def test_quota_errors_are_classified():
    from tools.measure_extraction import quota_kind, retry_seconds
    assert quota_kind(DAY_429) == "day" and quota_kind(MINUTE_429) == "minute" and quota_kind("timeout") == ""
    assert retry_seconds(DAY_429) == 1110 and retry_seconds(MINUTE_429) == 29
    assert retry_seconds("Please retry in 18m30.5s.") == 1110.5


def test_day_quota_stops_at_once_and_resume_keeps_finished_documents():
    from tools.measure_extraction import QuotaStop, read_live
    docs = [d for d in data.load_documents("clean") if d["type"] == "gas_invoice"][:4]
    waits = []
    client = QuotaClient(2, DAY_429)
    with pytest.raises(QuotaStop, match="per day"):
        read_live("clean", docs, client=client, sleep=waits.append)
    assert client.count == 3 and 1110 + 2 not in waits                 # no long wait, no retry
    assert set(extract.load_live("clean")) == {d["file"] for d in docs[:2]}
    client = QuotaClient(10, DAY_429)
    live = read_live("clean", docs, client=client, resume=True, sleep=waits.append)
    assert client.count == 2 and all(live.values())                    # only the two missing ones read


def test_minute_quota_stops_after_three_in_a_row():
    from tools.measure_extraction import QuotaStop, read_live
    docs = [d for d in data.load_documents("clean") if d["type"] == "gas_invoice"][:4]
    waits = []
    with pytest.raises(QuotaStop):
        read_live("clean", docs, client=QuotaClient(1, MINUTE_429), sleep=waits.append)
    assert waits.count(29 + 2) == 2


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
