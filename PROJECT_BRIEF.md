# PROJECT BRIEF: TraceCheck (hackathon prototype)

Goal: a small offline web app (Python, Streamlit) that helps a small Indian
steel-product maker turn scattered records into a checked, traceable data
pack for CBAM, before it goes to an EU buyer or an accredited verifier.

Customer (user): operator of a factory that makes steel products (for example
screws, bolts and nuts, CN heading 7318) from purchased steel rod (CN 7213).
First payer to test: CBAM consultants and verifiers who serve many factories.

The app does:
1. Reads documents into structured fields. A human reviews and approves
   uncertain fields.
2. Links steel purchases, mill certificates (heat numbers), production, scrap
   and shipments.
3. Gives every steel lot a PRECURSOR STATUS: "actual data allowed" (mill has a
   verification report covering the production year), "default applies:
   report covers wrong year", or "default applies: no mill link". Each status
   has a named next action. This is the main demo screen.
4. Runs reconciliation checks and raises flags with the source documents.
5. Calculates an ILLUSTRATIVE specific embedded emissions figure with the
   Commission's formula, and reproduces the Commission's worked example as a
   self-test.
6. Exports an Excel evidence pack: issue register, missing-documents list,
   evidence index, and an input sheet for the Commission's emissions report
   template.

The app does NOT: certify anything, replace a verifier, submit to any EU
registry, calculate the official CBAM obligation, show any rupee or euro
saving, track electricity, or claim compliance.

Stack: Python 3.11 or newer, Streamlit, pandas, pydantic, openpyxl, reportlab
(to make synthetic PDFs), Pillow, PyYAML, pytest. Plain JSON files. No login.

Data: all synthetic and labelled SYNTHETIC on every page. A fictional factory
called Sri Example Fasteners.

Extraction modes (the app shows which mode produced each value): MANUAL
(typed), CACHED (saved results), LIVE (optional AI service, key from an
environment variable, never in a file).

Honesty: use the words 'draft prepared for verifier review'. Never write
certified, audit-ready, compliant or ISO. Calculation outputs are labelled
'illustrative, for evidence preparation'.

Definition of done for every step: the command runs, the tests pass, and the
output is shown to the human.
