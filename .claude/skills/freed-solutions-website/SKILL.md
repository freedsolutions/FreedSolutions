---
name: freed-solutions-website
description: Edit the Freed Solutions landing page (index.html) and privacy policy within the established design system, deploy via direct push to main (GitHub Pages), and visually QA at desktop + mobile widths. Use when Adam wants copy, links, photos, stats, or section ordering updated on www.freedsolutions.com.
---

<!-- Generated from "freed-solutions/skills/freed-solutions-website/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Freed Solutions Website

Edit the public site at www.freedsolutions.com — a single-file static landing page (`index.html` at repo root) plus a privacy policy at `privacy-policy/index.html`, deployed via GitHub Pages on push to `main`. Match the inline CSS design system, keep the page render-safe at mobile + desktop widths, and respect the CTA strategy gate in the repo CLAUDE.md.

## When to Use

- Adam wants to update copy, links, photos, stats, or section ordering on the landing page.
- A new page section, badge, or asset slots into the existing design system.
- The privacy policy needs a wording change.
- An Action Item, email, or live conversation surfaces a "fix the FS website" ask.

## When NOT to Use

- Brand-new design system or visual rebrand — out of scope; deserves its own engagement.
- LinkedIn carousel slide work — separate project (`projects/linkedin-carousel/`).
- Notion CRM record updates — go through `notion-action-items`.

## Inputs

- **Change description** (required): concrete enough to find the right block ("add LinkedIn link to footer", "swap Nightjar revenue stat to 3x", "lead Experience with Freed Solutions").
- **Source asset/URL** (optional): for new photos, external links, badges.
- **Target page** (optional, default = `index.html`): privacy policy is the only other live page.

If placement is ambiguous (e.g., "add my LinkedIn" with no placement specified), use `HARDENED_GATE` before editing.

## Site Layout

Landing page (`index.html`, ~890 lines, single file):
- `<head>`: meta, OG, JSON-LD schema, all CSS in one inline `<style>` block. CSS variables live under `:root` near line 47.
- `<body>` sections in order: Nav · Hero · Problem · Quote · Framework (Venn) · How I Work · Outcomes · Experience · Past Clients · Quote 2 · CTA · Footer.
- Inline `<script>` at the bottom: IntersectionObserver for `.reveal` animations, mobile menu toggle, footer year.

Section IDs (anchored from nav): `#about`, `#framework`, `#process`, `#experience`, `#contact`. Don't rename without updating `<nav>` links and any inbound URL.

Privacy policy (`privacy-policy/index.html`): standalone page, separate styles. Real legal copy — gated.

## Design System

Reuse the CSS variables; don't introduce raw hex. The variables are the contract.

| Token | Value | Use |
|---|---|---|
| `--accent` / `--accent-light` | `#6366f1` / `#818cf8` | Primary CTAs, links, italic emphasis |
| `--green` / `--amber` / `--blue-muted` | `#4ade80` / `#d4a057` / `#6889b4` | Framework Venn pillars (Master / Ops / Software) |
| `--bg-primary` / `--bg-secondary` / `--bg-card` | `#111113` / `#1a1a1e` / `#222226` | Page / band / card backgrounds |
| `--serif` / `--sans` / `--mono` | DM Serif Display / DM Sans / JetBrains Mono | h1-h2 / body / labels |

Patterns to copy when extending:
- Section labels: `<div class="section-label">UPPERCASE MONO LABEL</div>`
- Reveal-on-scroll: add `.reveal` to the top-level block; the `IntersectionObserver` picks it up.
- Cards: `.process-card` / `.outcome-card` / `.exp-item` are the structural templates.
- Buttons: `.btn-primary` filled, `.btn-secondary` outline, `.nav-cta` for the small filled nav button.

## Workflow

### 1. Locate the block

Read `index.html` and find the section the change touches. Anchor by section ID or a `section-label` string. Note the line range before editing.

### 2. Make the edit

Edit in place using the existing markup pattern. Common recipes:

- **Footer external link:** insert into `.footer-links` alongside the Privacy Policy link. External links use `target="_blank" rel="noopener"`.
- **Nav link:** insert inside `<div class="nav-links">` before the `.nav-cta`. Anchors (`#section-id`) for in-page, full URL for external (with `target` + `rel`).
- **Reorder Experience:** rearrange `.exp-item` blocks inside `.exp-list`. Newest-first is the convention; the "Now" Freed Solutions role can lead or trail — confirm if unclear.
- **Stat update:** edit `.stat-number` and `.stat-label` inside the matching `.stat-card`.
- **Swap a photo:** drop the new file in `website/` (committed) and update the `<img src>`. `brand/` is gitignored — assets there will not deploy.

### 3. Visually QA

Serve locally and verify with Playwright MCP at desktop + mobile widths.

```bash
npx serve C:/Users/adamj/Code/FreedSolutions --listen 5173
```

Via Playwright:
- Navigate to `http://localhost:5173/`
- `browser_resize` to 1280×800 (desktop) and 390×844 (mobile); snapshot each
- Confirm: edited block renders, no broken images, nav not overlapping, CTAs still clickable
- For new external links: confirm `target` + `rel`, then `browser_click` to verify the destination loads

Fix any regressions in the same edit pass before committing. Delete files in `.playwright-mcp/` at session end (closeout sanity gate enforces it).

### 4. Commit + push

Direct push to `main` (no PR). Stage only files you changed:

```bash
git add index.html website/<new-asset>
git commit -m "<short imperative summary>"
git push
```

Do not stage `.playwright-mcp/`, `clients/`, or `brand/` — all gitignored.

### 5. Verify deploy

GitHub Pages publishes within 1-2 minutes. Open `https://www.freedsolutions.com/` in a fresh tab and hard-refresh to confirm the change is live.

## Guardrails

- **CTA strategy is gated.** Landing-page CTAs currently route to Calendly. Per the repo CLAUDE.md, don't change CTA targets without confirming current strategy — they may shift when the FS Workspace email goes live.
- **No design rebrand.** Stay within the design system (CSS vars, fonts, spacing). Out-of-scope changes warrant `HARDENED_GATE`.
- **Zero-dep root.** Do not add `package.json`, npm packages, or bundlers at the repo root. Inline `<script>` only.
- **Privacy policy is legal copy.** Use `HARDENED_GATE` before wording changes.
- **External links** use `target="_blank" rel="noopener"`. No `noreferrer` unless requested.
- **Asset ownership.** Public photos/logos → `website/` (committed). Source files (PSD, AI, raw exports) → `brand/` (gitignored).

## Gate Protocol

| Operation | Gate | Notes |
|---|---|---|
| Copy edits, link additions, section reordering, stat updates, photo swaps within the design system | `UNGATED` | Standard recipe with visual QA. |
| Ambiguous placement, missing source asset/URL, deviation from the design system, new section type | `HARDENED_GATE` | One compact decision-shaped question. |
| CTA target changes, privacy policy wording, JSON-LD/schema structure, GitHub Pages config (`CNAME`, workflow files) | `HARDENED_GATE` and surface the strategy concern | Scope creep here can break SEO, live booking, or compliance. |

## Known Limitations

- Single ~890-line file with no component framework. Treat as a feature: edits are local and reviewable in one diff.
- Playwright QA needs Node + `npx serve`. If unavailable, fall back to a `file://` open in a browser; some font/CDN behavior will differ from live.
- GitHub Pages cache can lag a few minutes after push. If a change isn't live, wait before re-pushing.

## References

- Repo CLAUDE.md (root) — CTA strategy gate, GitHub Pages config, artifact cleanup gate
- `index.html` lines ~47-65 — CSS variable definitions (the design system contract)
- `website/` — committed image/icon assets
- `brand/` — local-only brand source files
