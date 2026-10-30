"""Supplier request drafts: grouping from precursor status, template fallback, mocked Gemini."""

from types import SimpleNamespace

from tracecheck import data, drafts
from tracecheck.trace import lots


class FakeClient:
    def __init__(self, text):
        self.prompts = []

        def generate_content(**kwargs):
            self.prompts.append(kwargs["contents"])
            return SimpleNamespace(text=text)
        self.models = SimpleNamespace(generate_content=generate_content)


def groups(folder):
    return drafts.request_groups(lots(data.load_facility(folder, saved=False)))


def test_one_request_per_recipient_and_missing_evidence():
    for folder in data.FOLDERS:
        lot_list = lots(data.load_facility(folder, saved=False))
        asked = [h for g in groups(folder) for h in g["heats"]]
        assert sorted(asked) == sorted(lot["heat"] for lot in lot_list if lot["status"] != "ACTUAL_ALLOWED")
    mill_a = next(g for g in groups("problem") if g["status"] == "DEFAULT_REPORT_PERIOD")
    assert mill_a["heats"] == ["A1", "A2", "A3"] and mill_a["years"] == [2026]
    assert mill_a["need"] == "a verification report from an accredited verifier covering 2026"


def test_trader_chain_asks_the_trader_to_pass_it_on():
    g = next(g for g in groups("problem") if g["status"] == "DEFAULT_NO_EMISSIONS_DATA")
    assert g["via"] and g["to"] == g["via"] and g["mill"]
    assert g["mill"] in drafts.template_draft(g)


def test_template_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    g = groups("problem")[0]
    text, label = drafts.draft_request(g)
    assert label.startswith("Template") and "Review before sending" in label
    assert all(h in text for h in g["heats"]) and drafts.SENDER in text
    assert not drafts.BANNED.search(text)


def test_ai_draft_is_used_when_it_names_every_heat():
    g = groups("problem")[0]
    good = "Subject: Evidence\n\nDear team, please send it for heats " + ", ".join(g["heats"]) + "."
    client = FakeClient(good)
    text, label = drafts.draft_request(g, client)
    assert text.strip() == good and label.startswith("AI draft")
    assert g["need"] in client.prompts[0]


def test_ai_draft_falls_back_when_it_drops_a_heat_or_uses_a_banned_word():
    g = next(g for g in groups("problem") if len(g["heats"]) > 1)
    text, label = drafts.draft_request(g, FakeClient("Dear team, please send data for " + g["heats"][0]))
    assert label.startswith("Template") and text == drafts.template_draft(g)
    text, label = drafts.draft_request(g, FakeClient("We are compliant. Heats " + " ".join(g["heats"])))
    assert label.startswith("Template")
