# Prompt A — Domain + Google Workspace + Website Hosting

> **When to run:** First. Do not proceed to Prompt B until `adam@freedsolutions.com` is confirmed working.
> **DNS note:** Propagation takes 24–48 hours — plan accordingly.

---

## Paste this into a fresh Claude chat:

```
I need to migrate my professional identity from a personal Gmail to a
custom domain on Google Workspace, and simultaneously get my landing
page website live on that domain. Here is my full context:

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

Please walk me through this end-to-end in strict sequential order.
Flag any steps that are irreversible or require waiting (DNS
propagation, etc.) so I can plan my time. I am comfortable in a
terminal and with following technical steps.
```

---

## What this phase covers

1. Registrar selection and domain purchase (both domains)
2. Google Workspace account creation and DNS verification
3. Gmail history + calendar migration to new account
4. Email forwarding bridge during transition period
5. HTML landing page email reference update
6. Website hosting setup and deployment to freedsolutions.com

---

> ✅ **Done when:** You can send and receive email at `adam@freedsolutions.com` and `www.freedsolutions.com` loads your landing page.
