# Website Review Plan

## Objective

- Produce a single homepage review for `https://www.freedsolutions.com/` that Claude Code can execute without consulting the model-specific `*-plan.md` files.
- Keep the deliverable as a written review only in this phase, not code changes.
- Return the review in exactly four sections: `Must Fix`, `Should Fix`, `Nice To Have`, and `Do Not Change`.
- For each finding, include what is wrong, why it matters, where it appears, and the smallest reasonable fix.

## Source Of Truth And Scope

- Use live production behavior at `https://www.freedsolutions.com/` as the primary source of truth.
- Use local repo files only to explain the implementation behind a finding, especially `index.html` and directly referenced assets in `brand/`.
- Keep scope to the homepage plus crawl/share artifacts: `/favicon.ico`, `/robots.txt`, and `/sitemap.xml`.
- Do not expand this into a full redesign, multi-page crawl, or generic UX audit.

## Must Fix

- Missing canonical tag.
  Where: `<head>` in `index.html` and live production markup.
  Why: search engines can split authority across duplicate URLs if the canonical domain is not explicit.
  Smallest fix: add `<link rel="canonical" href="https://www.freedsolutions.com/">`.
- Missing icon declarations and live `/favicon.ico` 404.
  Where: no `rel="icon"` or `rel="apple-touch-icon"` links in `<head>` and live `/favicon.ico` returns 404.
  Why: browsers request a favicon by default, the missing file creates a visible quality issue and unnecessary 404 noise, and mobile/home-screen icon support is incomplete.
  Smallest fix: add icon links in `<head>` and provide a root favicon asset.
- Missing `/robots.txt`.
  Where: repo root and live production endpoint.
  Why: a missing file is not catastrophic, but it is a standard crawl-control artifact and should exist on a marketing site.
  Smallest fix: add a minimal allow-all `robots.txt` that also points to the sitemap.

## Should Fix

- Missing `/sitemap.xml`.
  Where: repo root and live production endpoint.
  Why: even a one-page site benefits from an authoritative sitemap for crawlers and Search Console, but it is not required for a single-page site.
  Smallest fix: add a single-URL sitemap for `https://www.freedsolutions.com/`.
- Missing JSON-LD structured data.
  Where: no `<script type="application/ld+json">` block is present in the page.
  Why: business/service structured data can improve search understanding without changing visible content.
  Smallest fix: add minimal schema using only facts already stated on the page.
- Missing `h2` hierarchy for major section titles.
  Where: major section titles use styled `<div class="section-title">` elements instead of headings.
  Why: the page currently jumps from `h1` to `h3` and `h4`, which weakens document structure for accessibility and SEO.
  Smallest fix: convert major section titles to semantic `h2` elements without changing visual styling.
- Missing `theme-color`.
  Where: `<head>` in `index.html`.
  Why: mobile browsers use it for browser-chrome theming and it is a low-cost polish improvement.
  Smallest fix: add `<meta name="theme-color" content="#111113">` or the final chosen brand-aligned color.
- Missing Google Fonts preconnect for `fonts.gstatic.com`.
  Where: `<head>` currently preconnects only to `fonts.googleapis.com`.
  Why: font files are served from `fonts.gstatic.com`, so the current setup misses the most useful connection warm-up.
  Smallest fix: add `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>`.
- Inline base64 photo assets should become normal optimized assets.
  Where: inline `data:image/jpeg;base64,...` images in `index.html`.
  Why: embedding large images directly in HTML increases document weight and reduces caching flexibility.
  Smallest fix: export optimized image files, store them as normal assets, and reference them by path.
- `og:image` and `twitter:image` assets are too large.
  Where: both tags point to `brand/logo-square-purple-text.png`.
  Why: the current file is ~1.4 MB, far exceeding the recommended <1 MB for social preview crawlers, and can slow or prevent share-image rendering.
  Smallest fix: generate an optimized social image asset and update both metadata tags to use it.

## Nice To Have

- Add a fuller icon/app-icon set when favicon work happens.
  Why: improves polish across devices and platforms once the primary favicon issue is fixed.
  Smallest fix: add common icon sizes only if they can be generated from the existing square logo asset.
- Add optional Open Graph image dimensions and supporting social metadata.
  Why: can improve preview consistency once the social image asset is finalized.
  Smallest fix: add `og:image:width`, `og:image:height`, and optionally `og:site_name` / `og:locale`.
- Revisit the Twitter card format only if a dedicated social card asset is created.
  Why: the current metadata baseline is already good, so this should not be churn for its own sake.
  Smallest fix: keep the current card unless a better share asset justifies a richer format.

## Do Not Change

- Keep the current title tag.
- Keep the current meta description.
- Keep the current Open Graph and Twitter title/description copy.
- Keep `og:url` pointing at `https://www.freedsolutions.com/`.
- Keep the current internal anchors for `about`, `framework`, `process`, `experience`, and `contact`.
- Keep the current choice of the text logo asset for social sharing unless it is being optimized for size.
- Do not add speculative marketing claims, keyword stuffing, or invented schema facts.
- Do not include the stale claim that the hero image alt text is wrong; the current photo alt text is not the logo/headshot mismatch described in the old Claude-specific plan.

## Verification

- Confirm live production is missing canonical, icon links, `theme-color`, and JSON-LD.
- Confirm live `/favicon.ico`, `/robots.txt`, and `/sitemap.xml` currently return 404.
- Confirm the heading structure is `h1` followed by `h3` and `h4`, with no `h2` elements for major section titles.
- Confirm `index.html` still contains inline base64 image assets before recommending replacement.
- Confirm `og:image` and `twitter:image` still point to `brand/logo-square-purple-text.png`.
- Confirm the page still preconnects to `fonts.googleapis.com` without a matching `fonts.gstatic.com` preconnect.
- Confirm the current photo alt text still matches the displayed assets; do not revive the old logo/headshot mismatch claim unless the asset changed.
- Confirm the review remains aligned with both the live site and the local repo before Claude Code uses it.

## Assumptions

- This document is the working plan for Claude Code and should supersede the three model-specific `ops/*-plan.md` files for this task.
- The existing model-specific plan files remain in place as reference material and should not be edited or deleted in this step.
- Prompt files remain unchanged in this step.
- The output of the later Claude Code task is a written review, not immediate website implementation.
- Treat missing `meta name="robots"` as non-urgent unless a conflicting crawl directive is discovered elsewhere.
