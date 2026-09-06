<!-- Generated from "freed-solutions/skills/designed-pdf/components.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# designed-pdf components

Every component below is a class set in `print-base.css` plus the HTML that uses it. Compose a
document from these; do not invent a new layout for a shape that already exists here. All
examples use neutral placeholder data. `example.html` in this folder stitches every component
into one two-page document, so render it first to see the look.

Conventions that hold across all components:

- Colour carries meaning. Indigo (`--ind`) = the thing being decided and the recommended option.
  Amber (`--amb`) = an open call. Soft tints with dark text = data chips. Grey = secondary text only.
- Copy is fragments, not sentences, wherever a label will do.
- Labels never wrap. If one wraps, widen its column, do not shrink the font.
- `white-space: nowrap` is already on chips, stats, call options and example-row notes.

## 0. Generator skeleton

One Python file per document: data at the top, a CSS block that inlines the base sheet, one
function per page, a `main` that writes `<name>.html`. Keep it beside the deliverable's other
scripts. The HTML is the source of truth for the PDF; never hand-edit the PDF.

```python
import html, sys
from pathlib import Path

def base_css() -> str:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        p = parent / ".claude" / "skills" / "designed-pdf" / "print-base.css"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError("print-base.css not found: run the skill wrapper sync")

EXTRA_CSS = """
/* document-specific overrides go here, after the base */
"""

def page1() -> str:
    return "<div class=\"page\"> ... </div>"

def page2() -> str:
    return "<div class=\"page\"> ... </div>"

doc = ("<!doctype html><html><head><meta charset=\"utf-8\"><title>Title</title><style>"
       + base_css() + EXTRA_CSS + "</style></head><body>" + page1() + page2() + "</body></html>")
Path(sys.argv[1]).write_text(doc, encoding="utf-8")
```

Then: `python .claude/skills/designed-pdf/render_pdf.py out.html out.pdf --pages 2`.

## 1. Page frame

Title, a short accent bar, a one-line subtitle. Page 2 uses `h1.small`. Each page is one
`.page` div; the last one gets no trailing page break.

```html
<div class="page">
  <h1>Decision Title</h1>
  <div class="accent"></div>
  <p class="sub">One line of context: what the document covers and the date.</p>
  ...
  <p class="foot">Per-line detail: name-of-the-workbook.xlsx</p>
</div>
```

## 2. Segment chips

A structured value (a name, a code, a key) drawn as labelled parts instead of a code string.
Each part gets a tint by ROLE, assigned once for the whole document:

| class | role | look |
|---|---|---|
| `lead` | the identifying part | teal, bold |
| `focus` | the part under decision | indigo chip, bold (the accent) |
| `t1`, `t2` | other parts | green, sky |
| `opt` | an optional trailing part | dashed lavender |

```html
<span class="name">
  <span class="s lead">Acme</span><span class="bar">|</span>
  <span class="s focus">Widget</span><span class="bar">|</span>
  <span class="s t1">Blue</span><span class="bar">|</span>
  <span class="s t2">12-pack</span><span class="bar">|</span>
  <span class="s opt">Holiday</span>
</span>
```

Helper for a `" | "`-separated value, with the optional last part detected by position:

```python
ROLES = ["lead", "focus", "t1", "t2"]

def seg(value: str, opt_from: int = 4) -> str:
    parts = value.split(" | ")
    out = []
    for i, p in enumerate(parts):
        cls = "opt" if i >= opt_from else ROLES[min(i, len(ROLES) - 1)]
        out.append(f'<span class="s {cls}">{html.escape(p)}</span>')
    return '<span class="name">' + '<span class="bar">|</span>'.join(out) + '</span>'
```

A neutral alternative value beside a chip row (an "option B" word) is a `.pill`:
`<span class="pill">Other word</span>`.

## 3. Segment strip

One labelled box per part of the shape, with the part under decision highlighted (`seg focus`)
and an optional part dashed (`seg opt`). Each box: `k` = the part's label, `v` = an example
value, `r` = one fragment of rule. Default grid is five columns; override
`grid-template-columns` inline for a different count.

```html
<div class="strip">
  <div class="seg"><div class="k">Maker</div><div class="v">Acme</div><div class="r">As the maker writes it.</div></div>
  <div class="seg focus"><div class="k">Kind</div><div class="v">Widget</div><div class="r">The one open question, below.</div></div>
  <div class="seg"><div class="k">Variant</div><div class="v">Blue (2:1)</div><div class="r">Colour or pattern; a ratio rides in parentheses.</div></div>
  <div class="seg"><div class="k">Size</div><div class="v">12-pack</div><div class="r">Per unit x pack.</div></div>
  <div class="seg opt"><div class="k">Edition, optional</div><div class="v">Holiday</div><div class="r">A seasonal drop.</div></div>
</div>
<div class="tagline"><span class="k">Short form</span> the same value without the Maker chip: <span class="ex">Widget | Blue (2:1) | 12-pack</span>.</div>
<p class="note"><b>Settled rule in one line.</b> The detail lives elsewhere.</p>
```

## 4. Decision grid

A label column plus one column per option. The recommended option's header is `hd a` (accent)
and its cells carry class `a` (tinted). The other option is `hd b`. The empty corner is `hd x`.
A row label may carry a muted second line (`span.m`) for a count or an example. Three columns
by default; add `c4` for label + three options.

```html
<h2>Whose word wins?</h2>
<div class="grid">
  <div class="hd x"></div>
  <div class="hd a">A &nbsp;One vocabulary<span class="badge">Recommended</span></div>
  <div class="hd b">B &nbsp;Two vocabularies</div>

  <div class="lab">The rule</div>
  <div class="a">The word we sell by: <b>Widget</b>, <b>Gadget</b>. One name everywhere.</div>
  <div>The system word in the store; our word online only.</div>

  <div class="lab">Exceptions<br><span class="m">68 of 128 lines</span></div>
  <div class="a">In the name.</div>
  <div>Online only.</div>

  <div class="lab">Work per new item</div>
  <div class="a">One name. The system checks the copy.</div>
  <div>Two names and a lookup per line. Nothing checks the second.</div>
</div>
```

Rules: 6 to 9 rows fit on a page with the strip and calls above and below; cells are fragments;
the last row loses its bottom border automatically (3 or 4 columns only).

## 5. Stat strip

Three or four numbers with a fragment each. Numbers in the accent colour. Keep it to one line.

```html
<div class="stats">
  <div><span class="n">128</span>product lines</div>
  <div><span class="n">68</span>use a word the system does not</div>
  <div><span class="n">763 of 871</span>already match</div>
</div>
```

## 6. Calls with checkboxes

The open decisions, numbered in amber, each with the options as checkboxes and a plain
"We recommend" line. The recommended box is pre-marked (`box rec`). No formal sign-off block,
no signature line.

Single A/B call:

```html
<h2>Two calls</h2>
<div class="call">
  <div class="num">1</div>
  <div class="t"><b class="h">A or B.</b> &nbsp;
    <span class="pick"><span class="box rec"></span>A</span>
    <span class="pick"><span class="box"></span>B</span><br>
    <span class="rec-line"><b>We recommend A.</b> B keeps every exception; it only moves them where nothing checks them.</span></div>
</div>
```

A call over several items, each with its own keep/drop boxes (two-column amber cards):

```html
<div class="call">
  <div class="num">2</div>
  <div class="t"><b class="h">Four vendor words: keep or drop.</b>
    <div class="words">
      <div><b>Word one</b><span class="m">Maker, 26 items</span><span class="chk"><span class="pick"><span class="box"></span>keep</span><span class="pick"><span class="box rec"></span>drop</span></span></div>
      <div><b>Word two</b><span class="m">Maker, 3 items</span><span class="chk"><span class="pick"><span class="box"></span>keep</span><span class="pick"><span class="box rec"></span>drop</span></span></div>
    </div>
    <p class="rec-line"><b>We recommend drop.</b> One fragment of reason. The trade, named.</p></div>
</div>
<p class="decided"><b>Already decided:</b> the settled items, as fragments, so the reader knows what is not being asked.</p>
```

## 7. Grouped example rows

Page-2 pattern: a legend, then one `.group` per category with a small-caps heading and rows of
`case | value | note`. The left column is fixed-width and wide enough that no case label wraps;
the right column is a muted note (`same`, or `B: <pill>`). Groups never split across pages.

```html
<div class="page">
  <h1 class="small">Examples by category</h1>
  <div class="accent"></div>
  <p class="sub">All values follow Option A. Where B differs, it is shown at right.</p>
  <div class="legend">
    <span><!-- seg("Maker | Kind | Variant | Size | Edition") --></span>
    <span>Kind is the open question; dashed = the optional Edition.</span>
  </div>

  <div class="group">
    <h3>Category one</h3>
    <div class="row"><div class="case">typical</div><div><!-- seg(...) --></div><div class="b"><span class="same">same</span></div></div>
    <div class="row"><div class="case">edge case</div><div><!-- seg(...) --></div><div class="b">B: <span class="pill">Other word</span></div></div>
  </div>
</div>
```

Python for the rows:

```python
SAME = '<span class="same">same</span>'
def group(title, rows):  # rows = [(case, value, alt_or_empty)]
    body = "".join(
        '<div class="row"><div class="case">' + html.escape(case) + '</div><div>' + seg(value) + '</div>'
        + '<div class="b">' + (('B: <span class="pill">' + html.escape(alt) + '</span>') if alt else SAME) + '</div></div>'
        for case, value, alt in rows)
    return '<div class="group"><h3>' + html.escape(title) + '</h3>' + body + '</div>'
```

## 8. Fitting to the page budget

Order of moves when a page overflows, cheapest first:

1. Section spacing: `h2` margins, `.grid > div` padding, `.group`/`.row` padding.
2. Column ratios on `.grid`, `.strip`, `.row` (inline `style="grid-template-columns: ..."`).
3. Body font 10pt to 9.6pt, chips 9.2pt to 8.8pt. Never below 8.4pt for body text.
4. `@page` margins down to 0.5in.
5. Copy: cut sentences to fragments.
6. Content: drop a row or a stat. Last resort, and say so in the handoff.

Check the render after each move. A wrapped label is a bug at any step.
