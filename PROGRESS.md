# Progress log

- Step 1 (plan and project files): done 2026-10-29.
- Step 2 (walking skeleton): done 2026-10-29. app.py with six pages, SYNTHETIC banner, run.bat, check_env.py.
- Step 3 (calculator and oracle): done 2026-10-29. tracecheck/calc.py; 20 tests pass; reproduces 2.039 and 2.371.
- Step 4 (synthetic factory): done 2026-10-30. tools/make_factory.py, tracecheck/model.py, tracecheck/data.py; data/clean (36 docs), problem (37), trader (40), each with ground_truth.json, expected_results.json, cached_fields.json; 2 JPG photos per folder (rotated gas invoice, stamped export invoice), 3 certificate layouts, handwritten note on the stock register. 33 tests pass.
  Deviation: gas invoice footer says "Commission worked-example value used as a synthetic stand-in, not a default value" instead of "standard factor, see regulatory notes" (56.1 is not in REGULATORY_NOTES.md; RULES.md rules 3 and 8 win).
  Note: in the problem folder the Mill A report covers 2025, so A0 (produced 2025) becomes ACTUAL_ALLOWED there. This follows note 5; the plan did not state A0's status for problem.
