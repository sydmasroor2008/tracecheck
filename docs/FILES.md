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
