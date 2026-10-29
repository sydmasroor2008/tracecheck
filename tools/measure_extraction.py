"""Compare extracted fields with the synthetic ground truth, per document type.

    python tools/measure_extraction.py [folder] [mode]

In CACHED mode the fields were generated from the ground truth, so the score
is 100 percent by construction. It is not a real accuracy measure.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracecheck.data import folder_path, get_path, read_json  # noqa: E402
from tracecheck.extract import extract_folder  # noqa: E402


def measure(folder: str, mode: str = "CACHED") -> dict:
    """{document type: (correct, total)}"""
    truth = read_json(folder_path(folder) / "ground_truth.json")
    types = {d["file"]: d["type"] for d in read_json(folder_path(folder) / "cached_fields.json")["documents"]}
    scores = {}
    for f in extract_folder(folder, mode):
        kind = types[f["source_file"]]
        correct, total = scores.get(kind, (0, 0))
        scores[kind] = (correct + (f["value"] == get_path(truth, f["key"])), total + 1)
    return scores


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "clean"
    mode = sys.argv[2] if len(sys.argv) > 2 else "CACHED"
    note = "  (CACHED mode, not a real accuracy measure)" if mode == "CACHED" else ""
    for kind, (correct, total) in sorted(measure(folder, mode).items()):
        print(f"{kind:22s} {correct:4d}/{total:<4d} {100 * correct / total:5.1f}%{note}")


if __name__ == "__main__":
    main()
