# TraceCheck build report (steps 4 to 12)

Built 2026-10-30 from BUILD_PLAN.md. Everything is synthetic. Step-by-step log: PROGRESS.md. Every file in one paragraph: docs/FILES.md.

## 1. What was built, screen by screen

Start with `run.bat` (or `streamlit run app.py`). Pick a demo folder in the sidebar: **clean** (default), **problem** or **trader**. Every page shows the SYNTHETIC banner.

| Screen | What it shows |
|---|---|
| Dashboard | Documents, fields reviewed, lots traced to a mill, issues open, and counts per precursor status |
| Documents and review | Each document (JPG photo shown, PDF to download) with its fields, mode (CACHED / MANUAL) and confidence. Low-confidence fields are marked ⚠ and can be approved, approved all at once, or corrected (a correction becomes MANUAL) |
| Trace map | **Precursor status panel** (one row per steel lot: status, supplier, mill, production year, tonnes, next action, mode), then shipment → month → heat → supplier → mill rows |
| Checks | Flags with severity, plain message and source documents; accept a flag with a note |
| Calculation | The Commission proof table (2.039 and 2.371, both "yes"), then the factory's illustrative result or the "input missing" message, with a box per lot for a default value "entered by user" |
| Evidence pack | Download the six-sheet Excel pack |

**90-second demo**
1. (10 s) Dashboard, clean folder: 36 documents, 0 issues, three different precursor verdicts.
2. (25 s) Trace map: A1–A3 actual data allowed (Mill A report covers 2026); A0 default because it was made in 2025; B1–B2 default because Mill B, found through the trader's delivery note, has no emissions data. Read one next action aloud.
3. (15 s) Documents and review: the rotated gas photo opens first with its ⚠ fields; approve it.
4. (20 s) Switch to **problem**, open Checks: five flags in plain English, each naming its documents.
5. (15 s) Calculation: the proof matches the Commission; the factory figure says "input missing: default value not entered…" instead of guessing.
6. (5 s) Evidence pack: download. Every sheet starts "Draft prepared for verifier review. Illustrative. Synthetic data."

## 2. Test output

Last line of `python -m pytest -q`:

```
87 passed in 2.31s
```

## 3. Flags and precursor statuses (from running the code)

| Folder | Flags | Precursor statuses |
|---|---|---|
| clean | none | A0 DEFAULT_REPORT_PERIOD; A1, A2, A3 ACTUAL_ALLOWED; B1, B2 DEFAULT_NO_EMISSIONS_DATA |
| problem | MASS_BALANCE, CERT_NO_PURCHASE, PRECURSOR_EVIDENCE, FUEL_UNIT, CHEMISTRY_RANGE | A0 ACTUAL_ALLOWED; A1, A2, A3 DEFAULT_REPORT_PERIOD; B1, B2 DEFAULT_NO_EMISSIONS_DATA |
| trader | none | A0 DEFAULT_REPORT_PERIOD; T1–T5 DEFAULT_NO_EMISSIONS_DATA |

Flags are the same at demo start (8 low-confidence fields per folder still awaiting review) and with every field approved.
Calculation with every field approved: clean says "input missing: default value not entered for A0, B1, B2"; problem also says the August gas quantity is in kg, so the unit must be confirmed; trader needs defaults for A0 and T1–T5.

## 4. Files

See docs/FILES.md (kept up to date at every step).

## 5. Not verified, cut, deviations, and checks for the team

**Not verified**
- Extraction accuracy on real documents. The demo runs in CACHED mode, so `tools/measure_extraction.py` prints 100 percent "by construction"; it is not a measure.
- The app was checked in a browser (dashboard, trace map, one approval, calculation, problem checks, no console errors), but not with Wi-Fi switched off and not through `run.bat` from a fresh folder.
- The Excel file was opened with openpyxl in tests, not in Excel itself.
- Only one JPG (EX-03, the stamped photo) was looked at by eye; the PDFs were checked only for the text SYNTHETIC.
- Default values for CN 7318 are not in the app. BUILD_PLAN names Implementing Regulation 2025/2621 as their source, but that is not in REGULATORY_NOTES.md, so the app and README do not cite it.

**Cut**: LIVE extraction (only a "not configured" message); a PDF preview image (PDFs are a download button instead); a trace diagram (tables only).

**Deviations from the plan, and why**
- The gas invoice footer does not say "standard factor, see regulatory notes". 56.1 t CO2/TJ is a Commission worked-example value and is not in REGULATORY_NOTES.md, so the footer labels it as a synthetic stand-in, not a default (RULES.md rules 3 and 8).
- In the problem folder Mill A's report covers 2025, so A0 (made in 2025) becomes ACTUAL_ALLOWED there. This follows note 5; the plan did not say what A0's status should be in the problem folder.
- PRECURSOR_EVIDENCE fires only for purchases whose invoice claims actual emissions. Opening stock A0 makes no claim, so the clean folder stays at zero flags.
- Low-confidence fields: all six fields on the rotated March gas photo, the stamped tonnes on EX-03, and the handwritten stock note. None of them feed a check, so the flags do not change before review, but the gas photo blocks the calculation until it is approved.

**Check by eye before the demo**: open these documents in data/problem/docs and confirm each planted issue is visible: `scrap_register.pdf` (15 t), `MC-X9.pdf` (extra heat), `VR-A.pdf` (covers 2025), `GI-08.pdf` (unit kg), `MC-A2.pdf` (Mn 0.02, Cr 0.85). Also open `data/clean/docs/GI-03.jpg` (rotated photo) and `stock_register.pdf` (handwritten note).

## Final 10-point check

| # | Check | Result |
|---|---|---|
| 1 | Oracle tests pass; proof shows 2.039 and 2.371 | Yes (tests, and seen on the Calculation page) |
| 2 | Clean and trader zero flags; problem exactly the five | Yes (tests/test_checks.py) |
| 3 | Clean folder shows all three verdicts | Yes (tests/test_trace.py, Trace map) |
| 4 | Every number in the evidence index has a source | Yes (tests/test_export.py) |
| 5 | Every screen says SYNTHETIC | Yes (banner on every page; every document) |
| 6 | No banned words | Yes (tests/test_words.py; exports and documents also searched) |
| 7 | Works offline in CACHED mode | No network calls in the code, usage statistics off, localhost only. Not tried with Wi-Fi off |
| 8 | Extraction mode next to values | On the review, precursor status, calculation and evidence-index tables. The Checks page shows sources, not modes |
| 9 | Missing defaults say "input missing" | Yes |
| 10 | Every step committed; PROGRESS.md and BUILD_REPORT.md complete | Yes, one commit per step |
