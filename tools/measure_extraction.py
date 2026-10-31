"""Compare extracted fields with the synthetic ground truth.

    python tools/measure_extraction.py --folder clean --mode cached
    python tools/measure_extraction.py --folder problem --mode live            (calls the Gemini API)
    python tools/measure_extraction.py --folder problem --mode live --replay   (uses live_fields.json)

In CACHED mode the fields were generated from the ground truth, so the score
is 100 percent by construction. It is not a real accuracy measure.
LIVE mode reads every document with Gemini, prints accuracy per document type
and per field, the fields sent to review, and whether the checks still find the
planted issues. It writes the printed report to docs/ACCURACY.md and the headline
numbers to data/accuracy.json, which the app reads for its accuracy line.
"""

import argparse
import datetime
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracecheck import data, extract  # noqa: E402
from tracecheck.checks import run_all  # noqa: E402
from tracecheck.data import folder_path, get_path, read_json, write_json  # noqa: E402
from tracecheck.extract import extract_folder  # noqa: E402
from tracecheck.trace import lots  # noqa: E402

REPORT = ROOT / "docs" / "ACCURACY.md"
PUBLIC = data.DATA / "public_samples"


def measure(folder: str, mode: str = "CACHED") -> dict:
    """{document type: (correct, total)} for CACHED fields."""
    truth = read_json(folder_path(folder) / "ground_truth.json")
    types = {d["file"]: d["type"] for d in data.load_documents(folder)}
    scores = {}
    for f in extract_folder(folder, mode):
        kind = types[f["source_file"]]
        correct, total = scores.get(kind, (0, 0))
        scores[kind] = (correct + same(f["value"], get_path(truth, f["key"])), total + 1)
    return scores


def same(a, b) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(map(same, a, b))
    num = (int, float)
    if isinstance(a, num) and isinstance(b, num) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-9
    if isinstance(a, str) and isinstance(b, str):
        return " ".join(a.split()) == " ".join(b.split())
    return a == b


def field_name(key: str, kind: str) -> str:
    """'certificates[2].chemistry.Mn' -> 'chemistry.Mn'; 'stock.opening[0].heat' -> 'stock.opening.heat'"""
    name = re.sub(r"\[\d+\]", "", key)
    return name.split(".", 1)[1] if extract._list_model_type(kind) else name


class QuotaStop(RuntimeError):
    """The API quota is used up; finished documents are already in live_fields.json."""


def quota_kind(text: str) -> str:
    """'day', 'minute' or '' from a Gemini 429 message."""
    if "429" not in text and "RESOURCE_EXHAUSTED" not in text:
        return ""
    if "PerDay" in text or "per day" in text:
        return "day"
    return "minute"


def retry_seconds(text: str) -> float:
    """'retryDelay': '29s' -> 29.0 (the quota message also says 'retry in 18m30.5s')."""
    m = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s", text)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", text)
    if m and any(m.groups()):
        h, mi, s = (float(g or 0) for g in m.groups())
        return h * 3600 + mi * 60 + s
    return 60.0


def read_live(folder: str, docs: list, client=None, replay: bool = False, resume: bool = False,
              tries: int = 3, pause: float = 0.0, max_quota_errors: int = 3, sleep=time.sleep) -> dict:
    """{doc file: LIVE result or None}. Each new result is written to live_fields.json at once.

    resume keeps results already saved with the same model; pause spaces requests (free tier:
    5 per minute). A per-day quota error, or max_quota_errors 429s in a row, raises QuotaStop."""
    saved = extract.load_live(folder)
    out = {}
    in_a_row = 0
    for d in docs:
        old = saved.get(d["file"])
        if replay or (resume and old and old["model"] == extract.model_name()):
            out[d["file"]] = old
            continue
        client = client or extract.make_client()
        out[d["file"]] = None
        for attempt in range(tries):
            try:
                out[d["file"]] = extract.extract_live(folder, d["file"], d["type"], client)
                extract.save_live(folder, d["file"], out[d["file"]])
                in_a_row = 0
                break
            except Exception as exc:  # quota or network: wait and retry, or give up
                text = str(exc)
                print(f"  {d['file']}: attempt {attempt + 1} failed: {text.splitlines()[0][:100]}")
                kind = quota_kind(text)
                if kind:
                    in_a_row += 1
                    if kind == "day" or in_a_row >= max_quota_errors:
                        raise QuotaStop(text)
                    sleep(retry_seconds(text) + 2)
                else:
                    sleep(10 * (attempt + 1))
        print(f"  read {d['file']}: {'ok' if out[d['file']] else 'FAILED'}")
        sleep(pause)
    return out


def compare(folder: str, docs: list, live: dict) -> list:
    """One row per field shown on a document (the CACHED field list), LIVE value against ground truth."""
    truth = read_json(folder_path(folder) / "ground_truth.json")
    rows = []
    for d in docs:
        result = live.get(d["file"])
        got = {f["key"]: f for f in result["fields"]} if result else {}
        for f in extract_folder(folder):
            if f["source_file"] != d["file"]:
                continue
            lf = got.get(f["key"])
            expected = get_path(truth, f["key"])
            rows.append({"doc": d["file"], "kind": d["type"], "key": f["key"],
                         "field": field_name(f["key"], d["type"]), "truth": expected,
                         "value": lf["value"] if lf else None, "found": lf is not None,
                         "correct": bool(lf) and same(lf["value"], expected),
                         "review": (not lf) or lf["needs_review"]})
    return rows


def live_facility(folder: str, live: dict) -> tuple:
    """Facility data with every document's LIVE fields (CACHED where a read failed), demo review rules."""
    cfg = data.load_config()
    threshold = cfg["review_confidence_threshold"]
    ok = {doc for doc, r in live.items() if r}
    fields = [f for f in extract_folder(folder) if f["source_file"] not in ok]
    fields += [f for doc in ok for f in live[doc]["fields"]]
    for f in fields:
        f["approved"] = not (f["confidence"] < threshold or (f["mode"] == "LIVE" and f["needs_review"]))
    return data.build_facility(fields, cfg), cfg


def pct(correct: int, total: int) -> str:
    return f"{100 * correct / total:5.1f}%" if total else "  n/a"


def table(rows: list, group: str) -> list:
    groups = {}
    for r in rows:
        groups.setdefault(r[group], []).append(r)
    lines = [f"| {group} | correct | total | accuracy | sent to review |", "|---|---:|---:|---:|---:|"]
    for name, rs in sorted(groups.items()):
        c = sum(r["correct"] for r in rs)
        lines.append(f"| {name} | {c} | {len(rs)} | {pct(c, len(rs)).strip()} | {sum(r['review'] for r in rs)} |")
    return lines


def model_text(results: list) -> str:
    models = sorted({r["model"] + (f" (served as {r['model_version']})" if r.get("model_version")
                                   and r["model_version"] != r["model"] else "") for r in results}) \
        or [extract.model_name()]
    return ", ".join(models)


def summary(folder: str, live: dict, rows: list) -> dict:
    """The headline numbers saved for the app."""
    results = [r for r in live.values() if r]
    return {"folder": folder, "documents": len(results), "correct": sum(r["correct"] for r in rows),
            "total": len(rows), "date": datetime.date.today().isoformat(),
            "model": ", ".join(sorted({r.get("model_version") or r["model"] for r in results}))}


def report(folder: str, docs: list, live: dict, rows: list) -> list:
    results = [r for r in live.values() if r]
    pages = sum(len(extract.page_images(folder_path(folder) / "docs" / d["file"])) for d in docs if live.get(d["file"]))
    correct = sum(r["correct"] for r in rows)
    wrong = [r for r in rows if not r["correct"]]
    caught = [r for r in wrong if r["review"]]
    missed = [r for r in wrong if not r["review"]]
    right_review = sum(r["correct"] and r["review"] for r in rows)
    known = {r["key"] for r in rows}
    extra_nulls = sum(f["key"] not in known and f["value"] is None for r in results for f in r["fields"])
    out = [
        "# LIVE extraction accuracy",
        "",
        f"- Date: {datetime.date.today().isoformat()} (documents read "
        f"{min((r['read_at'] for r in results), default='-')[:10]} to {max((r['read_at'] for r in results), default='-')[:10]})",
        f"- Model: {model_text(results)}",
        f"- Folder: {folder} (synthetic documents with ground truth)",
        f"- Documents read: {len(results)} of {len(docs)}; pages sent: {pages}; "
        f"schema mismatches: {sum(not r['valid'] for r in results)}",
        "- PDFs were rendered to PNG at 144 dpi, so the model read pixels, not the PDF text layer.",
        f"- Review threshold: confidence below {data.load_config()['review_confidence_threshold']}, "
        "a null value, or a schema mismatch.",
        "",
        "Produced by `python tools/measure_extraction.py --folder " + folder + " --mode live`. "
        "Numbers come only from running the script.",
        "",
        f"**Field accuracy: {correct} / {len(rows)} = {pct(correct, len(rows)).strip()}**",
        "",
        f"- Misread or missing fields: {len(wrong)}; sent to review: {len(caught)}; "
        f"not sent to review (auto-approved): {len(missed)}",
        f"- Correct fields sent to review anyway: {right_review}",
        f"- Null answers for fields the document does not carry (not scored, not shown in the app): {extra_nulls}",
        "",
        "## Per document type", "", *table(rows, "kind"), "",
        "## Per field", "", *table(rows, "field"), "",
    ]
    if wrong:
        out += ["## Misread or missing fields", "", "| document | field | ground truth | LIVE value | sent to review |",
                "|---|---|---|---|---|"]
        out += [f"| {r['doc']} | {r['field']} | {r['truth']} | {r['value'] if r['found'] else '(not returned)'} | "
                f"{'yes' if r['review'] else 'NO'} |" for r in wrong]
        out.append("")
    fac, cfg = live_facility(folder, live)
    flags = sorted({f["id"] for f in run_all(fac, cfg)})
    expected = read_json(folder_path(folder) / "expected_results.json")
    statuses = {lot["heat"]: lot["status"] for lot in lots(fac)}
    out += ["## Checks on LIVE fields", "",
            "Every document's LIVE fields, with the demo review rule: fields sent to review count as missing "
            "until a person approves them.", "",
            f"- Flags raised: {', '.join(flags) or 'none'}",
            f"- Planted flags expected: {', '.join(expected['flags']) or 'none'}",
            f"- Planted flags missed: {', '.join(sorted(set(expected['flags']) - set(flags))) or 'none'}",
            f"- Extra flags (raised by misreads or by fields awaiting review): "
            f"{', '.join(sorted(set(flags) - set(expected['flags']))) or 'none'}",
            f"- CHEMISTRY_RANGE (swapped Mn/Cr certificate) caught from LIVE fields: "
            f"{'yes' if 'CHEMISTRY_RANGE' in flags else 'NO'}",
            f"- Precursor statuses equal to expected: "
            f"{sum(statuses.get(h) == s for h, s in expected['statuses'].items())} of {len(expected['statuses'])}",
            ""]
    return out


def public_samples(client=None) -> list:
    """LIVE on data/public_samples (no ground truth), read as mill certificates, reported apart."""
    files = sorted(p for p in PUBLIC.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".pdf"))
    if not files:
        return []
    out = ["## Public sample documents, no ground truth: fields shown for human review", "",
           "Not part of the accuracy number above. Sources are listed in data/public_samples/SOURCES.md.", ""]
    for p in files:
        fields, message = extract.read_with_ai(None, p.name, "mill_certificate", client, path=p)
        out += [f"### {p.name}", "", message, "", "| field | value | confidence | review |", "|---|---|---:|---|"]
        out += [f"| {f['label']} | {f['value']} | {f['confidence']} | {'yes' if f['needs_review'] else ''} |"
                for f in fields]
        out.append("")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default="clean", choices=data.FOLDERS)
    ap.add_argument("--mode", default="cached", choices=["cached", "live"])
    ap.add_argument("--replay", action="store_true", help="use saved live_fields.json, no API calls")
    ap.add_argument("--resume", action="store_true", help="keep documents already read today with this model")
    ap.add_argument("--pause", type=float, default=13.0, help="seconds between requests (free tier: 5 per minute)")
    args = ap.parse_args()
    if args.mode == "cached":
        for kind, (correct, total) in sorted(measure(args.folder).items()):
            print(f"{kind:22s} {correct:4d}/{total:<4d} {pct(correct, total)}  (CACHED mode, not a real accuracy measure)")
        return
    docs = data.load_documents(args.folder)
    try:
        live = read_live(args.folder, docs, replay=args.replay, resume=args.resume, pause=args.pause)
    except QuotaStop as exc:
        done = extract.load_live(args.folder)
        left = [d["file"] for d in docs if d["file"] not in done or done[d["file"]]["model"] != extract.model_name()]
        print(f"\nStopped: Gemini {quota_kind(str(exc))} quota used up. Full error:\n{exc}\n")
        print(f"Saved in live_fields.json: {len(docs) - len(left)} of {len(docs)} documents. Not read yet: {', '.join(left)}")
        print(f"docs/ACCURACY.md was not changed. When the quota resets, run:\n"
              f"  python tools/measure_extraction.py --folder {args.folder} --mode live --resume")
        sys.exit(2)
    lines = report(args.folder, docs, live, compare(args.folder, docs, live))
    if PUBLIC.exists() and not args.replay:
        lines += public_samples()
    text = "\n".join(lines)
    print(text)
    REPORT.write_text(text + "\n", encoding="utf-8")
    write_json(data.ACCURACY, summary(args.folder, live, compare(args.folder, docs, live)))
    print(f"\nSaved to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
