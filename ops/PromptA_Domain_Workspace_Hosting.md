# Prompt A — Domain + Google Workspace + Website Hosting

> **Status: PARTIALLY COMPLETE** — Domain and hosting are live. Google Workspace setup is the remaining blocker.
> **When to run:** First. Do not proceed to Prompt B until `adam@freedsolutions.com` is confirmed working.
> **DNS note:** Propagation takes 24–48 hours — plan accordingly.

---

## Remaining: Google Workspace + Gmail Migration

```
I need to finish setting up my professional email identity. Domain
and website are already live — this covers only Google Workspace
setup and the Gmail migration.

IDENTITY:
  Current email:   freedsolutions@gmail.com
  Target email:    adam@freedsolutions.com
  Business name:   Freed Solutions (DBA, cannabis fractional consulting)

ALREADY COMPLETE (do not redo):
  - freedsolutions.com purchased and DNS configured
  - thirdwavecannabis.com purchased and parked
  - Landing page live at www.freedsolutions.com (GitHub Pages)
  - CTA links to Calendly booking (not email)
  - Repo restructured (multi-project layout)

CURRENT STATE:
  - All work tools (Calendly, Notion, Cowork) still tied to old Gmail
  - Google Calendar in use — must not lose events
  - Outlook client calendar synced via Cowork tasks

GOALS FOR THIS PHASE:
  1. Set up Google Workspace Starter on freedsolutions.com
  2. Create adam@freedsolutions.com as primary account
  3. Migrate Gmail history, contacts, and calendar to new account
     without losing anything
  4. Set up forwarding from old Gmail so nothing is missed
     during transition

Please walk me through this end-to-end in strict sequential order.
Flag any steps that are irreversible or require waiting (DNS
propagation, etc.) so I can plan my time. I am comfortable in a
terminal and with following technical steps.
```

---

## What this phase covers

1. ✅ Registrar selection and domain purchase (both domains)
2. ❌ Google Workspace account creation and DNS verification
3. ❌ Gmail history + calendar migration to new account (blocked on #2)
4. ❌ Email forwarding bridge during transition period (blocked on #2)
5. ✅ HTML landing page email reference update (CTA now links to Calendly)
6. ✅ Website hosting setup and deployment to freedsolutions.com (GitHub Pages)
7. ✅ Repo restructured (commit `81ecf22`)

---

> **Done when:** You can send and receive email at `adam@freedsolutions.com` and `www.freedsolutions.com` loads your landing page.
> **Remaining:** Google Workspace setup (#2), then Gmail migration (#3) and forwarding (#4) can proceed.
