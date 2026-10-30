"""Shared look of the TraceCheck screens: small functions that return HTML strings.

Nothing here calculates a result. Every number is passed in by app.py from the
tracecheck functions. Styling lives in static/style.css.
"""

import base64
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo_mark.svg"
LOGO_DARK = ROOT / "assets" / "logo_mark_dark_bg.svg"

# st.html strips inline <svg>, so drawings go in as data-URI images
CHECK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" '
             'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>')

# status in code -> (css class, icon, one-line meaning), DESIGN_PLAN.md section 7
VERDICT = {
    "ACTUAL_ALLOWED": ("ready", "✓", "The mill's verified report covers this year. Its real figures can be used."),
    "DEFAULT_REPORT_PERIOD": ("action", "⏱", "The mill's report covers another year. EU default applies until it arrives."),
    "DEFAULT_NO_EMISSIONS_DATA": ("neutral", "○", "We know the mill, but it has not shared verified emissions. EU default applies."),
    "NO_MILL_LINK": ("problem", "✕", "This steel cannot be linked to a mill yet."),
}

WORDS = {
    "precursor": "The steel rod that goes into the screws and nuts.",
    "heat number": "The number a mill gives one batch of steel, printed on its certificate.",
    "default value": "The standard figure that applies when actual mill data cannot be used.",
    "verification report": "A report from an accredited verifier covering the period the steel was produced.",
}


def css() -> str:
    return "<style>" + (ROOT / "static" / "style.css").read_text(encoding="utf-8") + "</style>"


def svg_img(svg: str, size: int, alt: str = "") -> str:
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="{uri}" width="{size}" height="{size}" alt="{escape(alt)}">'


def check_mark(size: int) -> str:
    return svg_img(CHECK_SVG, size, "check")


def logo_uri(path: Path = LOGO) -> str:
    svg = re.sub(r"<metadata>.*?</metadata>", "", path.read_text(encoding="utf-8"), flags=re.S)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def brand() -> str:
    return f'<div class="brand"><img src="{logo_uri()}" alt="TraceCheck"></div>'


def num(value) -> str:
    """Whole numbers without '.0'."""
    return f"{value:g}" if isinstance(value, float) else str(value)


def tonnes(value) -> str:
    return f'{num(value)}<span class="t">&nbsp;t</span>'


def head(eyebrow: str, title: str, lede: str = "", side: str = "") -> str:
    text = (f'<div><div class="eyebrow">{escape(eyebrow)}</div><h1 class="title">{escape(title)}</h1>'
            + (f'<div class="lede">{escape(lede)}</div>' if lede else "") + "</div>")
    return f'<div class="head{" split" if side else ""}">{text}{side}</div>'


def chip(mode) -> str:
    return f'<span class="chip {escape(str(mode))}">{escape(str(mode))}</span>'


def evidence_segments(bars: list) -> str:
    return "".join(f'<i class="{b["css"]}" style="flex:{b["t"]} 1 0" title="{escape(b["name"])}"></i>' for b in bars)


def hero(share: int, total, year, bars: list, mode: str) -> str:
    keys = "".join(f'<div class="k"><b>{tonnes(b["t"])}</b><small><span class="dot {b["css"]}"></span>'
                   f'{escape(b["name"])}</small></div>' for b in bars)
    return (f'<div class="hero"><div class="hero-top"><div class="hero-num">{share}<span>%</span></div>'
            f'<div><div class="hero-say">of this factory\'s steel can use<br>verified mill data.</div>'
            f'<div class="hero-sub">{num(total)} t of steel used in {year} · traced lot by lot</div></div></div>'
            f'<div class="bar">{evidence_segments(bars)}</div>'
            f'<div class="barkeys">{keys}<div class="note">Illustrative, for evidence preparation<br>'
            f'Extraction mode: {escape(mode)}</div></div></div>')


def tile(label: str, number, unit: str, line: str, tone: str, alert: bool = False) -> str:
    unit_html = f'<span class="unitword">{escape(unit)}</span>' if unit else ""
    return (f'<div class="card tile"><div class="label">{escape(label)}</div>'
            f'<div class="num{" alert" if alert else ""}">{num(number)}{unit_html}</div>'
            f'<div class="line"><span class="dot {tone}"></span>{escape(line)}</div></div>')


def tiles(items: list) -> str:
    return '<div class="tiles">' + "".join(items) + "</div>"


def ring(done: int, total: int, index: int) -> str:
    """The stage circle: filled when complete, a partial ring otherwise."""
    if done >= total:
        return f'<span class="ring full">{check_mark(22)}</span>'
    r, length = 19, 2 * 3.14159 * 19
    part = length * (done / total if total else 0)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44">'
           f'<circle cx="22" cy="22" r="{r}" fill="none" stroke="#E4DED2" stroke-width="4"/>'
           + (f'<circle cx="22" cy="22" r="{r}" fill="none" stroke="#FF6D1F" stroke-width="4" stroke-linecap="round" '
              f'stroke-dasharray="{part:.1f} {length:.1f}" transform="rotate(-90 22 22)"/>' if done else "")
           + "</svg>")
    return f'<span class="ring">{svg_img(svg, 44, f"{done} of {total}")}<em>{index}</em></span>'


def path_title(count: int) -> str:
    words = ["No", "One", "Two", "Three", "Four", "All"]
    return f"{words[count]} of five stages complete" if count < 5 else "All five stages complete"


def path_head(count: int) -> str:
    return f'<div class="label">Path to evidence pack</div><div class="pathtitle">{path_title(count)}</div>'


def path_track(stages: list) -> str:
    """stages: list of dicts with name, done, total, text."""
    out = []
    for i, s in enumerate(stages, 1):
        complete = s["done"] >= s["total"]
        out.append(f'<div class="stage{" done" if complete else ""}">{ring(s["done"], s["total"], i)}'
                   f'<b>{escape(s["name"])}</b><small>{escape(s["text"])}</small></div>')
    return '<div class="track">' + "".join(out) + "</div>"


def footline(text: str) -> str:
    return f'<div class="footline">{escape(text)}</div>'


def synth_pill() -> str:
    return '<span class="synth">SYNTHETIC · Draft for verifier review</span>'


def readiness(share: int, ready, total, bars: list) -> str:
    return (f'<div class="card ready-card"><div class="row"><span class="num">{share}<span class="pct">%</span></span>'
            f'<span class="txt">ready · {num(ready)} of {num(total)} t</span></div>'
            f'<div class="bar thin">{evidence_segments(bars)}</div></div>')


def glossary() -> str:
    items = "".join(f'<span class="tip" data-tip="{escape(meaning)}">{escape(word)}</span>'
                    for word, meaning in WORDS.items())
    return f'<div class="glossary"><span>Hover for meaning:</span>{items}</div>'


def verdict_head(css_name: str, icon: str, name: str, meaning: str, total_line: str) -> str:
    return (f'<div class="vhead {css_name}"><div class="top"><span class="ico">{icon}</span>{escape(name)}</div>'
            f'<p>{escape(meaning)}</p><div class="tot">{escape(total_line)}</div></div>')


def empty_card(line: str, hint: str = "") -> str:
    return f'<div class="empty">{escape(line)}' + (f"<small>{escape(hint)}</small>" if hint else "") + "</div>"


def lot_card(css_name: str, heat: str, t, mill: str, sub: str, mode, step: str, full_step: str) -> str:
    return (f'<div class="lot"><div class="lot-top"><span class="heat"><span class="dot {css_name}"></span>{escape(str(heat))}</span>'
            f'<span class="num">{tonnes(t if t is not None else "?")}</span></div>'
            f'<div class="lot-mill"><span>{escape(mill)}</span>{chip(mode)}</div>'
            f'<div class="lot-sub">{escape(sub)}</div><hr class="rule">'
            f'<div class="label">Next step</div><div class="lot-next" title="{escape(full_step)}">{escape(step)}</div></div>')


def review_card(done: int, total: int) -> str:
    return (f'<div class="card ready-card"><div class="row"><span class="num">{done}</span>'
            f'<span class="txt">of {total} documents approved</span></div></div>')


def doc_legend(need: int) -> str:
    return (f'<div class="doclegend"><span class="label">Documents</span>'
            f'<span class="small"><b>!</b> {need} need a check · <b>✓</b> approved</span></div>')


def small_tip(text: str) -> str:
    return f'<div class="small tipline">{escape(text)}</div>'


def lot_row(css_name: str, heat: str, t, mode, full_step: str) -> str:
    """One-line form of a lot card, for columns with many lots."""
    return (f'<div class="lotrow" title="{escape(full_step)}"><span class="heat"><span class="dot {css_name}"></span>'
            f'{escape(str(heat))}</span>{chip(mode)}<span class="num">{tonnes(t if t is not None else "?")}</span></div>')


def window(file_name: str, mode: str, image_uri: str, scanning: bool = False) -> str:
    scan = ('<div class="scan"></div><div class="reading">Gemini is reading…</div>' if scanning else "")
    return (f'<div class="window"><div class="winbar"><i class="a"></i><i class="b"></i><i class="c"></i>'
            f'<span class="name">{escape(file_name)}</span>{chip(mode)}</div>'
            f'<div class="page"><img src="{image_uri}" alt="{escape(file_name)}, SYNTHETIC">{scan}</div></div>')


def field_row(label: str, value: str, mode: str, confidence: float, check: bool = False) -> str:
    pct = round(confidence * 100)
    return (f'<div class="fld{" check" if check else ""}"><span class="l">{escape(label)}</span>'
            f'<span class="v">{escape(value)}</span>{chip(mode)}'
            f'<div><div class="conf-t">{pct}%</div><div class="conf{" low" if check else ""}"><i style="width:{pct}%"></i></div></div></div>')


def flag_top(severity: str, status: str, flag_id: str) -> str:
    mark = {"high": "▲", "medium": "◆", "low": "●"}[severity]
    return (f'<div class="sev {severity}"><span>{mark} {escape(severity)}</span>'
            f'<span>· {escape(status)}</span><span class="chip">{escape(flag_id)}</span></div>')


def flag_message(text: str) -> str:
    return f'<div class="flagmsg">{escape(text)}</div>'


def calm(title: str, items: list) -> str:
    rows = "".join(f"<li>✓ {escape(i)}</li>" for i in items)
    return (f'<div class="card calm"><div class="tick">{check_mark(56)}</div>'
            f"<h2>{escape(title)}</h2><ul>{rows}</ul></div>")


def proof_card(title: str, rows: list, notes: str) -> str:
    boxes = []
    for r in rows:
        ok = r["match"]
        boxes.append(f'<div class="pf"><div class="label">{escape(r["label"])}</div><div class="vs">'
                     f'<div><div class="num">{r["ours"]:.3f}</div><div class="who">Ours</div></div>'
                     f'<div><div class="num">{r["theirs"]:.3f}</div><div class="who">The Commission\'s</div></div>'
                     f'<div class="ok{"" if ok else " no"}">{check_mark(24) if ok else "✕"}</div></div></div>')
    return (f'<div class="card proof"><h2>{escape(title)}</h2><div class="proofs">{"".join(boxes)}</div>'
            f'<p class="small" style="margin:12px 0 0">{escape(notes)}</p></div>')


def section(title: str) -> str:
    return f'<h2 class="cardtitle sect">{escape(title)}</h2>'


def result_card(value, mode: str, steps: str) -> str:
    return (f'<div class="card result"><div class="label">Illustrative, for evidence preparation</div>'
            f'<div class="num">{num(value)}<span class="t">&nbsp;t CO2 per t of product</span></div>'
            f'<div class="small" style="margin:8px 0 16px">Extraction mode: {escape(mode)}</div>{steps}</div>')


def missing_card(items: list) -> str:
    rows = "".join(f"<li>{escape(i)}</li>" for i in items)
    return (f'<div class="card missing"><div class="cardtitle">Input missing</div>'
            f'<ul class="miss">{rows}</ul><div class="small">No total until these are in. '
            f"Illustrative, for evidence preparation.</div></div>")


def lot_values(rows: str) -> str:
    return f'<div class="card flat"><div class="label">Value used per lot</div>{rows}</div>'


def formula_card() -> str:
    terms = [("SEE", "specific embedded emissions, t CO2 per t of product"),
             ("own direct", "the factory's own direct emissions per tonne of product"),
             ("mi", "tonnes of precursor consumed divided by tonnes of product made"),
             ("precursor SEE", "from the mill's verification report, or the default value")]
    rows = "".join(f'<div><span class="mono">{t}</span> · {m}</div>' for t, m in terms)
    return (f'<div class="card flat"><div class="label">The formula</div>'
            f'<div class="formula">SEE = own direct + sum of (mi × precursor SEE)</div>'
            f'<div class="small terms">{rows}</div></div>')


def table(columns: list, rows: list, mono: tuple = ()) -> str:
    """rows hold HTML-safe strings; mono: column indexes in the data font."""
    head_row = "".join(f"<th>{escape(c)}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f'<td{" class=m" if i in mono else ""}>{cell}</td>' for i, cell in enumerate(r)) + "</tr>"
                   for r in rows)
    return f'<table class="rows"><thead><tr>{head_row}</tr></thead><tbody>{body}</tbody></table>'


def sheet_list(items: list) -> str:
    """items: (sheet name, missing count)."""
    rows = "".join(f'<li class="{"gap" if miss else ""}"><span class="mk">{"!" if miss else "✓"}</span>{escape(name)}'
                   f'<small>{f"{miss} missing" if miss else "ready"}</small></li>' for name, miss in items)
    return f'<ul class="sheets">{rows}</ul>'
