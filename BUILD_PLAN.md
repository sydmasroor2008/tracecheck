# BUILD PLAN: TraceCheck, steps 4 to 12

This file is the complete build specification. It replaces Parts 4 to 10 of the old
TraceCheck Build Guide PDF wherever they differ. Steps 1 to 3 are DONE: project files,
the six-page Streamlit skeleton (`app.py`), and `tracecheck/calc.py` with 20 passing tests.

## How to work (autonomous mode)

The human has asked you to build steps 4 to 12 in one go, without stopping between
steps. RULES.md rule 1 is relaxed for this plan only: continue to the next step when the
current one passes. All other rules in RULES.md still apply.

For every step:

1. Write the code and its tests.
2. Run `python -m pytest -q` with the virtual environment's Python
   (`.venv\Scripts\python.exe` on Windows; create `.venv` from requirements.txt if it is missing).
3. If tests fail, fix the code, not the test. If a test itself is wrong, fix it and say why in PROGRESS.md.
4. `git add -A` and `git commit -m "Step N: <short title>"`. Run `git init` first if there is no repository.
5. Append 2 to 4 lines to `PROGRESS.md`: step number, what was built, test count, anything unresolved.

Stop and ask the human only if:
- a regulatory fact is needed that is not in docs/REGULATORY_NOTES.md, or
- the same error survives three different fix attempts, or
- something in this plan contradicts itself.

To keep usage low:
- Do not re-read files you have just written. Do not print whole files or long outputs to the chat; use `pytest -q` and `head`.
- Write plain, short code. No classes where a function will do. No extra frameworks, no database, no login.
- Do not run the Streamlit server in the background for long. To check the app, run
  `python -c "import app"` with a stub, or `streamlit run app.py --server.headless true` briefly and stop it.
- If the session ends before the work is done, the next session starts by reading PROGRESS.md and continues from the first unfinished step.

When everything is done, write `BUILD_REPORT.md` (see Step 12) and stop.

## Folder layout to end with

```
app.py                 Streamlit app, six pages
run.bat                start script (exists)
config.yaml            settings (exists; add grade ranges, see Step 6)
tracecheck/
  calc.py              calculator (exists, do not change its behaviour)
  model.py             pydantic models for the ground truth and extracted fields
  data.py              load a demo folder (ground truth, cached fields, approvals)
  extract.py           MANUAL / CACHED / LIVE extraction interface
  checks.py            reconciliation checks, each a pure function
  trace.py             shipment -> batch -> lot -> heat -> mill chain, precursor status
  factory_calc.py      illustrative SEE for the synthetic factory, using calc.py
  export.py            Excel evidence pack
tools/
  make_factory.py      builds the synthetic factory and its documents
  measure_extraction.py
data/
  clean/  problem/  trader/      each: ground_truth.json, expected_results.json,
                                 cached_fields.json, docs/*.pdf, docs/*.jpg
tests/
  test_oracle.py, test_calc.py (exist)
  test_factory.py, test_checks.py, test_trace.py, test_export.py, test_app_smoke.py
```

## Step 4: the synthetic factory (`tools/make_factory.py`)

Two stages, fixed random seed 2026.

**Stage 1 writes `data/<folder>/ground_truth.json`** for each folder. **Stage 2 renders documents**
from that ground truth: PDFs with reportlab, and a few JPG "photos" with Pillow (rotate 2 to 4
degrees, add noise, draw a round red stamp partly over one number). Every page and image shows
the word SYNTHETIC. Use at least three different mill-certificate layouts (table across, table
down, two-column). Add one handwritten-style note (a script-like font or slanted text) on one register.

Stage 1 also writes `expected_results.json` per folder, generated from the ground truth (never typed
by hand): the list of flag ids that must appear, and the expected precursor status per lot.

### The clean folder (Sri Example Fasteners, fictional, reporting year 2026)

| Item | Value |
|---|---|
| Product | Carbon steel screws and bolts, CN 73181558 and 73181568 |
| Product made | 170 t (production register: 12 monthly rows summing to 170 t; each row lists the heat numbers used that month) |
| Scrap produced | 30 t, all pre-consumer (cutting and forging); scrap register says "pre-consumer share 100%" |
| Steel stock | opening 20 t, closing 10 t (stock register) |
| Purchases | Supplier A, a mill ("Example Steel Mill A, synthetic"): 120 t as heats A1, A2, A3 (40 t each). Supplier B, a trader ("Example Steel Traders, synthetic"): 70 t as heats B1, B2 (35 t each) |
| Opening stock | 20 t, heat A0 from Mill A, produced in 2025 |
| Closing stock | 10 t, all from heat B2 |
| Steel consumed | 20 + 190 - 10 = 200 t (A0 20, A1-A3 120, B1 35, B2 25); mi = 200 / 170 |
| Mill certificates | 6: A0, A1, A2, A3, B1, B2. Each has heat number, grade "SAE 1022 (synthetic)", tonnes, C, Mn, Si, Cr, Ni, other alloy %, mill name, production date |
| Trader delivery note | names Mill B ("Example Steel Mill B, synthetic") and heats B1, B2 |
| Verification report | Mill A, one synthetic page, covering calendar year 2026, states precursor SEE 1.567 t CO2/t. Label it: "Commission example value used as a synthetic stand-in. Not a real mill, not a default value." |
| Mill B | no emissions data |
| Fuel | natural gas for heating and forging, 12 monthly invoices in GJ, summing to 595 GJ (3.5 GJ per t x 170 t); emission factor 56.1 t CO2 per TJ from the invoice footer note "standard factor, see regulatory notes" |
| Shipments | 8 export invoices summing to 160 t, CN codes as above, destinations DE, NL, IT, FR, dates within 2026, each naming the production month(s) it was packed from |

Expected in clean: **no flags.** Precursor statuses:
- A1, A2, A3: `ACTUAL_ALLOWED` (Mill A report covers 2026)
- A0: `DEFAULT_REPORT_PERIOD` (produced 2025; no report covers 2025)
- B1, B2: `DEFAULT_NO_EMISSIONS_DATA` (installation identified through the delivery note, no emissions data)

These three different verdicts in one clean folder are the main demo screen.

### The problem folder: clean folder plus five planted issues (nothing else changed)

1. `MASS_BALANCE`: the scrap register shows 15 t instead of 30 t. Product 170 + scrap 15 = 185 t against 200 t consumed: 15 t unexplained.
2. `CERT_NO_PURCHASE`: an extra mill certificate, heat X9, that appears on no purchase invoice, delivery note or stock register.
3. `PRECURSOR_EVIDENCE`: Mill A states actual emissions, but its verification report covers 2025, not 2026. A1-A3 become `DEFAULT_REPORT_PERIOD`.
4. `FUEL_UNIT`: the August gas invoice states its quantity in kg; the other eleven are in GJ.
5. `CHEMISTRY_RANGE`: on the certificate for heat A2, the Mn and Cr values are swapped (Mn 0.02, Cr 0.85), as if a misread scan put values under the wrong element.

Expected in problem: exactly these five flag ids.

### The trader folder: a legitimate trader chain

Same factory, but all 190 t of purchases come from the trader (heats T1 to T5, 38 t each), with
delivery notes naming Mill B and every heat. Opening stock A0 as in clean; closing stock 10 t from T5.
Expected: **no flags.** Statuses: A0 `DEFAULT_REPORT_PERIOD`; T1-T5 `DEFAULT_NO_EMISSIONS_DATA`.

### Tests (`tests/test_factory.py`)
- Running make_factory twice gives identical ground truth (seed).
- Clean: opening + purchases - closing = 200; production sums to 170; gas sums to 595 GJ; shipments sum to 160.
- Each planted issue is present in problem and absent in clean.
- Every document file exists and every PDF contains the text SYNTHETIC.

## Step 5: reading the documents (`tracecheck/extract.py`, `tools/measure_extraction.py`)

One interface `extract(doc, mode)` with three modes:
- MANUAL: values typed in the review screen.
- CACHED: values read from `data/<folder>/cached_fields.json`. make_factory generates this from the
  ground truth and labels every value `mode: "CACHED"`. Give low confidence (0.55 to 0.75) to the fields
  under the stamp, on the rotated photo, and on the handwritten note, so they show `needs_review`;
  all others 0.95 or higher.
- LIVE: optional. Only if the environment variable `TRACECHECK_LIVE_KEY` is set. Keep this to one
  small function with a clear "LIVE mode not configured" message when the key is absent. Do not spend
  effort here; it is the first thing to cut.

Each field stores: value, unit, source file, page, mode, confidence, needs_review, reviewer, reviewed_at.
Fields below `review_confidence_threshold` in config.yaml are `needs_review`. Fields must be approved
before checks and calculation use them; in demo mode, all fields start approved except the low-confidence ones.

`measure_extraction.py` compares extracted fields with the ground truth and prints accuracy per document
type. In CACHED mode it will print 100 percent; print beside it: "CACHED mode, not a real accuracy measure".

Tests: CACHED loads every document; low-confidence fields are flagged; an unapproved field blocks the calculation with a clear message.

## Step 6: the checks (`tracecheck/checks.py`)

Each check is a pure function taking the reviewed facility data and returning a list of flags. A flag has:
`id`, `severity` (high / medium / low), `message` (plain English a factory manager understands),
`sources` (file and page), `status` (open / accepted with note).

| Flag id | Rule | Message style |
|---|---|---|
| MASS_BALANCE | consumed = opening + purchases - closing; compare with product + scrap; flag if the gap exceeds `mass_balance_tolerance` x consumed; also flag if mi < 1 | "200 t of steel was used, but product and scrap explain 185 t. 15 t is unexplained. Check the scrap register and stock counts." |
| CERT_NO_PURCHASE / PURCHASE_NO_CERT | a heat number on no purchase, delivery note or stock register, or a purchase with no certificate | Say "link missing", never fraud. A trader delivery note naming the mill and heats resolves the link. |
| PRECURSOR_EVIDENCE | a supplier claims actual emissions but no verification report covers the precursor's production year | "Mill A's verification report covers 2025, but this steel was produced in 2026. The default value applies until a 2026 report is received." |
| REPORTING_PERIOD | any production or shipment date outside the reporting year | |
| FUEL_UNIT | fuel invoices for one fuel in different units | "The August gas invoice is in kg; the others are in GJ. Confirm the unit before using it." |
| CHEMISTRY_RANGE | certificate chemistry outside the grade's ranges in config.yaml | "Heat A2 shows Mn 0.02% and Cr 0.85%, outside the SAE 1022 range. The values may have been read under the wrong element. Check the original certificate." |
| PARAMS_MISSING | Mn, Cr, Ni, other alloy %, scrap per tonne, or pre-consumer share missing | |

Add to config.yaml (illustrative, labelled as such):

```yaml
grade_ranges:          # illustrative synthetic ranges, % by mass
  "SAE 1022 (synthetic)":
    Mn: [0.70, 1.00]
    Cr: [0.00, 0.20]
    Ni: [0.00, 0.20]
```

Tests (`tests/test_checks.py`): run all checks on all three folders and compare with expected_results.json.
Clean and trader must give **zero** flags. Problem must give exactly the five planted ids. Add one unit test per check with a small hand-built case.

## Step 7: trace and precursor status (`tracecheck/trace.py`)

Build the chain: shipment -> production month(s) -> heats used -> supplier -> mill. Mark missing links with a reason.

For every heat (lot), return a precursor status with a next action:

| Status | When | Next action text |
|---|---|---|
| ACTUAL_ALLOWED | the producing mill has a verification report that covers the heat's production year | "Keep the verification report with the evidence pack." |
| DEFAULT_REPORT_PERIOD | a report exists but does not cover the production year, or no report covers that year | "Ask <mill> for a verification report covering <year>." |
| DEFAULT_NO_EMISSIONS_DATA | mill identified (directly or through a delivery note) but no emissions data | "Ask <mill> through <trader> for verified emissions data, or accept the default." |
| NO_MILL_LINK | lot cannot be traced to a mill | "Ask <supplier> for a delivery note naming the mill and heat numbers." |

Tests: statuses match expected_results.json for all three folders; one small test for NO_MILL_LINK.

## Step 8: illustrative calculation and Excel export

`tracecheck/factory_calc.py`: compute the synthetic factory's illustrative SEE with calc.py:
own direct = approved gas GJ / product t, times the emission factor; precursor SEE = mass-weighted
average over consumed lots, where ACTUAL_ALLOWED lots use the verified value and all other lots need a
default value. Default values are **not entered** (they must come from Implementing Regulation 2025/2621,
looked up by the human), so the result must be "input missing: default value not entered for <lots>".
Allow a default to be typed in the app (MANUAL mode, labelled "entered by user"); then show the result,
labelled "Illustrative, for evidence preparation".

`tracecheck/export.py` writes an Excel file with openpyxl. First row of every sheet:
"Draft prepared for verifier review. Illustrative. Synthetic data."

1. Issue register: every flag with severity, message, sources, status.
2. Precursor status: every lot, its status and next action.
3. Missing documents and what to ask for.
4. Evidence index: every number used, with source file, page, mode, confidence, reviewer.
5. Input sheet: the fields the Commission's operator emissions report needs (production per CN code, precursor mass and mi, fuel GJ and factor, Mn/Cr/Ni/other %, scrap per tonne, pre-consumer share, per-supplier evidence status), filled from reviewed data, "input missing" where absent.
6. Assumptions and versions.

Tests: the file opens; every number on sheet 4 has a source; the header line is on every sheet.

## Step 9: connect the app

Replace the placeholders in app.py. Keep the existing proof table on the Calculation page.

- Sidebar: folder selector (clean / problem / trader), default **clean**.
- Dashboard: documents, fields reviewed, lots traced, issues open, and the precursor-status counts.
- Documents and review: document list; image of the selected document on the left (render the JPG, or the first PDF page as an image if easy; otherwise a link); its fields on the right with mode and confidence; low-confidence fields highlighted; edit and approve buttons stored in `st.session_state` and saved to `data/<folder>/approvals.json`.
- Trace map: a table per shipment and the **precursor status panel** (one row per lot, colour by status, next action). Keep it a table; a diagram is optional.
- Checks: flags with plain message, severity and sources; accept a flag with a note.
- Calculation: proof table, then the factory's illustrative result or the "input missing" message, with a box to enter a default value per lot.
- Evidence pack: build and download the Excel file.
- Show the extraction mode next to every value. SYNTHETIC banner on every page.

Test (`tests/test_app_smoke.py`): import app.py with a stub streamlit module and call every page function for every folder without errors.

## Step 10: demo mode, offline, README

- The app works with no internet and no key: CACHED mode, generated folders committed to the repo.
- `run.bat` already starts the app; make sure it also works when `data/` exists.
- Update README.md: what it does in five lines, how to run, how to run tests, how to regenerate data (`python tools/make_factory.py`), what is synthetic, what we did not verify, limits.

## Step 11: strict review

Read the whole project as a strict reviewer. Fix, in order of how much they would hurt in front of judges:
bugs; any number written by hand outside tests and the oracle; any regulatory statement not in
REGULATORY_NOTES.md; any Commission example value presented as a default or a real factory value; any
claim of accuracy that was not measured; any secret in a file; anything needing internet in demo mode.

## Step 12: words audit and BUILD_REPORT.md

Search every screen, comment, README and export for: certified, audit-ready, compliant, ISO, guaranteed,
official (allowed only in "Commission's published result"), saves, saving, and any rupee or euro amount.
Replace with safer wording.

Then write `BUILD_REPORT.md` for the team, in plain English, under 2 pages:
1. What was built, screen by screen, and how to show it in the 90-second demo.
2. The actual test output (copy the last line of `pytest -q`).
3. The flags each folder produces and the precursor statuses (from running the code, not typed).
4. Every file, one line each (or point to docs/FILES.md, which you keep updated).
5. What was not verified, what was cut, and anything the team must check by eye (open six documents and confirm each planted issue is visible).

Final 10-point check before finishing:
1. Oracle tests pass; proof shows 2.039 and 2.371.
2. Clean and trader give zero flags; problem gives exactly the five planted flags.
3. The clean folder shows all three precursor verdicts.
4. Every number in the evidence index has a source.
5. Every screen says SYNTHETIC.
6. No banned words.
7. Works offline in CACHED mode.
8. Extraction mode shown next to values.
9. Missing default values say "input missing".
10. Every commit is in git, PROGRESS.md and BUILD_REPORT.md are complete.
