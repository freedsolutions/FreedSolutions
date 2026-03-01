# FreedSolutions — Workflow Contract

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact (never edit manually).
- `build.js` is the deterministic build script that regenerates the artifact.
- `preview.html` loads the built artifact in a local browser for preview (requires a local server).

## Workflow: Write → Build → See → Push

### 1. Write
Edit source files in `src/`.

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
- Commit all changed files (source + artifact + docs) atomically

**For code review**, the assistant should:
- Review the diff with findings-first rigor (bugs/regressions/risks, severity ordered)
- Patch issues, rebuild, recommit until clean

**For smoke testing** (optional, for visual/UX verification):
- Open `preview.html` in a local browser to verify changes visually
- For a second opinion, describe the change to browser Claude and let it explore
- Useful for: layout changes, new UI controls, visual regressions
- Not needed for: refactors, bug fixes with obvious behavioral impact, non-visual changes

## Lean Doc Set
| File | Purpose | Updated when |
|------|---------|-------------|
| `CLAUDE.md` | Workflow contract | Workflow/process changes |
| `CHANGES.md` | Behavior/process changelog | Behavior or process changes |
| `preview.html` | Local browser preview | Rarely (harness changes only) |

## Git Policy
- Direct push to `main`.
- Single atomic commit per task (source + artifact + docs together).
- Working tree clean after commit.

## Hard Guardrails
- Do not edit `linkedin-carousel.jsx` manually — always regenerate via `node build.js`.
- Do not skip build after source change.
- Verify changes visually in `preview.html` before pushing UI changes.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts change.
- `CHANGES.md`: add entry when behavior or process changes. Pure refactors with no behavior effect skip this.
