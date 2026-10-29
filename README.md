# TraceCheck

TraceCheck is a hackathon prototype for BuildX 2026. All data is synthetic.

What it does, in five lines:

1. Reads a small steel-product maker's records (mill certificates, invoices, gas bills, registers) into fields a person reviews and approves.
2. Links purchases, mill certificates (heat numbers), production, scrap and export shipments.
3. Gives every steel lot a precursor status: actual data allowed, or default applies (report covers the wrong year, no emissions data, or no mill link), each with a next action.
4. Runs reconciliation checks and raises plain-English flags that name the source documents.
5. Calculates an illustrative specific embedded emissions figure, reproduces the Commission's worked example as a self-test, and exports an Excel evidence pack as a draft prepared for verifier review.

## Run it (Windows)

Double-click `run.bat`, or in a terminal inside this folder:

```
run.bat
```

The first run creates a virtual environment in `.venv` and installs packages (needs internet once). After that it starts offline. Your browser opens at http://localhost:8501. Pick a demo folder (clean, problem, trader) in the sidebar.

Manual steps if you prefer:

```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python check_env.py
streamlit run app.py
```

## Run the tests

```
.venv\Scripts\python -m pytest -q
```

## Regenerate the demo data

```
.venv\Scripts\python tools\make_factory.py
```

This rebuilds `data/clean`, `data/problem` and `data/trader` from a fixed seed, so the result is the same every time. `python tools\measure_extraction.py clean` compares the cached fields with the ground truth (in CACHED mode this is 100 percent by construction and is not a real accuracy measure).

Review approvals and accepted-flag notes are saved in `data/<folder>/approvals.json` and `flag_notes.json`. Delete them, or use "Reset all reviews in this folder", to start the demo fresh.

## What is synthetic

Everything. The factory "Sri Example Fasteners", the mills, the trader and every document are fictional, and every page and document says SYNTHETIC. The verified precursor value for Mill A and the gas emission factor are values from the Commission's worked example, used as synthetic stand-ins; they are never presented as default values or real factory values.

## What we did not verify

- Extraction accuracy on real documents (not measured; the demo runs in CACHED mode).
- Default values for CN 7318. They are not shipped with the app; the team must look them up. Until a value is typed in, the app says "input missing".
- The regulatory notes rest on the Commission's guidance and on secondary sources quoting the regulations.
- The chemistry ranges and the mass-balance tolerance in config.yaml are illustrative.

## Limits

TraceCheck does not issue a verification, replace a verifier, submit to the CBAM Registry, calculate the CBAM obligation, show any money figure, or track electricity. LIVE extraction is not built; MANUAL and CACHED modes only.
