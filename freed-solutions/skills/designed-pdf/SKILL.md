---
name: designed-pdf
description: Render a business-facing one-pager, decision brief, example sheet, or anything a stakeholder signs off on as a designed PDF - HTML plus print CSS printed by headless Edge to a declared page budget, then checked by looking at the pages. Use for business or external audiences, including operator guides, quick cards and references that client staff read from (a "guide" defaults here even when Adam calls it a WI; ruled 2026-09-08). NOT for the technical tier (SOPs, data dictionaries, work instructions, QC reads), which goes to pandoc-deliverable.
---

# Designed PDF

Produce a business-facing PDF that reads like a designed brief, not a technical document:
a Python generator writes self-contained HTML on top of `print-base.css`, headless Edge prints
it to Letter, `render_pdf.py` counts the pages against the budget, and the pages are LOOKED AT
before delivery. The HTML generator is the single source; the PDF is an output.

## When to Use

- The reader is a business stakeholder: a one-pager, a decision brief, an options sheet, an
  example sheet, a scorecard, anything someone signs off on.
- "External" means anyone outside this working session, including a client's own internal
  stakeholders. A client-internal one-pager is external.
- A `pandoc-deliverable` render came back "hard to read" or "looks like a technical document".
- An operator guide, quick card or reference that client staff will read from — even when the ask
  says "WI" (Adam, 2026-09-08: the item-naming "WI" was a guide; it shipped as *How to Name an Item*
  through this skill and the pandoc files were retired). State the assumption in one line.
- Skip for the technical tier (SOPs, data dictionaries, work instructions, QC reads): those use
  `pandoc-deliverable` (Markdown to DOCX + PDF). If the audience is unclear, ask once.

## Inputs

- **Content** (required): the facts, the decision(s), what is already settled, and the
  recommendation. Usually a Markdown draft or a ruled workbook.
- **Page budget** (required, default 1; 2 for a decision plus an example sheet): declared up
  front and enforced by `render_pdf.py --pages N`.
- **Audience** (required): who signs off. Drives tone (fragments, plain "We recommend") and what
  gets cut first.
- **Output name** (required): `<slug>-<date>.html` and `.pdf` beside the deliverable. If a prior
  version was delivered, a NEW versioned name; never overwrite a delivered file.
- **Palette** (optional): defaults to the base. Change only tints, never the rule that colour
  carries meaning.

Missing page budget or audience: ask one question, then proceed.

## Files in this skill

- `print-base.css` - the base sheet: `@page`, palette, chips, segment strip, decision grid,
  stat strip, calls with checkboxes, grouped example rows.
- `components.md` - one description and HTML snippet per component, plus the generator skeleton
  and the fit-to-budget ladder. Read it before writing a generator.
- `render_pdf.py` - `python .claude/skills/designed-pdf/render_pdf.py <html> <out.pdf> [--pages N]`.
  Prints the page count; exit 1 if the count exceeds the budget; exit 2 if the render failed.
- `example.html` - every component in one two-page document. Render it to see the target look.

## Workflow

### 1. Intake

State the page budget, the audience, and the one thing being decided in a single line before
writing anything. List what is already settled (it becomes the "Already decided" line, not a
section). Pick the accent meaning: the accent marks the decided thing and the recommended option,
amber marks the open calls, nothing else gets colour.

### 2. Author the generator

One Python file beside the deliverable's other scripts: data at the top, page builders below,
the base CSS inlined (`base_css()` in `components.md` §0), document-specific CSS appended after
it. Compose from `components.md`; a structured value is always drawn as segment chips, never as
a code string. Write copy as fragments. Run it to produce `<name>.html`.

### 3. Render

```
python .claude/skills/designed-pdf/render_pdf.py <name>.html <name>.pdf --pages <N>
```

Exit 1 means over budget: go to step 5, do not deliver.

### 4. Read the pages

Open the PDF with the Read tool (it renders pages as images) and check every page:

- no label wraps (a wrapped label means a column is too narrow);
- the accent appears only on the decided thing and the recommended option;
- no page is a stub (a last page with two lines means the budget or the spacing is wrong);
- checkboxes, stats and chips render with their tints (if everything is grey,
  `print-color-adjust: exact` was lost);
- nothing is clipped at the right margin.

### 5. Fit

Tighten before cutting: spacing, then column ratios, then font size (never below 8.4pt body),
then `@page` margins, then copy to fragments, then content. The ladder with numbers is
`components.md` §8. Re-render and re-read after each move.

### 6. Deliver

Hand over the PDF. Keep the HTML and the generator as the source and say so in the handoff
("generator: `<script>.py`; the `.md`/pandoc copies are superseded" when that is the case).
Do not commit the PDF or HTML if the deliverable folder is gitignored; the generator follows the
folder's convention.

## Design rules (approved 2026-09-05)

In the order the feedback arrived:

1. Names and keys as labelled segment chips, not code strings with literal separators.
2. Colour with meaning, few colours: one accent for the decided thing and the recommended option,
   one warm tone for open calls, soft per-segment tints with dark text. Never black or grey
   blocks for data chips.
3. Copy cut to fragments.
4. An informal calls block: numbered, checkboxes for each option, the recommendation pre-marked,
   a plain "We recommend X." line. No formal sign-off, no signature block, no AI-speak.
5. A left column wide enough that labels never wrap.
6. A fixed page budget, verified by looking at the pages.

## Guardrails

- Brand-neutral: no client names, paths, products or people in this skill. Client specifics
  live in the generator beside the deliverable.
- Colour must carry meaning. A tint with no meaning is removed, not recoloured.
- Never a solid black or grey block for data chips.
- Labels never wrap. Widen the column or shorten the label; never shrink the font to fit a label.
- The HTML generator is the single source. Never hand-edit the HTML or the PDF.
- The page budget is declared before authoring and enforced by `render_pdf.py --pages`.
- Never a Pandoc table for this audience.
- Never deliver a PDF without reading the rendered pages.
- Do not install a browser. `render_pdf.py` finds Edge or Chrome; if neither exists, stop and
  say so.

## Gates

| Operation | Gate |
|---|---|
| Author + render + read + fit with a declared budget and audience | ungated |
| Budget or audience missing; a palette change; cutting content to fit | one question, then proceed |
| Committing deliverables; editing a delivered file in place | out of scope, caller's call |

## Known gotchas

- Chrome is not installed on this workstation; Edge is. `render_pdf.py` looks in the Edge x86 and
  x64 paths, then Chrome, then PATH. Override with `--browser` or `DESIGNED_PDF_BROWSER`.
- The render uses a throwaway `--user-data-dir`, so an open Edge window does not interfere.
- Chromium prints noisy stderr on success; `render_pdf.py` shows it only when no PDF appears.
- `-webkit-print-color-adjust: exact` is in the base sheet; without it every tint prints white.
- `.group` carries `page-break-inside: avoid`; a long group that cannot fit is split by the
  generator, not by the browser.
- "Segoe UI" is Windows-only. The stack falls back to Calibri, Arial, sans-serif.
- Letter size is set in `@page`. A4 is a one-line change in the document's CSS block.
- `pypdf` counts the pages; without it `render_pdf.py` falls back to a regex count.

## References

- `components.md`, `print-base.css`, `render_pdf.py`, `example.html` - this folder.
- Sibling skill `pandoc-deliverable` for technical documents (user-scope skill).
- Memory `feedback_business_onepager_designed_pdf.md` - why this skill exists.
- Memory `feedback_review_files_are_adams.md` - versioned delivery, never overwrite a delivered file.
