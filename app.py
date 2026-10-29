"""TraceCheck app (walking skeleton). Run with: streamlit run app.py

Six pages. Only the Calculation page's proof section is live so far;
the rest show placeholders until later build steps. No internet needed.
"""

import streamlit as st

from tracecheck.calc import mass_ratio, own_direct_per_tonne, specific_embedded_emissions

st.set_page_config(page_title="TraceCheck", layout="wide")

BANNER = "SYNTHETIC DATA · Draft prepared for verifier review · Illustrative, for evidence preparation"

PAGES = [
    "Dashboard",
    "Documents and review",
    "Trace map",
    "Checks",
    "Calculation",
    "Evidence pack",
]


def banner() -> None:
    st.warning(BANNER)


def placeholder(text: str) -> None:
    st.info(f"Placeholder: {text}")


def page_dashboard() -> None:
    st.header("Dashboard")
    cols = st.columns(4)
    for col, label in zip(cols, ["Documents", "Fields reviewed", "Lots traced", "Issues open"]):
        col.metric(label, "–")
    placeholder("project status for Sri Example Fasteners (fictional), reporting year 2026.")


def page_documents() -> None:
    st.header("Documents and review")
    left, right = st.columns(2)
    with left:
        placeholder("document image appears here.")
    with right:
        placeholder("extracted fields with edit and approve buttons, and the extraction mode for each value.")


def page_trace() -> None:
    st.header("Trace map")
    placeholder("shipment → production batch → steel lot (heat number, supplier, mill), "
                "with a precursor status per lot and red markers for gaps.")


def page_checks() -> None:
    st.header("Checks")
    placeholder("issue register with severity, a plain explanation and the source documents.")


def oracle_row(label: str, see: float, product: float, consumed: float, official: float) -> dict:
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
        "Commission's published result": official,
        "Match": "yes" if abs(rounded - official) < 1e-9 else "NO",
    }


def page_calculation() -> None:
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
    placeholder("illustrative result for the synthetic factory, or 'input missing: default value not entered'.")


def page_evidence() -> None:
    st.header("Evidence pack")
    placeholder("download button for the Excel evidence pack.")


RENDER = {
    "Dashboard": page_dashboard,
    "Documents and review": page_documents,
    "Trace map": page_trace,
    "Checks": page_checks,
    "Calculation": page_calculation,
    "Evidence pack": page_evidence,
}

st.sidebar.title("TraceCheck")
st.sidebar.caption("SYNTHETIC DATA")
choice = st.sidebar.radio("Page", PAGES)
banner()
RENDER[choice]()
