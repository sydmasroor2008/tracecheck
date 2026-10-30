# DESIGN PLAN: TraceCheck interface redesign (Step 14)

Do this after Step 13 is done and all tests pass. It changes **how the app looks and reads, not what it
calculates**. Same working rules: test, commit after each part, log in PROGRESS.md.

## 0. Hard limits

- Do not change anything in `tracecheck/`, `tools/`, `data/` or `tests/` except `tests/test_app_smoke.py`
  (update it if page function names change). All existing tests must still pass.
- Every number on screen comes from the existing functions. Never type a result into the UI.
- Keep, on every page: the word SYNTHETIC, "Draft prepared for verifier review", "Illustrative, for
  evidence preparation" on calculated values, and the extraction mode (MANUAL / CACHED / LIVE) next to values.
- Must work fully offline. No fonts, icons or scripts loaded from the internet at run time.
- Stay in Streamlit. No React, no new web framework. Use `.streamlit/config.toml`, one CSS file, and HTML
  blocks rendered with `st.html` or `st.markdown(..., unsafe_allow_html=True)`. Check the installed
  Streamlit version first and use only features it has.

## 1. The problem we are fixing

A first-time viewer did not know what to click first, did not understand the verdicts, saw too much text,
and could not read the numbers. A judge looks at each screen for about 10 seconds on a projector.

So every screen must answer one question in one glance:

| Screen | The one question it answers |
|---|---|
| Overview | How ready is this factory's CBAM evidence? |
| 1 Read | What did the AI read, and what needs a human check? |
| 2 Trace | Which steel can use real data, and what is missing for the rest? |
| 3 Check | What is wrong, and where is it in the papers? |
| 4 Calculate | Is the formula right? (proof), and what is still missing? |
| 5 Export | Download the pack for the verifier. |

## 2. Design direction: "Evidence on paper"

One direction, not ten. Editorial + Swiss grid + bento cards + minimal, on a warm paper background.

- **Editorial / bold:** very large, heavy sans-serif headlines and numbers (Montserrat), like a bold studio site. Few words, big.
- **Swiss:** strict 12-column grid, left-aligned, lots of white space, one accent colour per screen.
- **Bento:** the Overview is a grid of rounded tiles of different sizes.
- **Paper:** a faint paper-grain texture on the background; documents shown as sheets of paper.
- **One technical touch (a light nod to cybercore):** heat numbers, file names and IDs in a monospace font,
  and a thin scanning line animation over a document while the AI reads it. Nothing else neon, glitchy or Y2K.
- The other styles (surrealism, Y2K, bohemian, ethereal, sketch) are left out on purpose: mixing them makes a
  compliance tool look unserious.

Mood words: calm, confident, mature, expensive, quiet.

## 3. Colour tokens

Light theme only (projectors wash out dark themes). Taken from the team's palettes.

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#F4F1EB` | page background (Alabaster) |
| `--sheet` | `#FFFDF8` | cards, document sheets |
| `--line` | `#E4DED2` | 1 px borders, dividers |
| `--ink` | `#222222` | headlines, numbers (Black Hole) |
| `--ink-2` | `#5F5B52` | secondary text |
| `--brand` | `#0D4C3C` | logo, primary buttons, active step (Dark Emerald) |
| `--ready` | `#2D5A4A` text on `#7AA05A` at 18% tint | verdict "Ready" (Slate Green / Moss) |
| `--action` | `#FF6D1F` | verdict "Needs this year's report", primary "do this next" highlights (Electric Tangerine). Use sparingly. |
| `--neutral` | `#898861` | verdict "No mill data" (Leaf) |
| `--problem` | `#7D2826` | issues/flags, verdict "Untraced" (Coral) |
| `--deep` | `#343723` | dark tile background for the one hero tile (Juniper) |

Rules: one accent per screen besides the verdict colours. Never use colour alone for meaning: every
coloured item also has a word and an icon. Text contrast at least 4.5:1 (check `--ink-2` on `--paper`).

## 4. Type

Bold, OS-style headlines and numbers (approved in the Figma mockup). Bundle the font files in `static/fonts/`
(download once during this step; all three are open-licence Google Fonts). Set
`server.enableStaticServing = true` in `.streamlit/config.toml` and load them with `@font-face` from
`app/static/fonts/...`. If download fails, fall back to Arial Black / system-ui / Consolas and say so.

| Role | Font | Size (projector) | Weight | Letter-spacing |
|---|---|---|---|---|
| Hero number (e.g. 60%) | Montserrat | 104 px | ExtraBold 800 | -4% |
| KPI numbers | Montserrat | 60 px | ExtraBold 800 | -3% |
| Screen titles | Montserrat | 52 px | Bold 700 | -2.5% |
| Hero sentence, card titles | Montserrat | 26–32 px | Bold 700 | -1.5% |
| Tonnes on lot cards | Montserrat | 26 px | ExtraBold 800 | -1% |
| Unit words after numbers ("lots", "inputs") | Montserrat | 20–22 px | SemiBold 600 | 0 |
| Body | Inter | 18 px (never below 14) | 400 | 0 |
| Label: small caps above numbers | Inter | 13 px, uppercase | 600 | +8% |
| Data: heat numbers, IDs, file names, counts | JetBrains Mono | 12–24 px | 500 | 0 |

**Coloured units:** in big numbers, the unit is a different colour from the digits, like "96%" in the
reference: "%" in Electric Tangerine `#FF6D1F` on light backgrounds and Moss `#7AA05A` on the dark hero tile;
"t" (tonnes) in a muted grey `#8A857A` on light backgrounds and Moss on the dark tile.

Numbers people must read are big: KPI numbers at least 56 px. Use tabular figures for numbers in tables.

## 5. Layout and spacing

- Max content width 1280 px, centred, 48 px side padding; 8 px spacing grid (8, 16, 24, 32, 48, 64).
- Cards: `--sheet`, 1 px `--line` border, radius 20 px, soft shadow `0 1px 2px rgba(34,34,34,.04), 0 8px 24px rgba(34,34,34,.05)`.
- Paper grain: an inline SVG noise filter (data URI) over the page background at about 4% opacity. No image files.
- Hide Streamlit's default header, footer, deploy button and hamburger menu. Remove default top padding.
- Design for 1366×768 (typical venue projector) first, check at 1920×1080.

## 6. Navigation: a numbered path, not a menu

Replace the sidebar radio with a **horizontal top bar**:

`[logo mark + TRACE CHECK AI]   Overview · 1 Read · 2 Trace · 3 Check · 4 Calculate · 5 Export   [Scenario ▾]`

- Steps are shown as a progress path: a small numbered circle per step, a thin line between them, the
  current step filled `--brand`, finished steps with a check mark. This tells a newcomer where to start.
- Rename the folder selector to **Scenario** with friendly names: "Clean factory", "Factory with problems",
  "Trader supply chain". Default: Clean factory.
- Every screen ends with one primary button to the next step ("Next: Trace the steel →").
- Keep the sidebar collapsed or remove it; use `st.navigation(position="top")` if the installed version
  supports it, else a row of buttons with `st.session_state`.
- SYNTHETIC: a small, calm pill in the top bar ("SYNTHETIC DATA · Draft for verifier review"), not a big yellow
  warning box.

## 7. Screen by screen

### Overview (the first thing judges see)

Bento grid, 3 rows:

1. **Hero tile (full width, `--deep` background, light text):** one sentence in bold Montserrat, computed from data:
   "**{x} %** of this factory's steel can use verified mill data." Under it, the **Evidence bar** (section 8).
2. **Four tiles in a row**, each one big number, one label, one line:
   - Documents read — "{n} documents · {k} need a human check"
   - Steel traced — "{lots} lots to {mills} mills"
   - Issues — "{flags} open" (coloured `--problem` if above 0, else "All clear" in `--ready`)
   - Evidence pack — "Ready to export" / "{m} items missing"
3. **Path to evidence pack (wide tile):** the 5-stage progress tracker (section 8), and a button
   "Start: 1 Read the documents →".

No paragraphs on this page. Maximum 12 words in any line.

### 1 Read (documents and AI review)

- Left (5 columns): document list as small paper "thumbnails" with type icon, file name in mono, and a status
  dot (approved / needs check).
- Right (7 columns): the selected document as a **sheet of paper inside a minimal window frame** (three small
  dots top left in `--problem`, `--action`, `--ready` tints, file name in the bar). Below it, the extracted
  fields as clean rows: label, value (large), mode chip (MANUAL/CACHED/LIVE), confidence as a thin bar.
  Fields needing review get a `--action` left border and an "Approve" button.
- "Read with AI" button: while waiting, show the scanning line over the sheet and "Gemini is reading…".
- One line at the top in `--ink-2`: "AI reads · code calculates · a person approves".

### 2 Trace (the star screen)

- Title: "Can this steel use real data?"
- **Verdict legend** at the top, always visible, four cards with icon, short name and one-line meaning:

| Status in code | Badge text | Icon | Meaning (one line) | Colour |
|---|---|---|---|---|
| ACTUAL_ALLOWED | Ready | ✓ | The mill's verified report covers this year. Its real figures can be used. | `--ready` |
| DEFAULT_REPORT_PERIOD | Needs {year} report | ⏱ | The mill's report covers another year. EU default applies until it arrives. | `--action` |
| DEFAULT_NO_EMISSIONS_DATA | No mill data | ○ | We know the mill, but it has not shared verified emissions. EU default applies. | `--neutral` |
| NO_MILL_LINK | Untraced | ✕ | This steel cannot be linked to a mill yet. | `--problem` |

- **Layout (approved in the Figma mockup): four verdict columns side by side**, in the order Ready, Needs
  {year} report, No mill data, Untraced. Each column starts with a tinted header card (icon in a white circle,
  verdict name, the one-line meaning, then "{n} lots · {t} t" in mono), and the lot cards for that verdict
  stack under it. A column with no lots shows a dashed empty card: "None in this scenario".
- **Lot card:** coloured dot + heat number (mono, 24 px), tonnes (Montserrat ExtraBold, 26 px) on the right, mill name, a small
  line such as "Made 2025 · opening stock" or "via Example Steel Traders", a divider, "NEXT STEP" label, the
  next action, and for every non-Ready lot an outlined "✦ Draft request with AI" button.
- Top right of the screen: a compact readiness card ("60% ready · 120 of 200 t" plus a thin evidence bar).
- Optional, only if time allows: a simple left-to-right chain for one selected shipment
  (Shipment → Month → Heat → Mill) drawn with HTML boxes and arrows.
- Add hover help (`help=`) for the words precursor, heat number, default value, verification report,
  using the definitions in the pitch sheet.

### 3 Check

- Title: "{n} things to fix" or "Nothing to fix".
- One card per flag: severity as a small coloured label, the plain message in 20 px, and the source documents
  as clickable mono chips that open the document in 1 Read. "Accept with note" as a secondary button.
- Clean and trader scenarios show a calm empty state: large check mark, "All checks passed", list of the
  checks that ran in small text.

### 4 Calculate

- Top card "Our formula matches the Commission's example": two big numbers side by side, ours vs the
  Commission's, for each product (2.039 and 2.371 come from the existing proof function), with a ✓.
- Below: the factory result, or a clear "Input missing" card listing which lots need a default value, with
  the input boxes. Label every result "Illustrative, for evidence preparation".
- Formula shown once, small, with symbols explained in one line each.

### 5 Export

- One large card: "Evidence pack for the verifier", the six sheet names as a checklist with ✓ / missing,
  and one big download button. Small text: "Draft prepared for verifier review".

## 8. The two signature visuals (build these with HTML/CSS or inline SVG, not default charts)

**Evidence bar.** One horizontal bar, 100% = steel consumed in the reporting year. Segments by verdict in the
verdict colours, widths from tonnes per verdict (computed). Above it the big headline number (share of tonnes
that are Ready). Under each segment: tonnes and badge name. Animate segment widths growing from 0 on load
(0.6 s ease-out, once). This is the image judges should remember.

**Path to evidence pack.** Five stages in a row: Documents read → Fields approved → Steel traced → Checks clear
→ Pack ready. Each stage: a circle (filled when complete, a partial ring showing progress when not, e.g.
"31/37"), label under it, thin connecting line that fills as stages complete. Like a delivery-status tracker.

No pie charts, no default Streamlit/Altair charts, no 3D, no gradients on data.

## 9. Writing rules for all screen text

- Headlines as questions or answers, never system names ("Can this steel use real data?", not "Precursor status").
- Maximum 12 words per line, maximum 2 lines per card. Move detail into hover help or an expander.
- Plain words: "mill report", "default value", "needs a check". Avoid internal IDs except in mono chips.
- Keep the honesty words: draft, illustrative, synthetic, for verifier review. None of: certified,
  compliant, audit-ready, ISO, guaranteed, saves.

## 10. Logo

Use `assets/logo_mark.svg` (the perforated stamp with T, recreated from the team's green logo and recoloured to
Dark Emerald on paper). Next to it the wordmark as HTML text: "TRACE" in Inter 600, letter-spacing 0.25em, and
"CHECK AI" below in Inter 400, letter-spacing 0.3em, `--ink-2`. `assets/logo_mark_dark_bg.svg` is for the dark
hero tile. Also use the mark as the browser tab icon (`page_icon`).

## 11. Motion

Subtle only: evidence bar grows once on load; cards fade up 8 px on first render (0.3 s); scan line while the AI
reads. Respect `prefers-reduced-motion`. Nothing loops except the scan line during a read.

## 11b. Visual reference

The approved mockups of Overview and Trace are in Figma ("TraceCheck UI mockup"):
https://www.figma.com/design/3hZifYNHBUQLTjp9hOuWXw
PNG copies are in docs/mockups/ (overview.png, trace.png) for offline reference. Match their layout, spacing, type sizes and colours. The numbers in the mockup come from the clean scenario
specification; the app must compute its own. The other four screens follow the same components.

## 12. How to work and check

1. Add `.streamlit/config.toml` (theme colours, font fallbacks, static serving) and `static/style.css`.
2. Build shared components first as small functions in a new `ui.py`: top bar, card, big number, badge,
   evidence bar, progress path, document sheet.
3. Rebuild the screens in this order: Overview, 2 Trace, 1 Read, 3 Check, 4 Calculate, 5 Export.
4. After each screen: run `pytest -q`, open the app in the browser pane at 1366×768, take a screenshot, check
   it against section 1 (one question, one glance), fix, commit.
5. At the end, screenshot every screen for all three scenarios and save them to `docs/screens/`. Write a short
   `docs/DESIGN_NOTES.md`: what changed, what was cut, anything that did not work in Streamlit.
