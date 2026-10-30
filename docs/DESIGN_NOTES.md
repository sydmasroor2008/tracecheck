# Design notes (Step 14)

## What changed

- The app now follows DESIGN_PLAN.md: "Evidence on paper", light theme only, paper grain, Montserrat, Inter and JetBrains Mono bundled in `static/fonts/`.
- The sidebar is gone. A top bar holds the logo, the numbered path, the Scenario selector and the SYNTHETIC pill.
- Six screens rebuilt: Overview, 1 Read, 2 Trace, 3 Check, 4 Calculate, 5 Export. Each ends with one button to the next step.
- New files: `ui.py` (HTML components), `static/style.css`. `tracecheck/`, `tools/` and `data/` were not touched.
- Every number on screen still comes from the existing functions. All earlier features are kept: approve, correct, reset, upload, Read with AI, draft requests, accept with note, shipment chains, proof table.

## Where the app differs from the mockups

- **Page padding is 40 px**, as in the mockups, not the 48 px in DESIGN_PLAN.md section 5.
- **Overview path title reads "Three of five stages complete".** The mockup says "Four", but it also shows only three stages done. The app counts.
- **Evidence pack tile shows 4 inputs in the clean scenario**, not 3: three default values plus the March gas invoice still awaiting review. The app counts this too.
- **Fields approved is counted in documents** ("33 of 36 docs"), which is what the mockup's 33 of 36 means.
- **Top bar shows only the 40 px logo mark.** The team removed the wordmark after the first build; DESIGN_PLAN.md section 10 and the Overview mockup still show it.
- **Verdict columns with more than 3 lots** show the rest as one-line rows, with their full cards under Show all. Rows keep a mode chip, because the plan requires the mode next to values.
- **Below 1100 px** the step labels hide (Overview keeps its word, as it has no number), the Scenario selector and pill move to a second row, and all screen titles drop to 40 px.
- **Export ends with a quiet "Back to Overview →"** as it has no next step. **Overview ends with the Start button** in its last tile, as in the mockup.
- **The Scenario selector is wider** (244 px) so "Factory with problems" fits.
- **Lot cards carry a mode chip** (CACHED / LIVE / MANUAL), which the mockup lacks but the plan's hard limits require.
- **The "Try Factory with problems" hint is left out** of the empty Untraced column. No scenario has an untraced lot, so it would point nowhere.
- **The full line "Draft prepared for verifier review" sits in the footer of every screen.** The top pill keeps the shorter mockup wording.

## Added after the first build

- **Reset demo** sits at the bottom of Overview and asks for confirmation. It clears approvals, typed defaults and accepted flags for the current scenario only. LIVE document choices stay.
- **Page changes scroll to the top** through a small script in `st.html`, because Streamlit keeps the old scroll position.

## What was cut

- The optional Shipment → Month → Heat → Mill box diagram. The shipment table stays, in an expander on 2 Trace.
- Only the first page of a document shows on the sheet. No demo document needs more; "Open the PDF" gives the full file.

## What did not work in Streamlit

- `st.html` strips inline `<svg>`, so rings and check marks are data-URI images.
- `help=` only exists on widgets, so the four glossary terms on 2 Trace use a small CSS tooltip.
- The `st.navigation` top bar cannot show numbered circles or check marks, so the path is a row of styled buttons kept in `st.session_state`.
- Buttons cannot take custom classes. State is carried in widget keys (`nav-done-1`, `doc-need-sel-2`) and matched with CSS. These selectors depend on Streamlit 1.66 markup, including the selectbox, and may need fixing after an upgrade.
- Streamlit does not reload `ui.py` while running in every case. Restart the server after editing it.
- The whole page does not fit in 768 px. Overview needs about 1000 px and Trace more, as in the mockups, so both scroll. The hero and the four tiles are visible without scrolling.

## Added for screenshots

`?page=2%20Trace&scenario=problem` opens a screen and scenario directly. Used to capture `docs/screens/`; the app ignores it after the first load.
