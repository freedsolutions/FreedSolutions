# FreedSolutions - Multi-Project Repo

## Repo Structure
```text
FreedSolutions/
|- index.html              # Landing page (GitHub Pages)
|- CNAME, .nojekyll        # GitHub Pages config
|- projects/
|  |- linkedin-carousel/   # LinkedIn carousel slide designer
|- ops/                    # Migration prompts, internal ops, and private service scaffolds
|  |- notion-workspace/      # Notion CRM automation docs + workflow config
|- privacy-policy/         # Privacy policy page (GitHub Pages)
|- website/                # Website static assets (favicons, OG images, photos)
|- scripts/                # Repo-level utility scripts (codex_review.py)
|- tests/                  # Repo-level test suite (codex review, closeout sanity, local DB)
|- brand/                  # Brand assets - local only (.gitignore)
```

> **Note:** `scripts/` and `tests/` at the repo root are repo-level utilities, distinct from `ops/notion-workspace/scripts/` which contains Notion-workspace-specific automation scripts.

## Project Routing
Each project has its own CLAUDE.md or README with workflow details.

**LinkedIn Carousel** -> `projects/linkedin-carousel/CLAUDE.md`
- Build: `node projects/linkedin-carousel/build.js`
- Serve: `npx serve projects/linkedin-carousel --listen 5173`
- Source: `projects/linkedin-carousel/src/`
- Hooks: `git config core.hooksPath projects/linkedin-carousel/.githooks`

**Notion Workspace** -> `ops/notion-workspace/CLAUDE.md`
- Docs: `ops/notion-workspace/docs/`
- Notes: instruction docs and session handoff are local source of truth; CRM data stays in Notion (via MCP)

## Artifact Cleanup
- After any session that uses Playwright MCP, delete all files in `.playwright-mcp/` before closeout
- `git status --short` should show no `.playwright-mcp/` entries at session end (directory is gitignored, but stale files waste disk)

## Repo-Level Rules
- Direct push to `main`
- Git hooks path: `projects/linkedin-carousel/.githooks` (validates build ORDER + archives smoke artifacts)
- No `package.json` or `node_modules` at the repo root - zero-dep repo
- `index.html` at root is the Freed Solutions landing page (GitHub Pages)
- Do not edit `index.html` without confirming the current CTA strategy (may change when Workspace email goes live)

## Landing Page
- Hosted via GitHub Pages from repo root
- Custom domain: `www.freedsolutions.com` (configured via `CNAME` file)
- CTA currently links to Calendly booking (`https://calendly.com/freedsolutions/30min`)
