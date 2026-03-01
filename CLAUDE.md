# FreedSolutions — Workflow Contract

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact (never edit manually).
- `build.js` is the deterministic build script that regenerates the artifact.
- `preview.html` loads the built artifact in a local browser for preview (requires a local server).

## Architecture
This is a **LinkedIn carousel slide designer** — a single-page React app that renders to HTML5 Canvas for pixel-accurate slide export.

**Runtime model:**
- React 18.2.0 (UMD from CDN) + Babel Standalone 7.26.10 (browser JSX transform)
- `preview.html` pins these versions to match the Claude.ai artifact sandbox — do not upgrade without verifying sandbox parity
- No bundler, no transpiler, no module system — source files are concatenated by `build.js` into a single JSX artifact

**Zero-dependency constraint:**
- No `package.json`, no `node_modules`, no npm. Do not add them.
- `build.js` uses only Node.js built-ins (`fs`, `path`)
- `preview.html` loads React/Babel from unpkg CDN
- This constraint is intentional — the artifact must run identically in `preview.html` and when pasted into Claude.ai's artifact sandbox

## Source Manifest
`build.js` defines an explicit `ORDER` array that lists all 19 source files and their concatenation sequence. **This array is the single source of truth** for what ships in the artifact and in what order.

Dependencies flow top-to-bottom in `ORDER`: each file may reference symbols defined in files above it.

**Structure at a glance:**
| Layer | Files | Purpose |
|-------|-------|---------|
| Constants | `constants.js` | Shared constants (`MAX_SLIDES`, `FONT_OPTIONS`, `composeFont`) |
| Canvas | `canvas/*.js` (7 files) | Pure rendering: backgrounds, text, overlays, screenshots, slide composition |
| Data | `slideFactory.js`, `undoRedo.js`, `pdfBuilder.js` | Slide model, undo stack, PDF generation |
| UI components | `ColorPickerInline.jsx`, `SizeControl.jsx`, `SlideSelector.jsx` | Reusable React components |
| Hooks | `useSlideManagement.js`, `useCanvasRenderer.js`, `usePdfExport.js`, `usePresets.js` | State management, rendering, export, presets |
| App | `App.jsx` | Root component, layout, event wiring |

## Workflow: Write → Build → See → Push

### 1. Write
Edit source files in `src/`. Draft `FEATURE_CARD.md` for anything non-trivial.

**Adding a new source file:**
1. Create the file in `src/` (or `src/canvas/` for rendering code)
2. Add it to the `ORDER` array in `build.js` at the correct dependency position
3. Rebuild — the build will fail if a file is in `ORDER` but missing on disk, but will **silently exclude** a file that exists on disk but is not in `ORDER`

### 2. Build
```bash
node build.js
```
Required after any `src/` change. No exceptions.

### 3. See
Serve the repo root locally and open `preview.html` in a browser. The preview loads the built artifact directly — what you see is what ships. Refresh after each build.

```bash
npx serve . --listen 5173
# then open http://localhost:5173/preview.html
```

For visual/UX judgment calls on new features, use browser Claude as a second pair of eyes. Describe what changed and what to look at — no structured handoff card needed.

### 4. Push
```bash
git push origin main
```

## AI Assistant Context

When working with Claude Code, Codex, or any AI assistant on this repo:

**For feature implementation**, the assistant should:
- Make targeted edits in `src/`
- Run `node build.js` to regenerate the artifact
- Add a `CHANGES.md` entry if behavior changed
- If a new source file was created, add it to `ORDER` in `build.js` at the correct dependency position
- Commit all changed files (source + artifact + docs) atomically
- Replace `FEATURE_CARD.md` with current feature scope before starting (do not append to prior feature cards)

**For code review**, the assistant should:
- Review the diff with findings-first rigor (bugs/regressions/risks, severity ordered)
- Patch issues, rebuild, recommit until clean

**For smoke testing** (optional, for visual/UX verification):
- Open `preview.html` in a local browser to verify changes visually
- For a second opinion, describe the change to browser Claude and let it explore
- Useful for: layout changes, new UI controls, visual regressions
- Not needed for: refactors, bug fixes with obvious behavioral impact, non-visual changes

## Project Files

**Docs** (update per Documentation Update Rules below):
| File | Purpose | Updated when |
|------|---------|-------------|
| `CLAUDE.md` | Workflow contract | Workflow/process changes |
| `CHANGES.md` | Behavior/process changelog | Behavior or process changes |
| `FEATURE_CARD.md` | Current feature scope | Replaced each new feature session |

**Code artifacts** (rarely touched directly):
| File | Purpose | Updated when |
|------|---------|-------------|
| `build.js` | Deterministic concatenation build | New source file added to `ORDER` |
| `preview.html` | Local browser preview harness | React/Babel version pin changes |
| `linkedin-carousel.jsx` | Generated artifact — never edit | Every build |

## Git Policy
- Direct push to `main`.
- Single atomic commit per task (source + artifact + docs together).
- Working tree clean after commit.
- Commit message style: imperative mood, sentence case, no trailing period. ~72 chars max. Use colons or `+` for multi-part summaries.

## Hard Guardrails
- Do not edit `linkedin-carousel.jsx` manually — always regenerate via `node build.js`.
- Do not skip build after source change.
- Verify changes visually in `preview.html` before pushing UI changes.
- Do not add `package.json`, `node_modules`, or npm dependencies — the repo is intentionally zero-dep.
- When adding a new source file, add it to `ORDER` in `build.js` — files not in `ORDER` are silently excluded from the artifact.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts change.
- `CHANGES.md`: add entry when behavior or process changes. Pure refactors with no behavior effect skip this.
