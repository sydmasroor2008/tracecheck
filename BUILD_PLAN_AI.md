# BUILD PLAN ADD-ON: real AI with the Gemini API (Step 13)

Do this only after BUILD_PLAN.md Steps 4 to 12 are done and all tests pass.
It turns the LIVE extraction stub into real AI reading, and adds AI-drafted supplier requests.
Same working rules as BUILD_PLAN.md: test, commit, log in PROGRESS.md.

Design line (put it on the app's Documents page and in the README):
**"AI reads, code calculates, a person approves."**
Gemini never calculates, never decides a flag or a precursor verdict, and never sends anything.

## 13a. Real LIVE extraction with Gemini (OCR + LLM in one step)

- Add `google-genai` to requirements.txt. Use `from google import genai`.
- API key from the environment variable `GEMINI_API_KEY` only. Never write it in any file. Add `.env` to .gitignore (already there).
- Model name from the environment variable `GEMINI_MODEL`. If unset, list the available models with the client once, pick a current Flash model that accepts images, and record the choice in DECISIONS.md.
- In `tracecheck/extract.py`, LIVE mode:
  1. Send the document image (JPG, or a PDF page rendered to an image) with a short prompt per document type.
  2. Ask for structured JSON using the SDK's response schema, built from the same pydantic models as CACHED mode (mill certificate: heat number, grade, tonnes, C, Mn, Si, Cr, Ni, other alloy %, mill name, production date; invoice: supplier, date, tonnes, heats; gas invoice: month, quantity, unit; delivery note: mill, heats).
  3. Ask the model to also return, per field, a confidence from 0 to 1 and `null` when a value is not visible. Tell it never to guess.
  4. Validate with pydantic. If validation fails, mark every field `needs_review`.
  5. Store each field with `mode: "LIVE"`, the model name, and the time.
- If the key is missing or the network fails: show "LIVE mode not available, using CACHED results" and fall back. The app must never crash on stage.
- Add a "Read with AI" button on the Documents page for the selected document, and a file uploader so a user can upload their own certificate photo.
- Cache every LIVE result to `data/<folder>/live_fields.json`, so a run done once with internet can be replayed offline.

## 13b. Measure real accuracy

- `tools/measure_extraction.py --mode live --folder problem` runs LIVE on every synthetic document and compares with ground truth. Print field accuracy per document type and per field (heat number, tonnes, Mn, Cr, ...), and the number of fields sent to review.
- Save the printed table to `docs/ACCURACY.md` with the date and model name. These numbers come only from running the script.
- Check that the CHEMISTRY_RANGE check still catches the swapped Mn/Cr certificate when its fields come from LIVE mode.
- If the folder `data/public_samples/` exists (public sample certificates the team adds, with a SOURCES.md listing where each came from), run LIVE on them too and report results separately as "public sample documents, no ground truth: fields shown for human review". Never mix them into the synthetic accuracy number.

## 13c. AI-drafted supplier requests

- For each lot whose precursor status is not ACTUAL_ALLOWED, a "Draft request" button asks Gemini to write a short, polite email to the mill or trader asking for exactly the missing evidence (taken from the status and next action; for example, a verification report covering 2026 for heats A1 to A3).
- The draft appears in an editable text box labelled "AI draft, review before sending". The app never sends email.
- Without a key, use a plain template so the button still works offline.

## Tests

- Unit tests mock the Gemini client (no network in tests): valid JSON is stored as LIVE; invalid JSON sends all fields to review; low confidence sets needs_review; a missing key falls back to CACHED.
- No test may need the real API or the key.

## Pitch facts this step produces (fill the evidence slide only from these)

- Field accuracy of LIVE extraction on N synthetic documents (from docs/ACCURACY.md).
- How many misread fields the checks and review caught.
- Cost: number of pages read and the model name; do not state a rupee cost unless measured from billing.
