# Kickoff Prompt — Paste this first in a fresh chat

> **Status: CONSUMED** — This prompt was used to launch Phase A. The repo restructuring it describes was completed in commit `81ecf22`. Kept as historical reference for the original migration vision.

```
I am migrating my professional identity end-to-end across three
phases. This chat will cover Phase A. Here is the full context
before we begin.

WHO I AM:
  - Adam Freed, fractional data & systems consultant
  - Cannabis industry specialist (20+ years, 10 regulated)
  - DBA: Freed Solutions
  - Current email: freedsolutions@gmail.com
  - Target email:  adam@freedsolutions.com

THE FULL MIGRATION PLAN (three phases):

  Phase A (this chat): Domain purchase, Google Workspace setup,
    Gmail migration, and HTML landing page deployed to
    www.freedsolutions.com

  Phase B (next chat): Update all tools and professional assets —
    Calendly, Notion, Cowork, LinkedIn, resumes (.docx), and
    email signature

  Phase C (final chat): Systematic audit of every remaining
    account and subscription tied to the old Gmail, with a
    tracking spreadsheet at the end

KNOWN ASSETS THAT WILL BE TOUCHED ACROSS ALL THREE PHASES:
  - Google Workspace (new — being created in Phase A)
  - Calendly (free tier → upgrading to Standard)
  - Notion (meeting notes, to-do lists, client work)
  - Cowork (two scheduled automation tasks — calendar sync
    and Outlook invite forwarding — both reference old Gmail)
  - LinkedIn profile
  - Two resume .docx files (Fractional and Full versions)
  - Pre-built HTML landing page (single file, no host yet)
  - Google Calendar (must not lose events)
  - Outlook client calendar (synced via Cowork)

DOMAINS:
  - freedsolutions.com — primary, full Workspace + website
  - thirdwavecannabis.com — purchase and park only, no setup

GITHUB REPO — RESTRUCTURING REQUIRED:
  I have an existing GitHub repo called FreedSolutions. It was
  originally scoped to a single tool but needs to become the
  general-purpose home for all Freed Solutions work. The repo
  contains three distinct tiers of content that must be clearly
  separated in the folder structure:

  TIER 1 — GLOBAL (shared across all projects)
    Content that belongs to Freed Solutions as a whole, not to
    any specific project or tool. Examples:
      - Landing page HTML (index.html — the website)
      - Brand assets (logo, colors, fonts — if stored in repo)
      - Resumes (.docx files, both versions)
      - README for the repo itself

  TIER 2 — PROJECT: LinkedIn Carousel Generator
    An existing, self-contained tool that was the original purpose
    of this repo. It has its own files, logic, and workflow.
    It should live in its own clearly named project folder and
    not be mixed with global assets or other projects.

  TIER 3 — PROJECT: Freed Solutions Ops & Migration
    New content being added now as part of this migration effort.
    Currently sitting in /Temp and needs a permanent home.
    Includes:
      - PromptA_Domain_Workspace_Hosting.md
      - PromptB_Tools_Assets_Update.md
      - PromptC_Accounts_Audit.md
      - Kickoff_Prompt.md (this file, once migration is underway)
    Future additions to this project will include automation
    scripts (calendar sync, Notion integration, Cowork tasks)
    and any other ops tooling built for internal use.

  STRUCTURAL GOALS:
    1. Propose a folder structure that cleanly separates all
       three tiers and scales to additional projects over time
       without reorganizing from scratch
    2. Move /Temp contents into their correct Tier 3 location
    3. Confirm that permissions are managed at the repo level
       only — not per folder or per file — and flag if anything
       in the current setup needs to change
    4. The landing page HTML (Tier 1 / global) must be positioned
       correctly for GitHub Pages deployment, since that is how
       the site will be hosted

  Please include repo restructuring as a step in Phase A,
  after the domain and Workspace setup is complete.

NOW BEGIN PHASE A:

I need to migrate my professional identity from a personal Gmail
to a custom domain on Google Workspace, and simultaneously get
my landing page website live on that domain.

IDENTITY:
  Current email:   freedsolutions@gmail.com
  Target email:    adam@freedsolutions.com
  Business name:   Freed Solutions (DBA, cannabis fractional consulting)

DOMAINS TO PURCHASE:
  Primary:    freedsolutions.com  (full Workspace setup on this domain)
  Secondary:  thirdwavecannabis.com  (purchase and park only — no
              active setup needed, just IP protection)

WEBSITE:
  I have a pre-built single HTML file (landing page) that I will
  provide. It currently references freedsolutions@gmail.com and has
  no hosted domain yet. I need this deployed at freedsolutions.com.
  Preferred hosting: GitHub Pages (free) or Netlify (free tier).
  I want a clean www.freedsolutions.com URL.

CURRENT STATE:
  - All work tools (Calendly, Notion, Cowork) tied to old Gmail
  - Google Calendar in use — must not lose events
  - Outlook client calendar synced via Cowork tasks
  - No existing domain registrar account

GOALS FOR THIS PHASE:
  1. Purchase freedsolutions.com from a reputable registrar
     (recommend one — I have no preference)
  2. Purchase and park thirdwavecannabis.com (no email, no site)
  3. Set up Google Workspace Starter on freedsolutions.com
  4. Create adam@freedsolutions.com as primary account
  5. Migrate Gmail history, contacts, and calendar to new account
     without losing anything
  6. Set up forwarding from old Gmail so nothing is missed
     during transition
  7. Deploy my HTML landing page to www.freedsolutions.com
     — walk me through the hosting setup step by step
  8. Update the email reference in the HTML from
     freedsolutions@gmail.com to adam@freedsolutions.com
     before deploying
  9. Restructure the FreedSolutions GitHub repo for general use
     — propose folder structure, move /Temp files to their
     permanent home, confirm repo-level permissions

Please walk me through this end-to-end in strict sequential order.
Flag any steps that are irreversible or require waiting (DNS
propagation, etc.) so I can plan my time. I am comfortable in a
terminal and with following technical steps.
```
