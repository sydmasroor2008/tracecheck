# TraceCheck

TraceCheck is a hackathon prototype for BuildX 2026. It helps a small Indian steel-product maker turn scattered records (mill certificates, invoices, gas bills, registers) into a checked, traceable data pack for CBAM, as a draft prepared for verifier review. All data is synthetic. The calculator reproduces the European Commission's published worked example.

## Run it (Windows)

Double-click `run.bat`, or in a terminal inside this folder:

```
run.bat
```

The first run creates a virtual environment in `.venv` and installs packages (needs internet once). After that it starts the app offline. Your browser opens at http://localhost:8501.

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
.venv\Scripts\activate
pytest -q
```

## What is synthetic

Everything. The factory "Sri Example Fasteners" is fictional. Values from the Commission's worked example are labelled as example values, never as default values or real factory values.

## What we did not verify

- Extraction accuracy on real documents (not measured).
- Default values for CN 7318 from Implementing Regulation 2025/2621 (not entered; the app says "input missing").
- The regulatory notes rest on the Commission's guidance and on secondary sources quoting the regulations.

## Limits

TraceCheck does not issue a verification, replace a verifier, submit to the CBAM Registry, calculate the official CBAM obligation, show any saving, or track electricity.
