# FreedSolutions — Multi-Project Repo

## Repo Structure
```
FreedSolutions/
├── index.html              # Landing page (GitHub Pages)
├── CNAME, .nojekyll        # GitHub Pages config
├── projects/
│   └── linkedin-carousel/  # LinkedIn carousel slide designer
├── ops/                    # Migration prompts & internal ops
├── brand/                  # Brand assets — local only (.gitignore)
```

## Project Routing
Each project has its own CLAUDE.md with full workflow details.

**LinkedIn Carousel** → `projects/linkedin-carousel/CLAUDE.md`
- Build: `node projects/linkedin-carousel/build.js`
- Serve: `npx serve projects/linkedin-carousel --listen 5173`
- Source: `projects/linkedin-carousel/src/`
- Hooks: `git config core.hooksPath projects/linkedin-carousel/.githooks`

## Repo-Level Rules
- Direct push to `main`
- Git hooks path: `projects/linkedin-carousel/.githooks` (validates build ORDER + archives smoke artifacts)
- No `package.json` or `node_modules` — zero-dep repo
- `index.html` at root is the Freed Solutions landing page (GitHub Pages)
- Do not edit `index.html` without confirming the current CTA strategy (may change when Workspace email goes live)

## Landing Page
- Hosted via GitHub Pages from repo root
- Custom domain: `www.freedsolutions.com` (configured via `CNAME` file)
- CTA currently links to Calendly booking (`https://calendly.com/freedsolutions/30min`)
