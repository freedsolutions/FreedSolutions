---
name: pandoc-deliverable
description: Regenerate DOCX and PDF deliverables from a source Markdown file using the standard Calibri/Consolas style with glyph-substitution preprocessing for PDF safety. Use when a deliverable's Markdown source has changed and the rendered DOCX/PDF copies need to match.
---

# Pandoc Deliverable

Convert a single source Markdown file into a paired DOCX + PDF deliverable in the same directory. Style baseline: Calibri body, Consolas mono, 0.75in margins, 10pt, GFM input, 2-level TOC.

## When to Use

- A client deliverable lives as `<name>.md` and needs `<name>.docx` and `<name>.pdf` regenerated alongside it after edits.
- Any time the standard "Calibri body / Consolas mono / glyph-safe PDF" recipe is wanted.

## Inputs

- **Source path** (required): absolute or repo-relative path to the source `.md` file.
- **Output directory** (optional, default = source's parent directory): where to write the DOCX + PDF.

If the source path is missing, ambiguous, or points to a non-existent file, use `HARDENED_GATE` to ask before doing any work.

## Prerequisites

- Pandoc installed (default on this workstation: `$LOCALAPPDATA/Pandoc/pandoc.exe`).
- MiKTeX with `xelatex` available (default: `$LOCALAPPDATA/Programs/MiKTeX/miktex/bin/x64`).
- MiKTeX auto-install enabled (`initexmf --enable-installer --set-config-value='[MPM]AutoInstall=1'`) so first-run package fetches don't prompt.
- Python on PATH for the glyph-preprocess step (uses standard library only).

If any prerequisite is missing, stop and surface the gap rather than installing silently. Installs are out of scope for this skill.

## Workflow

1. **Resolve the source path.** Confirm the file exists and is readable. Default the output directory to the source's parent unless the caller supplies one.
2. **Build the DOCX.** Word renders glyphs via system font fallback, so no preprocessing needed:
   ```bash
   "$PANDOC" "$SRC" -o "$OUT_DIR/$BASENAME.docx" --from gfm --toc --toc-depth=2
   ```
3. **Preprocess glyphs for PDF.** Calibri/Consolas lack several common chars (checkmark, ballot box, high-voltage, memo, warning) — substitute to safe alternates in a temp copy (do not modify the source `.md`). Use Python with explicit Unicode escapes so the SKILL.md file stays cp1252-safe for the Codex validator:
   ```python
   subs = {
       '\u2705': '[x]',          # CHECK MARK BUTTON
       '\u2B1C': '[ ]',          # WHITE LARGE SQUARE
       '\u26A1': '\u2605',       # HIGH VOLTAGE -> BLACK STAR
       '\U0001F4DD': '\u2022',   # MEMO -> BULLET
       '\u26A0\uFE0F': '!',      # WARNING SIGN + VARIATION SELECTOR
       '\u26A0': '!',            # WARNING SIGN
       '\u2713': '[x]',          # CHECK MARK
   }
   ```
   Write the substituted text to a temp file under `c:/tmp/` (or the system temp dir on non-Windows).
4. **Build the PDF** from the preprocessed temp file:
   ```bash
   PATH="$MIKTEX_BIN:$PATH" "$PANDOC" "$TMP_SRC" \
     -o "$OUT_DIR/$BASENAME.pdf" \
     --from gfm --pdf-engine=xelatex --toc --toc-depth=2 \
     -V geometry:margin=0.75in -V mainfont="Calibri" -V monofont="Consolas" -V fontsize=10pt
   ```
5. **Verify.** Confirm both output files exist and are non-empty. Surface any pandoc errors verbatim, especially missing-character warnings (those indicate the glyph-substitution map needs an addition).
6. **Report.** Output the two file paths + sizes. Do not commit the DOCX or PDF — repo convention is `.md` source committed, generated artifacts kept local. Closeout commit/push of the source `.md` is the caller's job, not this skill's.

## Style Baseline (do not change without confirmation)

| Property | Value |
|---|---|
| Pandoc input | `--from gfm` |
| TOC | `--toc --toc-depth=2` |
| Geometry | `margin=0.75in` |
| Main font | Calibri |
| Mono font | Consolas |
| Font size | 10pt |
| PDF engine | xelatex |

If a caller wants a different style (different font, no TOC, different margins), use `HARDENED_GATE` to confirm before deviating — the baseline is the default for a reason.

## Glyph Substitution Map

(Codepoints listed without inline glyph rendering so this file stays cp1252-safe for the Codex validator. The Python escapes in the workflow code block above are the source of truth.)

| Source codepoint | PDF replacement | Notes |
|---|---|---|
| U+2705 (CHECK MARK BUTTON) | `[x]` | Calibri lacks |
| U+2B1C (WHITE LARGE SQUARE) | `[ ]` | Calibri lacks |
| U+26A1 (HIGH VOLTAGE) | U+2605 (BLACK STAR) | Calibri lacks |
| U+1F4DD (MEMO) | U+2022 (BULLET) | Calibri lacks |
| U+26A0 U+FE0F (WARNING SIGN + variation selector) | `!` | Calibri lacks |
| U+26A0 (WARNING SIGN) | `!` | Calibri lacks |
| U+2713 (CHECK MARK) | `[x]` | Calibri lacks |

If new missing-character warnings appear in pandoc output, add the missing codepoint to the map and to the Python escape block above. Always use `\u` / `\U` escapes in the source — never paste high-codepoint glyphs directly into this file.

## Guardrails

- Never modify the source `.md` — preprocessing happens in a temp copy only.
- Never commit the generated DOCX or PDF unless the caller explicitly requests it.
- Do not install Pandoc, MiKTeX, or LaTeX packages from this skill. Surface missing prerequisites and stop.
- This skill does not delegate to sub-agents.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Build DOCX + PDF from a valid source path with the documented style baseline | `UNGATED` | Standard recipe, no source mutation. |
| Missing/ambiguous source path; caller-requested deviation from the style baseline; new glyph that needs adding to the map | `HARDENED_GATE` | One compact decision-shaped question; re-ask if the reply is empty or unclear. |
| Source file edits, repo commits/pushes, prerequisite installs | `GOVERNANCE_GATE` | Out of scope — defer to the caller's workflow. |

## Known Limitations

- Style baseline assumes Windows fonts (Calibri, Consolas). On non-Windows hosts the caller must supply substitutes via `HARDENED_GATE`.
- First-time PDF builds may take 1–3 minutes while MiKTeX auto-installs missing packages. Subsequent builds are fast (~5–10s).
- Glyph map is curated for the project's typical content (status emojis, marker glyphs). Documents using broader Unicode (CJK, mathematical symbols, etc.) may need an expanded map or a different mainfont.
