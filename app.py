"""TraceCheck app. Run with: streamlit run app.py

Six pages over one synthetic demo folder (clean, problem or trader).
Works offline in CACHED mode. No login, no internet.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from tracecheck import data, drafts, extract
from tracecheck.calc import mass_ratio, own_direct_per_tonne, specific_embedded_emissions
from tracecheck.checks import apply_notes, run_all
from tracecheck.export import build_pack
from tracecheck.factory_calc import factory_see
from tracecheck.trace import ACTUAL_ALLOWED, STATUS_TEXT, chains, lots

BANNER = "SYNTHETIC DATA · Draft prepared for verifier review · Illustrative, for evidence preparation"
DESIGN_LINE = "AI reads, code calculates, a person approves."

PAGES = [
    "Dashboard",
    "Documents and review",
    "Trace map",
    "Checks",
    "Calculation",
    "Evidence pack",
]

STATUS_ICON = {
    "ACTUAL_ALLOWED": "🟢",
    "DEFAULT_REPORT_PERIOD": "🟠",
    "DEFAULT_NO_EMISSIONS_DATA": "🟡",
    "NO_MILL_LINK": "🔴",
}
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "⚪"}


def banner() -> None:
    st.warning(BANNER)


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


def lot_table(lot_list: list) -> pd.DataFrame:
    return pd.DataFrame([{
        "Status": f"{STATUS_ICON[lot['status']]} {STATUS_TEXT[lot['status']]}",
        "Heat": lot["heat"], "Supplier": lot["supplier"], "Mill": lot["mill"] or "—",
        "Produced": lot["production_year"], "Consumed (t)": lot["consumed_t"],
        "Next action": lot["next_action"], "Mode": lot["mode"],
    } for lot in lot_list])


def page_dashboard(folder: str) -> None:
    s = load(folder)
    st.header("Dashboard")
    st.caption(f"Sri Example Fasteners (fictional) · reporting year {s['cfg']['reporting_year']} · "
               f"demo folder: {folder} · extraction mode: CACHED"
               + (f", LIVE for {len(data.live_docs(folder))} document(s)" if data.live_docs(folder) else ""))
    approved = sum(f["approved"] for f in s["fields"])
    traced = sum(1 for lot in s["lots"] if lot["mill"])
    cols = st.columns(4)
    cols[0].metric("Documents", len(data.load_documents(folder)))
    cols[1].metric("Fields reviewed", f"{approved} / {len(s['fields'])}")
    cols[2].metric("Lots traced to a mill", f"{traced} / {len(s['lots'])}")
    cols[3].metric("Issues open", sum(f["status"] == "open" for f in s["flags"]))

    st.subheader("Precursor status")
    cols = st.columns(4)
    for col, status in zip(cols, STATUS_ICON):
        col.metric(f"{STATUS_ICON[status]} {STATUS_TEXT[status]}",
                   sum(lot["status"] == status for lot in s["lots"]))
    pending = s["fac"]["_pending"]
    if pending:
        st.info(f"{len(pending)} field(s) await review on the Documents and review page. "
                "Checks and the calculation treat them as missing until approved.")


def page_documents(folder: str) -> None:
    s = load(folder)
    st.header("Documents and review")
    docs = data.load_documents(folder)
    pending_docs = sorted({f["source_file"] for f in s["fields"] if not f["approved"]})
    if pending_docs:
        st.info("Fields awaiting review in: " + ", ".join(pending_docs))
    labels = [f"{'⚠ ' if d['file'] in pending_docs else ''}{d['file']} · {d['title']}" for d in docs]
    pending_first = sorted(pending_docs, key=lambda name: not name.endswith(".jpg"))
    first = next((i for i, d in enumerate(docs) if pending_first and d["file"] == pending_first[0]), 0)
    choice = st.selectbox("Document", labels, index=first)
    doc = docs[labels.index(choice)]
    path = data.folder_path(folder) / "docs" / doc["file"]

    st.caption(f"**{DESIGN_LINE}** Gemini never calculates, never decides a flag or a precursor status, "
               "and never sends anything.")
    ai = st.columns(2)
    if ai[0].button("Read with AI", key=f"ai-{folder}-{doc['file']}"):
        fields, message = extract.read_with_ai(folder, doc["file"])
        if fields and fields[0]["mode"] == "LIVE":
            data.clear_approvals(folder, [f["key"] for f in fields])
            data.set_live_doc(folder, doc["file"], True)
        st.session_state["ai_message"] = message
        st.rerun()
    if doc["file"] in data.live_docs(folder) and ai[1].button("Use CACHED fields again",
                                                              key=f"cached-{folder}-{doc['file']}"):
        data.set_live_doc(folder, doc["file"], False)
        st.rerun()
    if st.session_state.get("ai_message"):
        st.info(st.session_state.pop("ai_message"))

    left, right = st.columns(2)
    with left:
        if path.suffix == ".jpg":
            st.image(str(path), caption=f"{doc['file']} (SYNTHETIC photo)")
        else:
            st.download_button("Open the PDF", path.read_bytes(), file_name=doc["file"],
                               mime="application/pdf")
            st.caption(f"{doc['file']} (SYNTHETIC). The fields read from it are on the right.")
    with right:
        fields = [f for f in s["fields"] if f["source_file"] == doc["file"]]
        st.dataframe(pd.DataFrame([{
            "Field": f["label"], "Value": show(f["value"], f["unit"]), "Mode": f["mode"],
            "Confidence": f["confidence"],
            "Review": ("approved · " + f["reviewer"]) if f["approved"] else "⚠ needs review",
        } for f in fields]), hide_index=True)
        unapproved = [f for f in fields if not f["approved"]]
        if len(unapproved) > 1 and st.button("Approve all values on this document as shown",
                                             key=f"approve-all-{folder}-{doc['file']}"):
            for f in unapproved:
                data.save_approval(folder, f["key"], f["value"])
            st.rerun()
        for f in fields:
            if f["approved"]:
                continue
            st.markdown(f"**⚠ {f['label']}** · confidence {f['confidence']} · mode {f['mode']}")
            typed = st.text_input("Value", value=show(f["value"]), key=f"edit-{folder}-{f['key']}")
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


def page_trace(folder: str) -> None:
    s = load(folder)
    st.header("Trace map")
    st.subheader("Precursor status, lot by lot")
    st.caption("Actual precursor data may be used only if a verification report covers the year the "
               "steel was produced. Otherwise the default value applies.")
    st.dataframe(lot_table(s["lots"]), hide_index=True)
    request_section(folder, s["lots"])

    st.subheader("Shipment → production month → heat → supplier → mill")
    rows = chains(s["fac"], s["lots"])
    shipments = ["All"] + sorted({r["Shipment"] for r in rows if r["Shipment"]})
    pick = st.selectbox("Shipment", shipments, index=0)
    shown = [r for r in rows if pick == "All" or r["Shipment"] == pick]
    for r in shown:
        r["Status"] = f"{STATUS_ICON.get(r['Status'], '🔴')} {r['Status']}"
    st.dataframe(pd.DataFrame(shown), hide_index=True)
    st.caption("Values shown are from CACHED extraction unless read with AI (LIVE) or corrected by hand (MANUAL).")


def request_section(folder: str, lot_list: list) -> None:
    groups = drafts.request_groups(lot_list)
    if not groups:
        return
    st.subheader("Requests for missing evidence")
    st.caption("The app never sends email. Edit the draft, then copy it into your own email.")
    for g in groups:
        key = f"draft-{folder}-{g['to']}-{'-'.join(g['heats'])}"
        with st.container(border=True):
            st.markdown(f"**To {g['to']}** · heats {', '.join(g['heats'])} · needed: {g['need']}")
            if st.button("Draft request", key=f"btn-{key}"):
                st.session_state[key], st.session_state[f"{key}-label"] = drafts.draft_request(g)
            if key in st.session_state:
                st.caption(st.session_state.get(f"{key}-label", ""))
                st.text_area("AI draft, review before sending", key=key, height=230)


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
    "Dashboard": page_dashboard,
    "Documents and review": page_documents,
    "Trace map": page_trace,
    "Checks": page_checks,
    "Calculation": page_calculation,
    "Evidence pack": page_evidence,
}


def main() -> None:
    st.set_page_config(page_title="TraceCheck", layout="wide")
    st.sidebar.title("TraceCheck")
    st.sidebar.caption("SYNTHETIC DATA")
    folder = st.sidebar.selectbox("Demo folder", data.FOLDERS, index=0)
    choice = st.sidebar.radio("Page", PAGES)
    banner()
    RENDER[choice](folder)


if __name__ == "__main__":
    main()
