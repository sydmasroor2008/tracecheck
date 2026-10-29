# Files, in plain English

**PROJECT_BRIEF.md** — What TraceCheck is and is not. The AI agent reads it first in every chat. If the brief and the code disagree, the brief wins.

**RULES.md** — Thirteen rules the AI agent must follow, such as "never invent a regulatory fact" and "never write a result number by hand".

**CLAUDE.md** — Read automatically by Claude Code at the start of every session. It points to the files below and to BUILD_PLAN.md.

**BUILD_PLAN.md** — The full specification for steps 4 to 12: the synthetic factory, the checks, the trace and precursor status, the export and the app screens. Claude Code builds from it.

**PROGRESS.md** — A short log of each finished step, so a new session can continue where the last one stopped.

**DECISIONS.md** — Every team decision with its date, so nobody re-argues settled points.

**docs/REGULATORY_NOTES.md** — The only regulatory facts the code may use. Notes 14 to 17 are pitch context and are not used in any calculation.

**docs/TEST_ORACLE.md** — The Commission's worked example (2.039 and 2.371). The tests must reproduce it.

**tracecheck/calc.py** — The calculator: mass ratio, own fuel emissions per tonne, specific embedded emissions, mass-weighted average, and rounding. Each function returns a Result: a number, or a clear "input missing" message and no number. It never guesses a missing value.

**tests/test_oracle.py** — Checks that the calculator gives exactly 2.039 and 2.371 when intermediate values are rounded to 3 decimals, as the Commission shows them, and within 0.002 without rounding. Also checks the "about 90 percent from steel" claim on slide 4.

**tests/test_calc.py** — Checks weighted averages, rounding, and that a missing value (for example a default value not yet entered) stops the calculation with a message.

**app.py** — The Streamlit app with six pages. Right now the Calculation page shows the live proof table; the other pages are placeholders for later steps.

**check_env.py** — Prints the Python version and each package version, and says what is missing.

**run.bat** — One command for Windows: sets up the environment the first time, checks it, and starts the app.

**config.yaml** — Settings such as the mass-balance tolerance. Illustrative values to agree with a consultant.

**requirements.txt, pytest.ini, .gitignore** — Package list, test settings, and files Git should ignore.

**tools/make_factory.py** — Builds the three synthetic demo folders from a fixed random seed (2026). First it writes the ground truth (every purchase, certificate, register row, invoice and shipment) and the expected flags and precursor statuses worked out from it. Then it draws the documents: PDFs with reportlab and two JPG "phone photos" with Pillow, all marked SYNTHETIC. It also writes cached_fields.json, the CACHED extraction results the app reads.

**tracecheck/model.py** — Pydantic models describing the ground truth and one extracted field. make_factory.py checks its output against them before writing. The app itself never reads the ground truth.

**tracecheck/data.py** — Loads a demo folder: settings, extracted fields, saved approvals and accepted-flag notes. It builds the "facility data" from approved fields only; a field still awaiting review counts as missing. It also records the source document and extraction mode of every value.

**data/clean, data/problem, data/trader** — The generated demo folders. clean has no planted issues, problem has exactly five, trader buys all steel through a trader. Regenerate them with `python tools/make_factory.py`.

**tests/test_factory.py** — Checks the seed gives identical data, the clean totals (200 t consumed, 170 t made, 595 GJ gas, 160 t shipped), that each planted issue is in problem and not in clean, and that every document exists and says SYNTHETIC.

**tracecheck/extract.py** — One function, `extract(doc, mode)`, for reading a document into fields. CACHED reads saved results from cached_fields.json and works offline. MANUAL wraps values a person typed. LIVE is a placeholder that says "LIVE mode not configured" unless the environment variable TRACECHECK_LIVE_KEY is set, and is not built in this prototype.

**tools/measure_extraction.py** — Compares extracted fields with the ground truth and prints the share that match, per document type. In CACHED mode it prints 100 percent with the note "CACHED mode, not a real accuracy measure", because the cached values were made from the ground truth.

**tests/test_extract.py** — Checks that CACHED mode loads every document, that the low-confidence fields (photo, stamp, handwritten note) need review and start unapproved, and that LIVE mode without a key gives a clear message.

**tracecheck/checks.py** — The reconciliation checks. Each one takes the reviewed facility data and returns flags with an id, a severity, a plain-English message and the source documents. Missing links are called "link missing", never fraud. A flag can be accepted with a note, which is saved in data/<folder>/flag_notes.json.

**tests/test_checks.py** — Runs all checks on the three demo folders and compares them with expected_results.json: clean and trader give zero flags, problem exactly the five planted ones. It also has one small hand-built case for each check.

**tracecheck/trace.py** — Follows each export shipment back to the production months it was packed from, the heats used in those months, the supplier and the mill. It gives every steel lot a precursor status (actual data allowed, default because the report covers the wrong year, default because the mill has no emissions data, or no mill link) and a named next action. Missing links are listed with a reason.

**tests/test_trace.py** — Checks the precursor statuses and consumed tonnes against expected_results.json for all three folders, the next-action wording, a hand-built NO_MILL_LINK case, and that every clean shipment traces to a mill.

**tracecheck/factory_calc.py** — Works out the synthetic factory's illustrative specific embedded emissions with the calculator in calc.py. Lots with actual data allowed use the mill's verified value, and every other lot needs a default value typed by the user. Until then, or while a needed field awaits review or a fuel unit is unconfirmed, it says "input missing" and gives no number.

**tracecheck/export.py** — Writes the Excel evidence pack with six sheets: issue register, precursor status, missing documents, evidence index, input sheet for the Commission's operator emissions report template, and assumptions and versions. Every sheet starts with "Draft prepared for verifier review. Illustrative. Synthetic data." Every number in the evidence index carries its source file, page, mode and reviewer.

**tests/test_factory_calc.py** — Checks that the factory result says "input missing" while defaults are not entered, while a field awaits review, or while a fuel unit is wrong. With test defaults it recomputes the result independently from the data.

**tests/test_export.py** — Opens the Excel file for every folder, checks the header line on every sheet, that every number in the evidence index has a source, and that the problem folder's issues and "input missing" values appear.

**app.py** — The Streamlit app with six pages and a demo-folder selector (clean, problem, trader). Dashboard counts; Documents and review shows each document with its fields, mode and confidence, and lets a reviewer approve or correct values; Trace map shows the lot-by-lot precursor status and the shipment chains; Checks lists flags and lets you accept one with a note; Calculation keeps the Commission proof table and shows the factory's illustrative result or "input missing"; Evidence pack downloads the Excel file. Every page shows the SYNTHETIC banner.

**tests/test_app_smoke.py** — Imports app.py with a fake streamlit module and calls every page for every demo folder, so a broken page is caught without starting a browser.

**.streamlit/config.toml** — Streamlit settings for the demo laptop: no usage statistics sent, the app only listens on localhost, and a minimal toolbar. This keeps the app fully offline.

**README.md** — What TraceCheck does in five lines, how to run it, how to run the tests, how to regenerate the demo data, what is synthetic, what was not verified, and its limits.

**tests/test_words.py** — Searches app.py, the tracecheck and tools code, README, run.bat and config.yaml for the banned words (certified, audit-ready, compliant, ISO, guaranteed, official, saves or saving, and money amounts). It fails if any comes back.

**BUILD_REPORT.md** — The team's summary of steps 4 to 12: each screen and a 90-second demo script, the test result, the flags and precursor statuses each folder gives, what was not verified or was cut, and the final 10-point check.
