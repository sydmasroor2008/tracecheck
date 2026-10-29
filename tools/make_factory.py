"""Build the synthetic factory for TraceCheck (BUILD_PLAN.md, steps 4 and 5).

Stage 1 writes data/<folder>/ground_truth.json and expected_results.json.
Stage 2 draws the documents (PDF and JPG) and writes cached_fields.json.
Everything is synthetic and fixed by the random seed. Run:

    python tools/make_factory.py
"""

import datetime
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from tracecheck.data import get_path, load_config, write_json  # noqa: E402
from tracecheck.model import GroundTruth  # noqa: E402

SEED = 2026
YEAR = 2026
FOLDERS = ["clean", "problem", "trader"]

FACTORY = "Sri Example Fasteners (synthetic)"
MILL_A = "Example Steel Mill A, synthetic"
MILL_B = "Example Steel Mill B, synthetic"
TRADER = "Example Steel Traders, synthetic"
GRADE = "SAE 1022 (synthetic)"
CN_CODES = ["73181558", "73181568"]

# Inputs taken from BUILD_PLAN.md. They are inputs, not results.
MONTHLY_PRODUCT_T = [14, 14, 14, 14, 14, 14, 15, 14, 14, 14, 15, 14]
SHIPMENT_T = [18, 22, 20, 25, 15, 20, 21, 19]
DESTINATIONS = ["DE", "NL", "IT", "FR"]
SCRAP_T = 30
OPENING = ("A0", 20, "2025-11-14")
CLOSING_T = 10
# Commission worked-example values (docs/TEST_ORACLE.md) used as synthetic stand-ins.
GAS_GJ_PER_T = 3.5
GAS_EF_T_PER_TJ = 56.1
EXAMPLE_SEE = 1.567
EXAMPLE_LABEL = ("Commission example value used as a synthetic stand-in. "
                 "Not a real mill, not a default value.")
EF_NOTE = ("Emission factor: Commission worked-example value (docs/TEST_ORACLE.md) "
           "used as a synthetic stand-in. Not a default value.")
COUNT_NOTE = "Counted 31 Dec by R. (synthetic). Rack 3 checked twice."

GAS_PHOTO_MONTH = 3        # March gas invoice is a rotated phone photo
STAMPED_SHIPMENT = 3       # third export invoice is a photo with a stamp over the tonnes
LOW_CONFIDENCE = {"photo": 0.70, "stamp": 0.60, "handwritten": 0.55}

PLANTED = ["MASS_BALANCE", "CERT_NO_PURCHASE", "PRECURSOR_EVIDENCE", "FUEL_UNIT", "CHEMISTRY_RANGE"]


# ---------------------------------------------------------------- stage 1

def purchase_plan(folder: str) -> list:
    """(heat, supplier, tonnes, purchase date) in the order the steel is used."""
    if folder == "trader":
        return [(f"T{i}", TRADER, 38, f"{YEAR}-{2 * i - 1:02d}-08") for i in range(1, 6)]
    return [("A1", MILL_A, 40, f"{YEAR}-01-08"), ("A2", MILL_A, 40, f"{YEAR}-03-20"),
            ("A3", MILL_A, 40, f"{YEAR}-06-05"), ("B1", TRADER, 35, f"{YEAR}-08-03"),
            ("B2", TRADER, 35, f"{YEAR}-09-25")]


def chemistry(rng: random.Random) -> dict:
    return {"C": round(rng.uniform(0.18, 0.23), 2), "Mn": round(rng.uniform(0.75, 0.95), 2),
            "Si": round(rng.uniform(0.15, 0.30), 2), "Cr": round(rng.uniform(0.02, 0.12), 2),
            "Ni": round(rng.uniform(0.01, 0.08), 2), "other": round(rng.uniform(0.01, 0.05), 2)}


def overlapping(intervals: list, start: float, end: float) -> list:
    """Names of (name, lo, hi) intervals that overlap [start, end]."""
    return [name for name, lo, hi in intervals if lo < end - 1e-9 and hi > start + 1e-9]


def cumulative(items: list) -> list:
    out, total = [], 0.0
    for name, amount in items:
        out.append((name, total, total + amount))
        total += amount
    return out


def build_ground_truth(folder: str) -> dict:
    rng = random.Random(SEED)
    base = "trader" if folder == "trader" else "clean"
    plan = purchase_plan(base)
    layouts = ["across", "down", "two_column"]

    purchases, certificates = [], []
    heat, tonnes, prod_date = OPENING
    certificates.append({"cert_no": f"MC-{heat}", "heat": heat, "mill": MILL_A, "grade": GRADE,
                         "tonnes": tonnes, "production_date": prod_date,
                         "chemistry": chemistry(rng), "layout": layouts[0]})
    for i, (heat, supplier, tonnes, date) in enumerate(plan, start=1):
        is_mill = supplier != TRADER
        purchases.append({"invoice_no": f"PI-{heat}", "supplier": supplier,
                          "supplier_type": "mill" if is_mill else "trader", "heat": heat,
                          "tonnes": tonnes, "date": date,
                          "emissions_claim": "actual" if is_mill else None})
        made = datetime.date.fromisoformat(date) - datetime.timedelta(days=rng.randint(2, 7))
        certificates.append({"cert_no": f"MC-{heat}", "heat": heat,
                             "mill": MILL_A if is_mill else MILL_B, "grade": GRADE,
                             "tonnes": tonnes, "production_date": made.isoformat(),
                             "chemistry": chemistry(rng), "layout": layouts[i % 3]})

    trader_heats = [p["heat"] for p in purchases if p["supplier_type"] == "trader"]
    if base == "trader":
        delivery_notes = [{"note_no": f"DN-{h}", "supplier": TRADER, "mill": MILL_B, "heats": [h]}
                          for h in trader_heats]
    else:
        delivery_notes = [{"note_no": "DN-B", "supplier": TRADER, "mill": MILL_B, "heats": trader_heats}]

    last_heat = plan[-1][0]
    stock = {"opening": [{"heat": OPENING[0], "tonnes": OPENING[1], "mill": MILL_A}],
             "closing": [{"heat": last_heat, "tonnes": CLOSING_T, "mill": MILL_B}],
             "count_note": COUNT_NOTE}

    # Which heats each month used: walk the lots in order against monthly consumption.
    lot_use = [(OPENING[0], OPENING[1])] + [(h, t) for h, _, t, _ in plan]
    lot_use[-1] = (lot_use[-1][0], lot_use[-1][1] - CLOSING_T)
    consumed = sum(t for _, t in lot_use)
    product = sum(MONTHLY_PRODUCT_T)
    lot_iv = cumulative(lot_use)
    month_use = cumulative([(m, t * consumed / product) for m, t in enumerate(MONTHLY_PRODUCT_T, 1)])
    production = []
    for (m, lo, hi), t in zip(month_use, MONTHLY_PRODUCT_T):
        production.append({"month": f"{YEAR}-{m:02d}", "tonnes": t, "cn_code": CN_CODES[(m - 1) % 2],
                           "heats": overlapping(lot_iv, lo, hi)})

    fuel = [{"invoice_no": f"GI-{m:02d}", "month": f"{YEAR}-{m:02d}", "fuel": "natural gas",
             "quantity": round(GAS_GJ_PER_T * t, 3), "unit": "GJ",
             "emission_factor_t_per_tj": GAS_EF_T_PER_TJ}
            for m, t in enumerate(MONTHLY_PRODUCT_T, 1)]

    month_made = cumulative([(m, t) for m, t in enumerate(MONTHLY_PRODUCT_T, 1)])
    shipments = []
    for i, (n, lo, hi) in enumerate(cumulative(list(enumerate(SHIPMENT_T, 1)))):
        months = overlapping(month_made, lo, hi)
        shipments.append({"invoice_no": f"EX-{n:02d}",
                          "date": f"{YEAR}-{months[-1]:02d}-{rng.randint(20, 28)}",
                          "destination": DESTINATIONS[i % 4], "cn_code": CN_CODES[i % 2],
                          "tonnes": SHIPMENT_T[i],
                          "production_months": [f"{YEAR}-{m:02d}" for m in months]})

    gt = {
        "folder": folder, "factory": FACTORY, "reporting_year": YEAR, "cn_codes": CN_CODES,
        "purchases": purchases, "delivery_notes": delivery_notes, "certificates": certificates,
        "verification_reports": [{"report_no": "VR-A", "mill": MILL_A, "period_year": YEAR,
                                  "precursor_see": EXAMPLE_SEE, "label": EXAMPLE_LABEL}],
        "production": production, "stock": stock,
        "scrap": {"tonnes": SCRAP_T, "pre_consumer_share": 1.0, "sources": "cutting and forging"},
        "fuel": fuel, "shipments": shipments, "planted_issues": [], "documents": [],
    }
    if folder == "problem":
        plant_issues(gt, rng)
    return gt


def plant_issues(gt: dict, rng: random.Random) -> None:
    """The five planted issues of the problem folder. Nothing else changes."""
    gt["scrap"]["tonnes"] = 15                                   # MASS_BALANCE
    gt["certificates"].append({"cert_no": "MC-X9", "heat": "X9", "mill": MILL_A, "grade": GRADE,
                               "tonnes": 40, "production_date": f"{YEAR}-05-02",
                               "chemistry": chemistry(rng), "layout": "down"})  # CERT_NO_PURCHASE
    gt["verification_reports"][0]["period_year"] = YEAR - 1      # PRECURSOR_EVIDENCE
    gt["fuel"][7]["unit"] = "kg"                                 # FUEL_UNIT (August)
    a2 = next(c for c in gt["certificates"] if c["heat"] == "A2")["chemistry"]
    a2["Mn"], a2["Cr"] = 0.02, 0.85                              # CHEMISTRY_RANGE
    gt["planted_issues"] = list(PLANTED)


def expected_results(gt: dict) -> dict:
    """Expected flags and precursor statuses, worked out from the ground truth."""
    years = {c["heat"]: int(c["production_date"][:4]) for c in gt["certificates"]}
    report_years = {}
    for r in gt["verification_reports"]:
        report_years.setdefault(r["mill"], set()).add(r["period_year"])
    mill_of = {c["heat"]: c["mill"] for c in gt["certificates"]}
    closing = {r["heat"]: r["tonnes"] for r in gt["stock"]["closing"]}
    statuses = {}
    lots = [r["heat"] for r in gt["stock"]["opening"]] + [p["heat"] for p in gt["purchases"]]
    for heat in lots:
        mill = mill_of[heat]
        if years[heat] in report_years.get(mill, set()):
            statuses[heat] = "ACTUAL_ALLOWED"
        elif mill in report_years:
            statuses[heat] = "DEFAULT_REPORT_PERIOD"
        else:
            statuses[heat] = "DEFAULT_NO_EMISSIONS_DATA"
    consumed = {h: t - closing.get(h, 0) for h, t in
                [(r["heat"], r["tonnes"]) for r in gt["stock"]["opening"]] +
                [(p["heat"], p["tonnes"]) for p in gt["purchases"]]}
    return {"flags": sorted(gt["planted_issues"]), "statuses": statuses, "consumed_t": consumed}


# ---------------------------------------------------------------- stage 2

def document_specs(gt: dict) -> list:
    """Every document: file name, type, title, and the fields it shows (key, label, unit)."""
    docs = []

    def add(file, kind, title, fields, **extra):
        docs.append({"file": file, "type": kind, "title": title, "fields": fields, **extra})

    for i, p in enumerate(gt["purchases"]):
        k = f"purchases[{i}]"
        fields = [(f"{k}.invoice_no", "Invoice no", None), (f"{k}.supplier", "Supplier", None),
                  (f"{k}.supplier_type", "Supplier type", None), (f"{k}.heat", "Heat no", None),
                  (f"{k}.tonnes", "Quantity", "t"), (f"{k}.date", "Date", None)]
        if p["emissions_claim"]:
            fields.append((f"{k}.emissions_claim", "Embedded emissions data", None))
        add(f"{p['invoice_no']}.pdf", "purchase_invoice", f"Purchase invoice {p['invoice_no']}", fields)

    for i, n in enumerate(gt["delivery_notes"]):
        k = f"delivery_notes[{i}]"
        add(f"{n['note_no']}.pdf", "delivery_note", f"Delivery note {n['note_no']}",
            [(f"{k}.note_no", "Note no", None), (f"{k}.supplier", "Supplier", None),
             (f"{k}.mill", "Producing mill", None), (f"{k}.heats", "Heat numbers", None)])

    for i, c in enumerate(gt["certificates"]):
        k = f"certificates[{i}]"
        fields = [(f"{k}.cert_no", "Certificate no", None), (f"{k}.mill", "Mill", None),
                  (f"{k}.heat", "Heat no", None), (f"{k}.grade", "Grade", None),
                  (f"{k}.tonnes", "Mass", "t"), (f"{k}.production_date", "Production date", None)]
        fields += [(f"{k}.chemistry.{el}", el, "%") for el in ["C", "Mn", "Si", "Cr", "Ni", "other"]]
        add(f"{c['cert_no']}.pdf", "mill_certificate", f"Mill test certificate {c['cert_no']}",
            fields, layout=c["layout"])

    for i, r in enumerate(gt["verification_reports"]):
        k = f"verification_reports[{i}]"
        add(f"{r['report_no']}.pdf", "verification_report", f"Verification report {r['report_no']}",
            [(f"{k}.report_no", "Report no", None), (f"{k}.mill", "Installation", None),
             (f"{k}.period_year", "Period covered (calendar year)", None),
             (f"{k}.precursor_see", "Specific direct embedded emissions", "t CO2/t"),
             (f"{k}.label", "Note", None)])

    rows = []
    for i in range(len(gt["production"])):
        k = f"production[{i}]"
        rows += [(f"{k}.month", "Month", None), (f"{k}.tonnes", "Product made", "t"),
                 (f"{k}.cn_code", "CN code", None), (f"{k}.heats", "Heats used", None)]
    add("production_register.pdf", "production_register", "Production register",
        [("factory", "Factory", None)] + rows, table="production")

    add("scrap_register.pdf", "scrap_register", "Scrap register",
        [("scrap.tonnes", "Scrap produced", "t"),
         ("scrap.pre_consumer_share", "Pre-consumer share", "fraction"),
         ("scrap.sources", "Scrap from", None)])

    fields = []
    for side in ["opening", "closing"]:
        for i in range(len(gt["stock"][side])):
            k = f"stock.{side}[{i}]"
            fields += [(f"{k}.heat", f"{side.title()} stock heat", None),
                       (f"{k}.tonnes", f"{side.title()} stock", "t"),
                       (f"{k}.mill", f"{side.title()} stock mill", None)]
    fields.append(("stock.count_note", "Handwritten note", None))
    add("stock_register.pdf", "stock_register", "Steel stock register", fields,
        confidence={"stock.count_note": LOW_CONFIDENCE["handwritten"]})

    for i, f in enumerate(gt["fuel"]):
        k = f"fuel[{i}]"
        fields = [(f"{k}.invoice_no", "Invoice no", None), (f"{k}.month", "Billing month", None),
                  (f"{k}.fuel", "Fuel", None), (f"{k}.quantity", "Quantity", None),
                  (f"{k}.unit", "Unit", None),
                  (f"{k}.emission_factor_t_per_tj", "Emission factor (footer)", "t CO2/TJ")]
        if i + 1 == GAS_PHOTO_MONTH:
            add(f"{f['invoice_no']}.jpg", "gas_invoice", f"Gas invoice {f['invoice_no']}", fields,
                confidence={key: LOW_CONFIDENCE["photo"] for key, _, _ in fields})
        else:
            add(f"{f['invoice_no']}.pdf", "gas_invoice", f"Gas invoice {f['invoice_no']}", fields,
                footer=EF_NOTE)

    for i, s in enumerate(gt["shipments"]):
        k = f"shipments[{i}]"
        fields = [(f"{k}.invoice_no", "Invoice no", None), (f"{k}.date", "Date", None),
                  (f"{k}.destination", "Destination", None), (f"{k}.cn_code", "CN code", None),
                  (f"{k}.tonnes", "Net mass", "t"), (f"{k}.production_months", "Packed from", None)]
        if i + 1 == STAMPED_SHIPMENT:
            add(f"{s['invoice_no']}.jpg", "export_invoice", f"Export invoice {s['invoice_no']}", fields,
                stamp=f"{k}.tonnes", confidence={f"{k}.tonnes": LOW_CONFIDENCE["stamp"]})
        else:
            add(f"{s['invoice_no']}.pdf", "export_invoice", f"Export invoice {s['invoice_no']}", fields)
    return docs


def fmt(value, unit=None) -> str:
    if value is None:
        text = ""
    elif isinstance(value, list):
        text = ", ".join(str(v) for v in value)
    elif isinstance(value, float):
        text = f"{value:g}"
    else:
        text = str(value)
    return f"{text} {unit}" if unit and unit != "fraction" else text


def draw_pdf(path: Path, doc: dict, gt: dict) -> None:
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=0, invariant=1)
    w, h = A4
    c.saveState()
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFont("Helvetica-Bold", 80)
    c.translate(w / 2, h / 2)
    c.rotate(40)
    c.drawCentredString(0, 0, "SYNTHETIC")
    c.restoreState()

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h - 60, doc["title"])
    c.setFont("Helvetica", 9)
    c.drawString(50, h - 76, f"SYNTHETIC DOCUMENT. {FACTORY} is fictional. Made for a software demo.")
    c.setFont("Helvetica", 10)
    values = [(label, fmt(get_path(gt, key), unit)) for key, label, unit in doc["fields"]]
    y = h - 110

    if doc.get("table") == "production":
        c.drawString(50, y, f"Factory: {values[0][1]}")
        y -= 24
        c.setFont("Helvetica-Bold", 10)
        for x, head in zip([50, 130, 230, 320], ["Month", "Product made", "CN code", "Heats used"]):
            c.drawString(x, y, head)
        c.setFont("Helvetica", 10)
        rows = values[1:]
        for r in range(0, len(rows), 4):
            y -= 16
            for x, (_, text) in zip([50, 130, 230, 320], rows[r:r + 4]):
                c.drawString(x, y, text)
    elif doc["type"] == "mill_certificate":
        head, chem = values[:6], values[6:]
        layout = doc["layout"]
        for label, text in head:
            c.drawString(50, y, f"{label}: {text}")
            y -= 16
        if layout == "across":
            y -= 10
            c.drawString(50, y, "Chemical analysis (% by mass)")
            for j, (label, text) in enumerate(chem):
                c.drawString(50 + j * 75, y - 18, label)
                c.drawString(50 + j * 75, y - 34, text)
        elif layout == "down":
            y -= 10
            c.drawString(50, y, "Chemical analysis")
            for label, text in chem:
                y -= 16
                c.drawString(70, y, f"{label:6s} {text}")
        else:
            yy = h - 110
            c.drawString(330, yy, "Chemistry, % by mass")
            for label, text in chem:
                yy -= 16
                c.drawString(330, yy, f"{label}: {text}")
    else:
        for label, text in values:
            if doc["file"] == "stock_register.pdf" and label == "Handwritten note":
                continue
            c.drawString(50, y, f"{label}: {text}")
            y -= 16

    if doc["file"] == "stock_register.pdf":
        c.saveState()
        c.setFillColorRGB(0.1, 0.2, 0.6)
        c.setFont("Times-Italic", 14)
        c.translate(80, y - 40)
        c.rotate(6)
        c.drawString(0, 0, get_path(gt, "stock.count_note"))
        c.restoreState()
    if doc.get("footer"):
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(50, 50, doc["footer"])
    c.setFont("Helvetica", 8)
    c.drawString(50, 36, "SYNTHETIC - not a real company, invoice or certificate.")
    c.showPage()
    c.save()


def draw_jpg(path: Path, doc: dict, gt: dict, rng: random.Random) -> None:
    img = Image.new("RGB", (900, 900), "white")
    d = ImageDraw.Draw(img)
    big = ImageFont.load_default(size=30)
    font = ImageFont.load_default(size=24)
    d.text((40, 30), doc["title"], fill="black", font=big)
    d.text((40, 80), "SYNTHETIC DOCUMENT - fictional company", fill=(160, 0, 0), font=font)
    y, stamp_at = 150, None
    for key, label, unit in doc["fields"]:
        d.text((40, y), f"{label}: {fmt(get_path(gt, key), unit)}", fill="black", font=font)
        if key == doc.get("stamp"):
            stamp_at = (40 + d.textlength(f"{label}: ", font=font), y)
        y += 45
    d.text((40, y + 40), EF_NOTE if doc["type"] == "gas_invoice" else "", fill="black",
           font=ImageFont.load_default(size=16))
    d.text((260, 760), "SYNTHETIC", fill=(200, 200, 200), font=ImageFont.load_default(size=70))
    if stamp_at:
        x, sy = stamp_at
        d.ellipse([x - 40, sy - 60, x + 120, sy + 100], outline=(200, 0, 0), width=7)
        d.text((x - 20, sy + 8), "RECEIVED", fill=(200, 0, 0), font=font)
    img = img.rotate(rng.uniform(2, 4), expand=True, fillcolor="white")
    px = img.load()
    for _ in range(6000):
        g = rng.randint(90, 210)
        px[rng.randrange(img.width), rng.randrange(img.height)] = (g, g, g)
    img.save(path, quality=85)


def cached_fields(docs: list, gt: dict, rng: random.Random, threshold: float) -> list:
    out = []
    for doc in docs:
        low = doc.get("confidence", {})
        for key, label, unit in doc["fields"]:
            conf = low.get(key, round(rng.uniform(0.95, 0.99), 2))
            out.append({"key": key, "doc": doc["file"], "label": label, "value": get_path(gt, key),
                        "unit": unit, "source_file": doc["file"], "page": 1, "mode": "CACHED",
                        "confidence": conf, "needs_review": conf < threshold,
                        "reviewer": None, "reviewed_at": None})
    return out


def make_folder(folder: str, out_root: Path) -> dict:
    gt = build_ground_truth(folder)
    docs = document_specs(gt)
    gt["documents"] = [d["file"] for d in docs]
    GroundTruth.model_validate(gt)
    out = out_root / folder
    (out / "docs").mkdir(parents=True, exist_ok=True)
    write_json(out / "ground_truth.json", gt)
    write_json(out / "expected_results.json", expected_results(gt))

    rng = random.Random(SEED)
    for doc in docs:
        path = out / "docs" / doc["file"]
        if path.suffix == ".pdf":
            draw_pdf(path, doc, gt)
        else:
            draw_jpg(path, doc, gt, rng)
    threshold = load_config()["review_confidence_threshold"]
    write_json(out / "cached_fields.json", {
        "note": "CACHED extraction results generated from the synthetic ground truth.",
        "documents": [{"file": d["file"], "type": d["type"], "title": d["title"]} for d in docs],
        "fields": cached_fields(docs, gt, rng, threshold),
    })
    return gt


def main() -> None:
    for folder in FOLDERS:
        gt = make_folder(folder, ROOT / "data")
        print(f"{folder}: {len(gt['documents'])} documents, planted issues: {gt['planted_issues'] or 'none'}")


if __name__ == "__main__":
    main()
