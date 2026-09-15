#!/usr/bin/env bash
# render_docs.sh <source.md> [...] — DOCX + PDF into <source dir>/renders/, house recipe (pandoc-deliverable skill:
# Calibri/Consolas, 2-level TOC, wide-tables filter, glyph substitution piped in memory; the source .md is
# never touched). Run from anywhere:  bash <skill>/scripts/render_docs.sh <estate dir>/BI-SOP.md
#
# A missing glyph FAILS the run (2026-09-14, Adam's ruling). Until then the count was printed and
# never read, which is the `feedback_bi_change_gate_inert_check` shape exactly: the Dictionary
# rendered with 1 warning for at least a full day and nothing went red, because xelatex drops the
# character and pandoc still exits 0. The render is KEPT on disk — it is still the best available
# copy — and every file in the argument list is still rendered; the exit is taken once, after the
# loop, so a red on file 1 cannot hide files 2..n.
set -euo pipefail
PANDOC="$LOCALAPPDATA/Pandoc/pandoc.exe"
MIKTEX_BIN="$LOCALAPPDATA/Programs/MiKTeX/miktex/bin/x64"
SKILL="$HOME/.claude/skills/pandoc-deliverable"
LUA="$SKILL/wide-tables.lua"
SUBS_PY="$SKILL/glyph_subs.py"
GLYPH_FAILURES=0
for SRC in "$@"; do
  SRC_DIR="$(dirname "$SRC")"; BASE="$(basename "$SRC" .md)"
  # Renders live in their own subdir (P6, 2026-09-08): 29 DOCX/PDF beside the sources were ~40% of
  # the estate's top-level file count. --resource-path still points at SRC_DIR so images resolve.
  OUT_DIR="$SRC_DIR/renders"; mkdir -p "$OUT_DIR"
  OUT_DOCX="$OUT_DIR/$BASE.docx"; OUT_PDF="$OUT_DIR/$BASE.pdf"
  PREV_DOCX=0; [ -f "$OUT_DOCX" ] && PREV_DOCX=$(stat -c %s "$OUT_DOCX")
  "$PANDOC" "$SRC" -o "$OUT_DOCX" --from gfm-tex_math_dollars --lua-filter "$LUA" --resource-path "$SRC_DIR" --toc --toc-depth=2
  python "$SUBS_PY" "$SRC" | PATH="$MIKTEX_BIN:$PATH" "$PANDOC" -f gfm-tex_math_dollars --lua-filter "$LUA" --resource-path "$SRC_DIR" -o "$OUT_PDF" --pdf-engine=xelatex --toc --toc-depth=2 -V geometry:margin=0.75in -V mainfont="Calibri" -V monofont="Consolas" -V fontsize=10pt 2> "$SRC_DIR/.render-$BASE.log" || { echo "PDF FAILED for $BASE"; tail -20 "$SRC_DIR/.render-$BASE.log"; exit 1; }
  NEW_DOCX=$(stat -c %s "$OUT_DOCX"); NEW_PDF=$(stat -c %s "$OUT_PDF")
  MISSING=$(grep -c "Missing character" "$SRC_DIR/.render-$BASE.log" || true)
  echo "$BASE: docx $PREV_DOCX -> $NEW_DOCX bytes, pdf $NEW_PDF bytes, missing-char warnings: $MISSING"
  if [ "$MISSING" -gt 0 ]; then
    # Print the warnings themselves, not just the count: the codepoint is the whole diagnosis, and
    # the log is deleted two lines below.
    echo "  MISSING GLYPHS in $BASE — the PDF on disk is silently short these characters:"
    grep "Missing character" "$SRC_DIR/.render-$BASE.log" | sed 's/^/    /'
    echo "    source: $SRC"
    GLYPH_FAILURES=$((GLYPH_FAILURES + 1))
  fi
  rm -f "$SRC_DIR/.render-$BASE.log"
done
if [ "$GLYPH_FAILURES" -gt 0 ]; then
  echo ""
  echo "$GLYPH_FAILURES file(s) rendered with missing glyphs. The renders are on disk and are the best"
  echo "available copy, but a character has been dropped from each. Add the codepoint to the glyph map in"
  echo "\$HOME/.claude/skills/pandoc-deliverable/glyph_subs.py (and its tracked source), then re-render."
  exit 1
fi
