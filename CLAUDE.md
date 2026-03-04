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
Edit source files in `src/`.

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

## Feature Flow

### Phase 1 — Get the card

*Trigger A — In-session (feature described in chat):*
Adam describes the feature in Claude Code chat. Claude asks the number of scope/approach questions needed for alignment (typically ~2–6, but more when ambiguity/risk is high), then writes `FEATURE_CARD.md` (replacing the entire file).
Claude must send those questions to the user in plain chat (drafting internally does not count) and wait for answers before writing the card.
Do not use the `AskUserQuestion` tool for this gate.

*Trigger B — External card (card written elsewhere):*
Adam updates `FEATURE_CARD.md` outside this session and types `SHIP` in chat.

### Phase 2 — Explore & ask

Claude reads `FEATURE_CARD.md` and explores the relevant source files in the repo. Then asks the number of implementation questions needed for alignment (typically ~2–6, but more when ambiguity/risk is high) based on what it found (approach choices, ambiguities, edge cases, patterns to reuse or avoid). Once answered, the autonomous SHIP loop starts.
Claude must send questions as an explicit plain-chat message and pause for user answers. Preparing questions without sending them is not completion of this phase.
Do not use the `AskUserQuestion` tool for this gate.
If no questions are needed, Claude must explicitly send: `No blocking questions; proceeding with stated assumptions:` followed by a short assumptions list.
If any response payload is empty/unclear (for example, blank tool-return text), do not treat it as answered. Re-ask in plain chat and wait for a concrete user reply.

This is the single pause point before code changes begin.

### Phase 3 — SHIP loop (autonomous, no pausing)

**Implement:**
- Read `FEATURE_CARD.md` scope and `CLAUDE.md` guardrails
- Make targeted edits in `src/`
- If a new source file was created, add it to `ORDER` in `build.js`
- Run `node build.js` — fix any build errors before continuing

**Self-review:**
- Review own diff against `FEATURE_CARD.md` scope (anything missing? anything out of scope?)
- Review code quality: bugs, regressions, risks — severity ordered
- Patch issues, rebuild, repeat until clean

**Smoke test (via Playwright MCP):**
- Open `http://localhost:5173/preview.html` in Playwright browser
- Light test: verify the new feature works per `FEATURE_CARD.md` scope
- Quick visual check: does the layout look right? Any obvious regressions?
- If issues found: patch, rebuild, re-test
- If Playwright MCP is unavailable or the local server isn't running, stop and ask the user to fix it before continuing

**Commit gate (final step before review):**
- Run `node scripts/archive-smoke-artifacts.js` to file away Playwright MCP logs and smoke screenshots from repo root, `.playwright-mcp/`, and `test-results/`
- Add `CHANGES.md` entry if behavior changed
- Verify `git status` reflects only intended task files
- Commit all changed files atomically (source + artifact + docs)
- Report commit hash (`git rev-parse --short HEAD`) in the handoff
- Do NOT push

### Phase 4 — Your review (post-commit only)
Claude Code pauses only after the Commit gate is complete. Review the diff. Then either:
- Request patches: describe what to fix, Claude Code patches and re-runs from self-review onward
- Push: `git push origin main`

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
- Review handoff must include the local commit hash.
- Commit message style: imperative mood, sentence case, no trailing period. ~72 chars max. Use colons or `+` for multi-part summaries.
- Commit-time artifact hygiene is automated by `.githooks/pre-commit` (one-time setup per clone: `git config core.hooksPath .githooks`).

## Permission Preflight (Before Any Escalation Request)
- Always check permission config files before asking for approval:
  1. `.claude/settings.local.json`
  2. `.claude/settings.json`
- Treat these files as the permission source of truth for the repo session.
- Precedence rule: when both files define the same permission key, `.claude/settings.local.json` takes priority for this session.
- Before requesting escalation, verify whether the exact action is already allowed (including wildcard/pattern matches).
- Re-run this preflight at each phase boundary (`Explore -> Implement`, `Self-review -> Smoke test`, `Smoke test -> Commit gate`).
- Evaluate shell commands by segments (`&&`, `|`, `;`), not only full command strings.
- If a command was only blocked because of a `cd ... &&` wrapper, rerun it from repo root without the `cd` prefix before requesting escalation.
- If allowed, execute without requesting extra permission.
- If not allowed, request escalation with a single-sentence reason tied to the specific blocked command.
- Do not request broad or speculative approvals for actions you are not about to run.
- Re-check permission config after any user or repo instruction that may have changed policy.

## Hard Guardrails
- Do not edit `linkedin-carousel.jsx` manually — always regenerate via `node build.js`.
- Do not skip build after source change.
- Verify changes visually in `preview.html` before pushing UI changes.
- Do not add `package.json`, `node_modules`, or npm dependencies — the repo is intentionally zero-dep.
- When adding a new source file, add it to `ORDER` in `build.js` — files not in `ORDER` are silently excluded from the artifact.
- Do not commit without a passing Playwright smoke test. If the smoke test cannot run, stop and ask.
- Do not commit raw Playwright MCP logs or smoke screenshots from repo root; archive them via `node scripts/archive-smoke-artifacts.js`.
- Do not hand off for user review until a local commit is created and its hash is reported.
- Do not request permission for an action until the Permission Preflight checklist above has been completed.
- Do not start Phase 3 code changes until the Phase 1/2 question message has been sent and answered (or a no-blockers assumptions message has been sent).
- Do not use `AskUserQuestion` for Phase 1/2 alignment gates; ask in plain chat and wait for explicit user responses.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts change.
- `CHANGES.md`: add entry when behavior or process changes. Pure refactors with no behavior effect skip this.
