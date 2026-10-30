"""TraceCheck app. Run with: streamlit run app.py

Six pages over one synthetic demo folder (clean, problem or trader).
Works offline in CACHED mode. No login, no internet.
"""

import base64
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

import ui
from tracecheck import data, drafts, extract
from tracecheck.calc import mass_ratio, own_direct_per_tonne, specific_embedded_emissions
from tracecheck.checks import apply_notes, run_all
from tracecheck.export import build_pack
from tracecheck.factory_calc import factory_see
from tracecheck.trace import ACTUAL_ALLOWED, DEFAULT_NO_EMISSIONS_DATA, DEFAULT_REPORT_PERIOD, STATUS_TEXT, chains, lots

BANNER = "SYNTHETIC DATA · Draft prepared for verifier review · Illustrative, for evidence preparation"
DESIGN_LINE = "AI reads · code calculates · a person approves"

PAGES = ["Overview", "1 Read", "2 Trace", "3 Check", "4 Calculate", "5 Export"]
SCENARIOS = {"clean": "Clean factory", "problem": "Factory with problems", "trader": "Trader supply chain"}

DOC_ICON = {
    "purchase_invoice": ":material/receipt_long:", "gas_invoice": ":material/local_fire_department:",
    "export_invoice": ":material/local_shipping:", "mill_certificate": ":material/workspace_premium:",
    "delivery_note": ":material/inventory_2:", "verification_report": ":material/task_alt:",
    "production_register": ":material/menu_book:", "scrap_register": ":material/menu_book:",
    "stock_register": ":material/menu_book:",
}

STATUS_ICON = {
    "ACTUAL_ALLOWED": "🟢",
    "DEFAULT_REPORT_PERIOD": "🟠",
    "DEFAULT_NO_EMISSIONS_DATA": "🟡",
    "NO_MILL_LINK": "🔴",
}
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "⚪"}


def go(page: str) -> None:
    st.session_state["page"] = page


def load(folder: str) -> dict:
    """Everything a page needs, rebuilt from the folder's files on every run."""
    cfg = data.load_config()
    fields = data.load_fields(folder)
    fac = data.build_facility(fields, cfg)
    lot_list = lots(fac)
    flags = apply_notes(run_all(fac, cfg), data.load_flag_notes(folder))
    return {"cfg": cfg, "fields": fields, "fac": fac, "lots": lot_list, "flags": flags}


def defaults_for(folder: str) -> dict:
    """Default values typed by the user this session (MANUAL, 'entered by user')."""
    return st.session_state.setdefault("defaults", {}).setdefault(folder, {})


def show(value, unit=None) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        value = ", ".join(map(str, value))
    elif isinstance(value, float):
        value = f"{value:g}"
    return f"{value} {unit}" if unit and unit != "fraction" else str(value)


def parse_like(original, text: str):
    """Turn typed text into the same kind of value as the original."""
    text = text.strip()
    if isinstance(original, list):
        return [part.strip() for part in text.split(",") if part.strip()]
    if isinstance(original, (int, float)) and not isinstance(original, bool):
        return float(text)
    return text


def mode_line(folder: str) -> str:
    live = len(data.live_docs(folder))
    return f"CACHED, LIVE for {live} document(s)" if live else "CACHED"


def verdict_name(status: str, lot_list: list, year) -> str:
    if status == ACTUAL_ALLOWED:
        return "Ready"
    if status == DEFAULT_REPORT_PERIOD:
        years = sorted({lot["production_year"] for lot in lot_list if lot["status"] == status and lot["production_year"]})
        return f"Needs {'/'.join(map(str, years or [year]))} report"
    return "No mill data" if status == DEFAULT_NO_EMISSIONS_DATA else "Untraced"


def consumed(lot_list: list, status: str = None):
    """Tonnes consumed; a lot whose count awaits review adds nothing yet."""
    return sum(lot["consumed_t"] or 0 for lot in lot_list if status in (None, lot["status"]))


def evidence(s: dict) -> dict:
    """Readiness figures for the evidence bar, all from the lots of this scenario."""
    year = s["cfg"]["reporting_year"]
    total = consumed(s["lots"])
    ready = consumed(s["lots"], ACTUAL_ALLOWED)
    bars = [{"css": ui.VERDICT[status][0], "name": verdict_name(status, s["lots"], year),
             "t": consumed(s["lots"], status)} for status in ui.VERDICT]
    return {"total": total, "ready": ready, "share": round(100 * ready / total) if total else 0,
            "bars": [b for b in bars if b["t"] > 0]}


def missing_inputs(calc: dict) -> tuple:
    """(inputs that still stop the illustrative result, how many of them are lot default values)."""
    if calc["result"].ok:
        return 0, 0
    items = re.split(r"; (?![^()]*\))", (calc["result"].missing or "").removeprefix("input missing: "))
    others = [i for i in items if i and not i.startswith("default value not entered")]
    no_default = sum(v["see"] is None for v in calc["lot_values"])
    return no_default + len(others), no_default


def page_overview(folder: str) -> None:
    s = load(folder)
    docs = data.load_documents(folder)
    year = s["cfg"]["reporting_year"]
    pending_docs = {f["source_file"] for f in s["fields"] if not f["approved"]}
    traced = [lot for lot in s["lots"] if lot["mill"]]
    mills = {lot["mill"] for lot in traced}
    untraced = len(s["lots"]) - len(traced)
    open_flags = sum(f["status"] == "open" for f in s["flags"])
    missing, no_default = missing_inputs(factory_see(s["fac"], s["lots"], defaults_for(folder)))
    e = evidence(s)

    st.html(ui.head(f"Overview · Sri Example Fasteners · Reporting year {year}", "How ready is the evidence?"))
    st.html(ui.hero(e["share"], e["total"], year, e["bars"], mode_line(folder)))
    st.html(ui.tiles([
        ui.tile("Documents read", len(docs), "", f"{len(pending_docs)} need a human check" if pending_docs
                else "All checked by a person", "action" if pending_docs else "ready"),
        ui.tile("Steel traced", len(s["lots"]), "lots", f"to {len(mills)} mills, no gaps" if not untraced
                else f"{untraced} lots not linked to a mill", "problem" if untraced else "ready"),
        ui.tile("Issues", open_flags, "", f"{open_flags} open" if open_flags else "All checks passed",
                "problem" if open_flags else "ready", alert=open_flags > 0),
        ui.tile("Evidence pack", missing, "input" if missing == 1 else "inputs",
                "Ready to export" if not missing else "default values still to enter" if missing == no_default
                else f"{no_default} default values, {missing - no_default} other", "action" if missing else "ready"),
    ]))
    n = len(docs)
    stages = [
        {"name": "Documents read", "done": n, "total": n, "text": f"{n} of {n}"},
        {"name": "Fields approved", "done": n - len(pending_docs), "total": n, "text": f"{n - len(pending_docs)} of {n} docs"},
        {"name": "Steel traced", "done": len(traced), "total": len(s["lots"]), "text": f"{len(traced)} of {len(s['lots'])} lots"},
        {"name": "Checks clear", "done": len(s["flags"]) - open_flags, "total": len(s["flags"]), "text": f"{open_flags} issues"},
        {"name": "Pack ready", "done": 0 if missing else 1, "total": 1,
         "text": f"{missing} inputs missing" if missing else "ready to export"},
    ]
    complete = sum(x["done"] >= x["total"] for x in stages)
    with st.container(key="box-path"):
        with st.container(horizontal=True, key="pathhead"):
            st.html(ui.path_head(complete))
            st.button("Start: 1 Read the documents →", type="primary", key="start", on_click=go, args=("1 Read",))
        st.html(ui.path_track(stages))
    foot()


@lru_cache(maxsize=64)
def doc_image(path: str) -> str:
    """First page of a document as a data URI, for the paper sheet."""
    raw, mime = extract.page_images(Path(path))[0]
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def pick_doc(folder: str, name: str) -> None:
    st.session_state[f"doc-{folder}"] = name


def doc_list(folder: str, docs: list, pending_docs: list, chosen: str) -> None:
    ordered = sorted(docs, key=lambda d: d["file"] not in pending_docs)
    with st.container(height=520, key="doclist", border=False):
        for i, d in enumerate(ordered):
            state = ("need" if d["file"] in pending_docs else "ok") + ("-sel" if d["file"] == chosen else "")
            st.button(d["file"], key=f"doc-{state}-{i}", icon=DOC_ICON.get(d["type"]), help=d["title"],
                      on_click=pick_doc, args=(folder, d["file"]))


def field_review(folder: str, f: dict, i: int) -> None:
    """One field that needs a person: its row, the value box and Approve."""
    st.html(ui.field_row(f["label"], show(f["value"], f["unit"]), f["mode"], f["confidence"], check=True))
    with st.container(horizontal=True, key=f"chk-{i}"):
        typed = st.text_input("Value", value=show(f["value"]), key=f"edit-{folder}-{f['key']}",
                              label_visibility="collapsed")
        if st.button("Approve", key=f"approve-{folder}-{f['key']}"):
            edited = typed != show(f["value"])
            try:
                value = parse_like(f["value"], typed) if edited else f["value"]
            except ValueError:
                st.error("Please type a number.")
                return
            data.save_approval(folder, f["key"], value, edited=edited)
            st.session_state["last_approved"] = f["key"]
            st.rerun()


def page_documents(folder: str) -> None:
    s = load(folder)
    docs = data.load_documents(folder)
    pending_docs = sorted({f["source_file"] for f in s["fields"] if not f["approved"]})
    pending_first = sorted(pending_docs, key=lambda name: not name.endswith(".jpg"))
    chosen = st.session_state.setdefault(f"doc-{folder}", pending_first[0] if pending_first else docs[0]["file"])
    doc = next(d for d in docs if d["file"] == chosen)
    path = data.folder_path(folder) / "docs" / doc["file"]
    fields = [f for f in s["fields"] if f["source_file"] == doc["file"]]
    modes = " + ".join(sorted({f["mode"] for f in fields})) or "CACHED"

    st.html(ui.head("Step 1 · Read the documents", "What did the AI read?", DESIGN_LINE,
                    side=ui.review_card(len(docs) - len(pending_docs), len(docs))))
    left, right = st.columns([5, 7], gap="medium")
    with left:
        st.html(ui.doc_legend(len(pending_docs)))
        doc_list(folder, docs, pending_docs, chosen)
    with right:
        sheet = st.empty()
        sheet.html(ui.window(doc["file"], modes, doc_image(str(path))))
        with st.container(horizontal=True, key="aibar"):
            read = st.button("Read with AI", key=f"ai-{folder}-{doc['file']}")
            if doc["file"] in data.live_docs(folder) and st.button("Use CACHED fields again",
                                                                   key=f"cached-{folder}-{doc['file']}"):
                data.set_live_doc(folder, doc["file"], False)
                st.rerun()
            if path.suffix != ".jpg":
                st.download_button("Open the PDF", path.read_bytes(), file_name=doc["file"], mime="application/pdf")
        if read:
            sheet.html(ui.window(doc["file"], modes, doc_image(str(path)), scanning=True))
            fields_read, message = extract.read_with_ai(folder, doc["file"])
            if fields_read and fields_read[0]["mode"] == "LIVE":
                data.clear_approvals(folder, [f["key"] for f in fields_read])
                data.set_live_doc(folder, doc["file"], True)
            st.session_state["ai_message"] = message
            st.rerun()
        if st.session_state.get("ai_message"):
            st.info(st.session_state.pop("ai_message"))
        st.html(ui.small_tip("Gemini never calculates, never decides a flag or a precursor status, and never sends anything."))

        unapproved = [f for f in fields if not f["approved"]]
        if len(unapproved) > 1 and st.button("Approve all values on this document as shown",
                                             key=f"approve-all-{folder}-{doc['file']}"):
            for f in unapproved:
                data.save_approval(folder, f["key"], f["value"])
            st.rerun()
        for i, f in enumerate(unapproved):
            field_review(folder, f, i)
        st.html("".join(ui.field_row(f["label"], show(f["value"], f["unit"]), f["mode"], f["confidence"])
                        for f in fields if f["approved"]))
        with st.expander("Correct an approved value"):
            keys = [f["key"] for f in fields]
            key = st.selectbox("Field", keys, key=f"fix-{folder}-{doc['file']}")
            field = next((f for f in fields if f["key"] == key), None)
            if field:
                typed = st.text_input("Corrected value", value=show(field["value"]), key=f"fixv-{folder}-{key}")
                if st.button("Apply correction (mode becomes MANUAL)", key=f"fixb-{folder}-{key}"):
                    try:
                        data.save_approval(folder, key, parse_like(field["value"], typed), edited=True)
                    except ValueError:
                        st.error("Please type a number.")
                        return
                    st.rerun()
            if st.button("Reset all reviews in this folder"):
                data.reset_approvals(folder)
                st.rerun()
        upload_section()
    foot("Next: 2 Trace the steel →", "2 Trace")


def upload_section() -> None:
    with st.expander("Upload your own document photo and read it with AI"):
        st.caption("For review only: an uploaded document is not added to this folder's checks. "
                   "The file is kept in data/uploads on this computer and its image is sent to the "
                   "Gemini API when you press the button.")
        kind = st.selectbox("Document type", list(extract.DOC_SPECS), key="upload-kind")
        upload = st.file_uploader("Photo (JPG or PNG) or PDF", type=["jpg", "jpeg", "png", "pdf"])
        if upload is not None and st.button("Read the upload with AI"):
            dest = extract.UPLOADS / Path(upload.name).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(upload.getvalue())
            fields, message = extract.read_with_ai(None, dest.name, kind, path=dest)
            st.info(message)
            if fields:
                st.dataframe(pd.DataFrame([{
                    "Field": f["label"], "Value": show(f["value"], f["unit"]), "Mode": f["mode"],
                    "Confidence": f["confidence"],
                    "Review": "⚠ needs review" if f["needs_review"] else "readable",
                } for f in fields]), hide_index=True)


def short_name(name: str) -> str:
    return (name or "").replace(", synthetic", "")


def mill_tag(name: str) -> str:
    return short_name(name).replace("Example Steel ", "")


def lot_line(lot: dict) -> str:
    """The small line on a lot card, for example 'Made 2025 · opening stock'."""
    bits = [f"via {short_name(lot['supplier'])}" if lot["supplier"] != lot["mill"] and lot["kind"] == "purchase"
            else f"Made {lot['production_year'] or 'year unknown'}"]
    if lot["kind"] == "opening stock":
        bits.append("opening stock")
    left = (lot["tonnes"] or 0) - (lot["consumed_t"] or 0) if lot["consumed_t"] is not None else 0
    if left > 0:
        bits.append(f"{ui.num(left)} t still in stock")
    return " · ".join(bits)


def lot_step(lot: dict) -> str:
    """Short form of the next action from trace.py; the card's hover text keeps the full sentence."""
    mill, year = mill_tag(lot["mill"]), lot["production_year"]
    if lot["status"] == ACTUAL_ALLOWED:
        return f"Keep the {year} verification report in the pack."
    if lot["status"] == DEFAULT_REPORT_PERIOD:
        return f"Ask {mill} for a report covering {year or 'the production year'}."
    if lot["status"] == DEFAULT_NO_EMISSIONS_DATA:
        through = ", through the trader," if lot["supplier"] != lot["mill"] and lot["kind"] == "purchase" else ""
        return f"Ask {mill}{through} for verified data."
    return lot["next_action"]


def open_draft(folder: str, g: dict) -> None:
    key = f"draft-{folder}-{g['to']}-{'-'.join(g['heats'])}"

    def body() -> None:
        st.markdown(f"**Heats {', '.join(g['heats'])}** · needed: {g['need']}")
        if key not in st.session_state:
            with st.spinner("Drafting…"):
                st.session_state[key], st.session_state[f"{key}-label"] = drafts.draft_request(g)
        st.caption(st.session_state.get(f"{key}-label", ""))
        st.text_area("AI draft, review before sending", key=key, height=260)
        st.caption("The app never sends email. Edit the draft, then copy it into your own email.")

    st.dialog(f"Request to {short_name(g['to'])}", width="large")(body)()


def lot_cards(folder: str, status: str, lot_list: list, groups: list) -> None:
    name = ui.VERDICT[status][0]
    for lot in lot_list:
        with st.container(key=f"lot-{lot['heat']}"):
            st.html(ui.lot_card(name, lot["heat"], lot["consumed_t"], short_name(lot["mill"]) or "Mill not known",
                                lot_line(lot), lot["mode"], lot_step(lot), lot["next_action"]))
            group = next((g for g in groups if lot["heat"] in g["heats"]), None)
            if status != ACTUAL_ALLOWED and group and st.button("Draft request with AI", key=f"ask-{lot['heat']}"):
                open_draft(folder, group)


def page_trace(folder: str) -> None:
    s = load(folder)
    e = evidence(s)
    year = s["cfg"]["reporting_year"]
    st.html(ui.head("Step 2 · Trace the steel", "Can this steel use real data?",
                    "Every lot of steel, followed back to the mill that made it.",
                    side=ui.readiness(e["share"], e["ready"], e["total"], e["bars"])))
    groups = drafts.request_groups(s["lots"])
    for col, (status, (name, icon, meaning)) in zip(st.columns(4, gap="small"), ui.VERDICT.items()):
        shown = [lot for lot in s["lots"] if lot["status"] == status]
        count = f"{len(shown)} {'lot' if len(shown) == 1 else 'lots'}"
        with col, st.container(key=f"col-{name}"):
            st.html(ui.verdict_head(name, icon, verdict_name(status, s["lots"], year), meaning,
                                    f"{count} · {ui.num(consumed(shown))} t" if shown else count))
            if not shown:
                st.html(ui.empty_card("None in this scenario"))
            lot_cards(folder, status, shown, groups)
    st.html(ui.glossary())

    with st.expander("Precursor status, shipment by shipment"):
        rows = chains(s["fac"], s["lots"])
        shipments = ["All"] + sorted({r["Shipment"] for r in rows if r["Shipment"]})
        pick = st.selectbox("Shipment", shipments, index=0)
        shown = [r for r in rows if pick == "All" or r["Shipment"] == pick]
        for r in shown:
            r["Status"] = f"{STATUS_ICON.get(r['Status'], '🔴')} {r['Status']}"
        st.dataframe(pd.DataFrame(shown), hide_index=True)
        st.caption("Values shown are from CACHED extraction unless read with AI (LIVE) or corrected by hand (MANUAL).")
    foot("Next: 3 Check the papers →", "3 Check")


def page_checks(folder: str) -> None:
    s = load(folder)
    st.header("Checks")
    if not s["flags"]:
        st.success("No flags. Every check passed on the reviewed data.")
    for f in s["flags"]:
        with st.container(border=True):
            st.markdown(f"{SEVERITY_ICON[f['severity']]} **{f['id']}** · {f['severity']} · {f['status']}")
            st.write(f["message"])
            st.caption("Sources: " + ", ".join(f["sources"]))
            if f["status"] == "open":
                note = st.text_input("Note", key=f"note-{folder}-{f['key']}")
                if st.button("Accept with note", key=f"accept-{folder}-{f['key']}"):
                    if not note.strip():
                        st.warning("Write a note first: why is this flag accepted?")
                    else:
                        data.save_flag_note(folder, f["key"], note.strip())
                        st.rerun()
            else:
                st.caption(f"Note: {f['note']}")


def oracle_row(label: str, see: float, product: float, consumed: float, published: float) -> dict:
    mi = mass_ratio(consumed, product).value
    own = own_direct_per_tonne(3.5, 56.1).value
    rounded = specific_embedded_emissions(own, [("steel rod", mi, see)], round_intermediates_to=3).value
    raw = specific_embedded_emissions(own, [("steel rod", mi, see)]).value
    return {
        "Product": label,
        "Precursor SEE (example value)": see,
        "Mass ratio mi": round(mi, 3),
        "Our result (intermediates rounded to 3 dp)": round(rounded, 3),
        "Our result (no rounding)": round(raw, 5),
        "Commission's published result": published,
        "Match": "yes" if abs(rounded - published) < 1e-9 else "NO",
    }


def page_calculation(folder: str) -> None:
    s = load(folder)
    st.header("Calculation")
    st.subheader("Proof: the Commission's worked example")
    st.caption("Commission Guidance No. 5d, Example 3 (screws and nuts from purchased steel rods), "
               "14 August 2026. Illustrative example values, not default values and not a real factory.")
    rows = [
        oracle_row("Carbon steel screws and nuts", 1.567, 17_000, 20_000, 2.039),
        oracle_row("Stainless screws and nuts", 1.783, 8_200, 10_000, 2.371),
    ]
    st.table(rows)
    st.caption("Units: t CO2 per t of product. Gas: 3.5 GJ per t at 56.1 t CO2 per TJ.")

    st.subheader("Sri Example Fasteners (synthetic)")
    defaults = defaults_for(folder)
    need = [lot for lot in s["lots"] if lot["status"] != ACTUAL_ALLOWED]
    if need:
        st.caption("Default values are not shipped with the app. Look them up and type them here; "
                   "they are labelled 'entered by user'.")
        cols = st.columns(min(len(need), 4))
        for i, lot in enumerate(need):
            defaults[lot["heat"]] = cols[i % len(cols)].number_input(
                f"Default for heat {lot['heat']} (t CO2/t), entered by user",
                value=defaults.get(lot["heat"]), min_value=0.0, format="%.5f",
                key=f"default-{folder}-{lot['heat']}")
    out = factory_see(s["fac"], s["lots"], defaults)
    if out["result"].ok:
        st.success(f"Specific embedded emissions: {out['result'].value:g} t CO2 per t of product. "
                   "Illustrative, for evidence preparation.")
        st.table(pd.DataFrame([{"Step": a, "Value": b, "Unit": c} for a, b, c in out["steps"]]))
    else:
        st.error(out["result"].missing)
    st.dataframe(pd.DataFrame([{
        "Heat": v["heat"], "Consumed (t)": v["consumed_t"], "Value (t CO2/t)": v["see"],
        "Basis": v["basis"], "Mode": "MANUAL" if v["basis"].endswith("by user") else "CACHED",
    } for v in out["lot_values"]]), hide_index=True)


def page_evidence(folder: str) -> None:
    s = load(folder)
    st.header("Evidence pack")
    st.write("An Excel workbook with six sheets: issue register, precursor status, missing documents, "
             "evidence index, input sheet for the Commission's operator emissions report template, "
             "and assumptions. Draft prepared for verifier review.")
    defaults = defaults_for(folder)
    calc = factory_see(s["fac"], s["lots"], defaults)
    pack = build_pack(folder, s["fields"], s["fac"], s["flags"], s["lots"], calc, s["cfg"], defaults)
    st.download_button("Download the evidence pack (Excel)", pack,
                       file_name=f"tracecheck_evidence_pack_{folder}_SYNTHETIC.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


RENDER = {
    "Overview": page_overview,
    "1 Read": page_documents,
    "2 Trace": page_trace,
    "3 Check": page_checks,
    "4 Calculate": page_calculation,
    "5 Export": page_evidence,
}


def top_bar() -> str:
    """Logo, numbered path and scenario. Returns the chosen folder."""
    query = st.query_params
    if "page" not in st.session_state:
        st.session_state["page"] = query.get("page") if query.get("page") in PAGES else PAGES[0]
    if "scenario" not in st.session_state:
        st.session_state["scenario"] = query.get("scenario") if query.get("scenario") in SCENARIOS else data.FOLDERS[0]
    now = PAGES.index(st.session_state["page"])
    with st.container(horizontal=True, key="topbar"):
        st.html(ui.brand())
        with st.container(horizontal=True, key="navpath"):
            for i, page in enumerate(PAGES):
                state = "now" if i == now else "done" if i < now else "todo"
                st.button(page.split()[-1], key=f"nav-{state}-{i}", on_click=go, args=(page,))
        folder = st.selectbox("Scenario", list(SCENARIOS), format_func=SCENARIOS.get, key="scenario",
                              label_visibility="collapsed")
        st.html(ui.synth_pill())
    return folder


def foot(next_label: str = None, target: str = None) -> None:
    """Every screen ends with the honesty line and one button to the next step."""
    with st.container(horizontal=True, key="foot"):
        st.html(ui.footline(BANNER))
        if next_label:
            st.button(next_label, type="primary", key="next", on_click=go, args=(target,))


def main() -> None:
    st.set_page_config(page_title="TraceCheck", page_icon=str(ui.LOGO), layout="wide",
                       initial_sidebar_state="collapsed")
    st.html(ui.css())
    folder = top_bar()
    RENDER[st.session_state["page"]](folder)


if __name__ == "__main__":
    main()
