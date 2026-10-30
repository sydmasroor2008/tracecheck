"""Words audit (RULES.md rule 13, BUILD_PLAN.md step 12): no banned words on screens, code or README."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED = re.compile(r"certif(ied|y)|audit-ready|compliant|\bISO\b|guarantee|official|(?<!\.)\bsaves?\b|"
                    r"saving|rupee|₹|€|\bEUR\b|\bINR\b", re.IGNORECASE)
FILES = (["app.py", "ui.py", "static/style.css", "README.md", "run.bat", "config.yaml"]
         + [str(p.relative_to(ROOT)) for p in (ROOT / "tracecheck").glob("*.py")]
         + [str(p.relative_to(ROOT)) for p in (ROOT / "tools").glob("*.py")])


def test_no_banned_words():
    hits = []
    for name in FILES:
        for n, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), 1):
            if BANNED.search(line):
                hits.append(f"{name}:{n}: {line.strip()}")
    assert hits == []
