# Decisions

- 2026-10-29: Keep TraceCheck for BuildX. Pitch order retention and verifier speed, not savings. The factory is the user; consultants and verifiers are the first payer to test.
- 2026-10-29: The main demo screen is the lot-by-lot precursor status (actual allowed / default: wrong-year report / default: no mill link).
- 2026-10-29: Organisers confirmed code written before the event and AI coding tools are allowed. Team size is 4. IP and scoring still unknown.
- 2026-10-29: Add a fifth planted issue in the problem folder: a mill certificate where a chemistry value sits under the wrong element.
- 2026-10-29: Calculator functions return a Result (value, missing). A missing input gives a message and no number.
- 2026-10-29: requirements.txt uses minimum versions, because the first build could not reach the package index. After the first install on the team laptop, run `pip freeze > requirements-lock.txt` and commit it.
- 2026-10-30: Steps 4 to 12 are specified in BUILD_PLAN.md for Claude Code to build autonomously, committing and logging each step in PROGRESS.md.
- 2026-10-30: The clean folder carries all three precursor verdicts (actual allowed, default for report period, default for no emissions data); this is the main demo screen. The problem folder carries five planted flags.
- 2026-10-30: LIVE extraction is a stub unless a key is set; CACHED mode is the demo mode.
- 2026-10-30: Step 13 uses the Gemini API for LIVE extraction. Model: gemini-3.8-flash, the newest stable Flash model (not lite, preview, image or TTS) in the key's model list on 2026-10-30; override with GEMINI_MODEL. PDFs are rendered to PNG before sending, so the model reads pixels, not the PDF text layer.
- 2026-10-30: LIVE fields replace CACHED fields for a document only after the user presses Read with AI (choice kept in the git-ignored live_use.json). Demo start (saved=False) always uses CACHED. Uploaded documents are read for review only and kept in the git-ignored data/uploads.
- 2026-10-30: Default LIVE model changed from gemini-3.8-flash to gemini-3.5-flash. Measured on this key the same day: a gas-invoice photo read took 89 s on 3.8 and 5 s on 3.5 with identical fields; a five-word text reply took 39 to 89 s (with 504 timeouts) on 3.8 and 3.7, 4 s on 3.5. A 90 s wait is not usable on stage. GEMINI_MODEL=gemini-3.8-flash switches back. Requests time out after 90 s and fall back.
- 2026-10-30: Approvals, typed defaults, accepted flags and LIVE choices live only in st.session_state, so a reload or new tab starts from the original demo state and every rehearsal is fresh. This replaces approvals.json, flag_notes.json and live_use.json, and the Reset demo buttons. Hidden reset: ?reset=1. Saved LIVE readings stay in live_fields.json.
