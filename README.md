# TraceCheck

TraceCheck is a hackathon prototype for BuildX 2026. All data is synthetic.

What it does, in five lines:

1. Reads a small steel-product maker's records (mill certificates, invoices, gas bills, registers) into fields a person reviews and approves.
2. Links purchases, mill certificates (heat numbers), production, scrap and export shipments.
3. Gives every steel lot a precursor status: actual data allowed, or default applies (report covers the wrong year, no emissions data, or no mill link), each with a next action.
4. Runs reconciliation checks and raises plain-English flags that name the source documents.
5. Calculates an illustrative specific embedded emissions figure, reproduces the Commission's worked example as a self-test, and exports an Excel evidence pack as a draft prepared for verifier review.

**AI reads, code calculates, a person approves.** Gemini reads document images into fields (LIVE mode) and drafts supplier requests. It never calculates, never decides a flag or a precursor status, and never sends anything.

## Reading documents with AI (optional)

Set the environment variable `GEMINI_API_KEY` (never write it in a file). Optionally set `GEMINI_MODEL`; the default is `gemini-3.5-flash`. On the Documents page press **Read with AI** for the selected document, or upload your own photo. Results are saved to `data/<folder>/live_fields.json` so they replay offline. Without a key or internet the app says "LIVE mode not available, using CACHED results" and carries on.

## Run it (Windows)

Double-click `run.bat`, or in a terminal inside this folder:

```
run.bat
```

The first run creates a virtual environment in `.venv` and installs packages (needs internet once). After that it starts offline. Your browser opens at http://localhost:8501. Pick a scenario (Clean factory, Factory with problems, Trader supply chain) in the top bar.

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

Approvals, typed defaults and accepted flags last only for the current browser session and are never written to a file. Reloading the page or opening a new tab starts from the original state. Opening the app with `?reset=1` in the URL does the same and removes the parameter.

## What is synthetic

Everything. The factory "Sri Example Fasteners", the mills, the trader and every document are fictional, and every page and document says SYNTHETIC. The verified precursor value for Mill A and the gas emission factor are values from the Commission's worked example, used as synthetic stand-ins; they are never presented as default values or real factory values.

## What we did not verify

- Extraction accuracy on real documents (not measured; the demo runs in CACHED mode).
- Default values for CN 7318. They are not shipped with the app; the team must look them up. Until a value is typed in, the app says "input missing".
- The regulatory notes rest on the Commission's guidance and on secondary sources quoting the regulations.
- The chemistry ranges and the mass-balance tolerance in config.yaml are illustrative.

## Limits

TraceCheck does not issue a verification, replace a verifier, submit to the CBAM Registry, calculate the CBAM obligation, show any money figure, or track electricity. LIVE extraction needs a Gemini key and internet; its accuracy on the synthetic documents is in docs/ACCURACY.md.
