"""Draft emails asking a mill or trader for missing precursor evidence.

Gemini writes the wording only. What to ask for comes from the precursor status
and next action worked out in trace.py. Without a key a plain template is used.
The app shows the draft in an editable box and never sends email.
"""

import re
from pathlib import Path

from tracecheck.extract import make_client, model_name
from tracecheck.trace import ACTUAL_ALLOWED, DEFAULT_NO_EMISSIONS_DATA, DEFAULT_REPORT_PERIOD, NO_MILL_LINK

SENDER = "Sri Example Fasteners (synthetic)"
# RULES.md rule 13 words, kept in a text file so this code does not contain them
BANNED = re.compile((Path(__file__).with_name("banned_words.txt")).read_text(encoding="utf-8").strip(), re.IGNORECASE)

PROMPT = """Write a short, polite email (under 150 words) from a small steel-product maker to a supplier.
Ask for exactly the evidence below and nothing else. Use only the facts given. Do not add deadlines,
regulations, numbers, attachments or promises that are not in the facts. Plain text, start with a
'Subject:' line, sign as the sender.

Sender: {sender}
Recipient: {to}
Heat numbers: {heats}
Production year(s): {years}
Evidence needed: {need}
Why: {why}
{via}"""


def _join(items: list) -> str:
    items = [str(i) for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def request_groups(lot_list: list) -> list:
    """One request per recipient and next action, for every lot whose status is not ACTUAL_ALLOWED."""
    groups = {}
    for lot in lot_list:
        if lot["status"] == ACTUAL_ALLOWED:
            continue
        via = lot["supplier"] if lot["status"] == DEFAULT_NO_EMISSIONS_DATA and lot["supplier"] != lot["mill"] else None
        to = via or lot["mill"] or (lot["supplier"] if lot["kind"] == "purchase" else None)
        if not to:
            continue
        g = groups.setdefault((to, lot["next_action"]), {
            "to": to, "mill": lot["mill"], "via": via, "status": lot["status"],
            "status_text": lot["status_text"], "next_action": lot["next_action"], "heats": [], "years": []})
        g["heats"].append(lot["heat"])
        if lot["production_year"] and lot["production_year"] not in g["years"]:
            g["years"].append(lot["production_year"])
    for g in groups.values():
        g["need"] = evidence_needed(g)
    return list(groups.values())


def evidence_needed(g: dict) -> str:
    years = _join(g["years"]) if g["years"] else "the production year"
    if g["status"] == DEFAULT_REPORT_PERIOD:
        return f"a verification report from an accredited verifier covering {years}"
    if g["status"] == DEFAULT_NO_EMISSIONS_DATA:
        return f"verified emissions data for these heats: the mill's verification report covering {years}"
    if g["status"] == NO_MILL_LINK:
        return "a delivery note naming the producing mill and the heat numbers"
    return g["next_action"]


def template_draft(g: dict) -> str:
    heats = _join(g["heats"])
    via = f"\nIf this data sits with {g['mill']}, could you please pass this request on to them?\n" if g["via"] else ""
    return (f"Subject: Request for evidence for heat{'s' if len(g['heats']) > 1 else ''} {heats}\n\n"
            f"Dear {g['to']} team,\n\n"
            f"We are preparing our CBAM records for the steel we bought from you. "
            f"For heat{'s' if len(g['heats']) > 1 else ''} {heats} we need {g['need']}.\n"
            f"{via}\n"
            f"Could you please send this, or let us know when it will be available?\n\n"
            f"Thank you,\n{SENDER}\n")


def draft_request(g: dict, client=None) -> tuple:
    """(text, label). Falls back to the template if Gemini is not available or the draft looks wrong."""
    try:
        client = client or make_client()
        via = f"Ask the recipient to pass the request on to {g['mill']}." if g["via"] else ""
        resp = client.models.generate_content(model=model_name(), contents=PROMPT.format(
            sender=SENDER, to=g["to"], heats=", ".join(g["heats"]), years=_join(g["years"]) or "unknown",
            need=g["need"], why=g["status_text"], via=via))
        text = (resp.text or "").strip()
    except Exception as exc:  # no key or no network: the button still works
        reason = str(exc).splitlines()[0][:120] if str(exc) else type(exc).__name__
        return template_draft(g), f"Template (AI not available: {reason}). Review before sending."
    if not text or BANNED.search(text) or not all(h in text for h in g["heats"]):
        return template_draft(g), "Template (the AI draft left out a heat or used a banned word). Review before sending."
    return text + "\n", f"AI draft ({model_name()}). Review before sending."
