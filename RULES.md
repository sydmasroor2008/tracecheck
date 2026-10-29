RULES FOR THE AGENT

1. Work on one step at a time. Stop and wait for the human after each step,
   except when BUILD_PLAN.md says to continue autonomously; then run the tests,
   commit and log each step in PROGRESS.md before moving on.
2. Never use real personal or company data. All data is synthetic.
3. Never invent a regulatory fact. Use only docs/REGULATORY_NOTES.md. If you
   need a rule that is not there, stop and ask the human.
4. All arithmetic is done in plain Python functions with unit tests. Never
   ask a language model to calculate.
5. Never write result numbers by hand into any file. Numbers come only from
   running the code.
6. Never put keys or secrets in files. Use environment variables.
7. Write tests with every piece of logic. Never change a test just to make it
   pass. Fix the code. If a test is wrong, say so and explain why.
8. A value from the Commission's worked example must never be labelled as a
   default value or as a real factory's value.
9. If a needed input is missing (for example a default value), the app must
   say 'input missing' and refuse to give a total. It must never guess.
10. Keep the code simple. Plain Python is better than clever design.
11. Explain each file you create in 3 to 5 sentences of simple English in
    docs/FILES.md.
12. At the end of every reply, list what you did not verify or are unsure
    about.
13. Never use the words certified, audit-ready, compliant, ISO or guaranteed
    in code, comments, screens or the README.
