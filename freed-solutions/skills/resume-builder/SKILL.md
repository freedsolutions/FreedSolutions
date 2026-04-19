---
name: resume-builder
description: Tailor Adam's resume + cover letter + application answers for a specific job opening, using a base resume as the reference-doc for DOCX styling. Use when Adam wants to apply to a role and needs the materials written, tuned to the JD, and rendered to DOCX/PDF.
---

# Resume Builder

Produce tailored resume, cover letter, and application-question answers for a specific job opening. Follow Adam's voice (operator-direct, AI-tell-free), use one of his maintained resume versions as the DOCX style anchor, and place artifacts under `freed-solutions/applications/<company-slug>/`.

## When to Use

- Adam is applying to a specific role. The JD is available as text, URL, or paste.
- Output needed: tailored resume DOCX, optional cover letter DOCX, and paste-ready application-question answers.

## Inputs

- **Base resume** (required): one of `Adam Freed - Resume - 2025 - Fractional.docx`, `... - Full.docx`, or a client/application-specific variant in `C:\Users\adamj\OneDrive\Documents\My Documents\Occupational\Resume\`. Default: Fractional (most recent).
- **Job description** (required): paste from chat, URL, or `.txt` / `.md` path.
- **Company slug** (required): short kebab-case company name (e.g., `theory-wellness`) for the folder.
- **Application questions** (optional): any custom questions the posting requires answers to.
- **Contact preferences** (optional): compensation range, start date, work-auth answers. Default to Adam's canonical values (see Canonical Facts).

If any required input is missing or ambiguous, use `HARDENED_GATE` to ask a compact decision-shaped question.

## Canonical Facts

Adam maintains his canonical contact-info block (name, address, phone, email, age confirmation, education, work-auth, letterhead format) in a local-only file outside this repo. Do not re-ask unless contradicted.

- **Source of truth:** `~/.config/freed-solutions/canonical-facts.md` (gitignored; maintained by Adam).
- **Public identifiers safe to reference in repo:** `adam@freedsolutions.com`, `www.freedsolutions.com`, Freed Solutions company name.

When invoking this skill, read the canonical-facts file at session start and hold the contents in working memory only — never write any element of it (address, phone, DOB, etc.) into a committed file.

## Folder Structure

All artifacts land under `freed-solutions/applications/<company-slug>/`:

| File | Purpose |
|---|---|
| `resume.md` | Tailored resume source (Markdown). Converts to DOCX via pandoc with base-resume as reference-doc. |
| `cover-letter.md` | Cover letter source. Optional but usually included. |
| `application-answers.md` | Paste-ready answers to the posting's custom questions. |

**DOCX outputs** land in Adam's OneDrive resume folder:
- `Adam Freed - Resume - 2025 - <Company>.docx`
- `Adam Freed - Cover Letter - 2025 - <Company>.docx`

## Workflow

### 1. Intake

- Confirm base resume, JD, company slug. If the company has a dedicated folder already, check it for prior tailoring work.
- Check Notion for a wired Action Item linked to the hiring manager Contact. If one exists, the AI's `Task Notes` and `Source Meeting` often contain crucial context (e.g., a prior-manager "interest signal" framing that reshapes the cover letter's tone).
- Read the JD carefully. Identify the Required vs. Preferred bullets, the Application Questions, and the compensation bracket.

### 2. Resume tailoring

- Start from the base resume. Read it end-to-end in plain text via `pandoc <base>.docx -t plain`.
- Adjust the **Profile** headline and paragraph to match the JD's role name and focus. Keep Adam's voice ("Cannabis Operations & IT SME", "Data, Systems & AI Leader", etc. — pick the framing that aligns).
- Update **Core Competencies** to match the JD's skill emphasis while staying honest to Adam's actual strengths. See Voice Rules below for "don't overclaim" guidance.
- Expand the current **Freed Solutions (Fractional)** section with any new client engagements / wins not yet on the base resume. Default structure:
  - Sub-blocks per engagement (format: `*<Client Name> (<Region>) — <Engagement Type>* — <Operator Type>`). Specific client names and engagement terms come from the local `canonical-facts.md` or the caller, not from this skill file.
  - 3-5 tight bullets per engagement.
  - Internal (Freed Solutions) sub-block for personal infra (Notion CRM, Claude Code skill library, etc.).
- Leave earlier roles largely intact. Minor tech-up of verbs OK ("Architected API-driven Dutchie Backoffice integrations" beats "Automated Dutchie Backoffice workflows"). Don't invent scope that wasn't there.
- Preserve chronological structure. Preserve JCHE (entry-level role with measurable impact — $100K saved, 6-month schedule compression).
- Education: add any relevant in-progress certifications or degree exploration (e.g., "Exploring a Master's program in Computer Science (AI specialization)").

### 3. Cover letter

- Letterhead at top (see Canonical Facts).
- Two-beat argument body, Adam's voice:
  - **Beat 1: domain depth.** Name the specific cannabis operators / roles / systems that differentiate Adam from non-cannabis applicants.
  - **Beat 2: current Fractional / AI-paired direction.** Notion CRM + Claude Code + MCP integrations. Honest about "AI-paired builder, not a traditional software engineer."
- If the target is a current or former client Adam has discovery context on, weave in a specific observation from the engagement as proof-of-depth (subject to the Confidentiality rule below).
- Optional closing paragraph: "connective tissue" framing — the role's scope extends Adam's cross-functional strengths beyond the JD's narrow scope as breadth and operational depth build over time.
- Close with openness to alternative structures (Fractional path) if relevant.

### 4. Application-question answers

- Produce `application-answers.md` with the posting's questions verbatim as headers, answers below each.
- Respect character limits (many platforms enforce 1500-char per answer).
- Use specific, quantified examples from Adam's actual career. Specific figures, prior-manager names, and per-engagement savings numbers belong in the local `canonical-facts.md`, not in this skill file. The skill's job is the workflow; the facts come from the local-only source of truth.
  - JCHE: $100K+ saved, 6-month schedule compression on a 200-resident relocation
  - Node Labs: GAS barcode label maker shipped 2021, 4+ years in production, 3x'd label production, zero support calls
  - Current: multi-agent Notion CRM, Claude Code skill library, MCP integrations
- For SQL/Python/cloud questions: lead with the low-code + AI-paired honesty. "Not a traditional software engineer" is a strength signal, not a weakness, when owned directly.
- For compensation: anchor to Adam's stated floor + inflation-adjusted historical rate. Offer a range (e.g., $150K-$160K) to leave negotiation room.

### 5. Voice calibration (AI-tell hunt)

Every answer and every paragraph should be run against these checks before rendering:

| Tell | Frequency threshold | Remedy |
|---|---|---|
| Em dashes (—) in prose | 0 in body text; OK in date ranges / title separators | Replace with periods, commas, parens, colons |
| Enumerated preambles ("Three things...", "Two reasons...") | Avoid | Let the prose flow; use "On prioritization:" or similar transition if needed |
| Triadic rhythm (sentences stacked in threes) | Don't let it dominate | Vary sentence shapes; break into two paragraphs |
| Parallel-structure verb openers ("Built X. Shipped Y. Delivered Z.") | Avoid as a pattern | Mix sentence shapes; some clipped, some longer, some fragments |
| Consultant vocabulary ("connective tissue", "cross-stakeholder convergence", "signal weight") | Use once max, or rephrase | Prefer operator vocabulary: "the link between", "multiple people said the same thing", "how much weight to give" |
| AI-template openers ("To be direct:", "Honest framing up front:") | Replace with Adam's voice | "Straight up:" or just dive in |
| "I bring deep domain knowledge" | Too generic | Replace with specifics or cut |

**Voice model:** Adam's chat voice — direct, practical, qualified, honest about what he doesn't claim. "Juice isn't worth the squeeze" Adam, not "value-driven strategic leader" Adam. Uses contractions freely. Occasional fragments. Parens for asides. Self-effacing about technical skills but confident about operator chops.

### 6. DOCX render

Use pandoc with the base resume as `--reference-doc` to preserve Adam's styling:

```bash
pandoc "freed-solutions/applications/<slug>/resume.md" \
  -o "C:/Users/adamj/OneDrive/Documents/My Documents/Occupational/Resume/Adam Freed - Resume - 2025 - <Company>.docx" \
  --reference-doc="C:/Users/adamj/OneDrive/Documents/My Documents/Occupational/Resume/Adam Freed - Resume - 2025 - Fractional.docx"

pandoc "freed-solutions/applications/<slug>/cover-letter.md" \
  -o "C:/Users/adamj/OneDrive/Documents/My Documents/Occupational/Resume/Adam Freed - Cover Letter - 2025 - <Company>.docx" \
  --reference-doc="C:/Users/adamj/OneDrive/Documents/My Documents/Occupational/Resume/Adam Freed - Resume - 2025 - Fractional.docx"
```

If Word has the target file open, pandoc will fail with "permission denied" — ask Adam to close Word and retry.

Do not commit the rendered DOCX files. Source MD goes in the repo.

### 7. Online submission (optional)

If Adam wants the application submitted through Indeed / LinkedIn / company ATS:
- Use Playwright MCP. Sign-in is Adam's step (his credentials).
- Upload resume DOCX from the OneDrive path. Indeed converts to PDF automatically.
- Fill contact info from Canonical Facts.
- Fill screener questions. Adam reviews before the final submit click.
- Pause for Adam's explicit "submit" confirmation before the final click.

### 8. Closeout

- Update the Notion AI page (if wired) with `⚡ ARTIFACT UPDATE \[YYYY-MM-DD\]` marker describing what landed.
- Suggest tagging `@Follow-Up Agent` on the source Meeting if the application affects the counterparty's related AIs.
- Do not mark `Record Status` outside what the AI page's lifecycle already authorizes (see `GOVERNANCE_GATE` in `ops/notion-workspace/CLAUDE.md`).

## Guardrails

- **Never overclaim.** Adam is a low-code + AI-paired builder. Not a traditional software engineer. Not a data scientist in the strict ML/stats sense. Not a cloud architect. Owning those boundaries on paper is a strength; pretending otherwise will surface in a technical interview.
- **Cannabis depth is the differentiator.** Always foreground Adam's MSO / retail / compliance / operations experience. It's rare in the applicant pool and it's real.
- **Confidentiality.** If Adam is applying to a current client (while an engagement is active), do not cite specific discovery findings in the application text. Generalize or anonymize.
- **Do not modify Adam's canonical base resumes.** Always tailor a copy; leave the base versions in OneDrive untouched.
- **Do not commit rendered DOCX files.** Repo convention: `.md` source in, generated artifacts local only.

## Gate Protocol

| Operation | Gate | Notes |
|---|---|---|
| Draft / tailor resume + cover letter + answers, render DOCX via pandoc, save to OneDrive, place source MD in repo | `UNGATED` | Standard recipe; no external state mutation. |
| Submit application online via Playwright; commit source MD to repo | `UNGATED` after explicit execution request | Still pause for Adam's final "submit" confirmation before the last click. |
| Notion AI page `Status` updates after application completion | `UNGATED` bounded target update | Follow-through after explicit execution request. |
| Modify Adam's canonical base resumes, push to a public profile (LinkedIn, Indeed profile update), or submit without final confirmation | `HARDENED_GATE` | Ask before executing. |
| Schema changes, bulk edits, destructive git operations | `GOVERNANCE_GATE` | Out of scope for this skill. |

## Known Limitations

- The base resume structure is carried through by pandoc via `--reference-doc`, but Word sometimes normalizes certain formatting (bullet spacing, section spacing). Final review in Word is recommended before submission.
- Indeed profiles sometimes prefill contact fields inconsistently — always verify before clicking Continue on the contact-info page.
- Application platforms vary in how they handle character limits (some truncate silently, some block). Keep answers under stated limits with 5-10% buffer.
- FigJam / design tools are not in scope for this skill — resume artifacts are text-first.

## Reference Pattern (generalized)

The first end-to-end exercise of this recipe lives locally under `freed-solutions/applications/<company-slug>/` (gitignored). When working a new application, read the most recent prior folder's three `.md` files for a worked example of voice, structure, and calibration. Notable moves from the canonical first run:

- Base resume: Fractional. Tailored in place with expanded Freed Solutions Mar 2025–Present section broken into engagement sub-blocks plus Internal.
- Core Competencies rewritten from AI-consultant-sounding to honest-operator ("Department Building & Leadership" up top instead of the sexier "Data Infrastructure & BI" framing that overclaimed scope Adam directs but doesn't do himself).
- Cover letter: two-beat argument (domain depth + AI-first current direction), closed with Fractional openness as a phone-call hook.
- Application answers: multiple questions, all trimmed under the platform's character limit with buffer.
- AI-tell pass after initial draft — em dashes removed from prose, triadic rhythms broken up, consultant vocabulary swapped to operator voice.
- Post-submission: Notion AI page Status flipped to Done, final ⚡ marker captured what landed, Indeed profile updated to carry the tailored resume.
