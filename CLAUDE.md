# TraceCheck: instructions for Claude Code

At the start of every session, read these files before doing anything else:
PROJECT_BRIEF.md, RULES.md, docs/REGULATORY_NOTES.md, docs/TEST_ORACLE.md, DECISIONS.md,
BUILD_PLAN.md, and PROGRESS.md if it exists.

- BUILD_PLAN.md is the build specification. Follow it step by step.
- If PROGRESS.md exists, continue from the first step it does not mark as done.
- Follow RULES.md at all times (BUILD_PLAN.md relaxes rule 1 only).
- Use the virtual environment in `.venv` (`.venv\Scripts\python.exe` on Windows).
- Run tests with `python -m pytest -q` and commit after every passing step.
- Keep replies short. Do not paste whole files or long logs into the chat.
