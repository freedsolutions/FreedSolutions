---
name: dutchie-support-ticket
description: Draft Dutchie support tickets — potential bugs and product feedback — routed to the right queue (possupport@ for Backoffice, support@ for Ecom/Pro/Kiosk), with the header block and repro detail Dutchie triage needs. Use when a Dutchie defect or feature gap surfaces and Adam wants it filed or parked.
---

<!-- Generated from "freed-solutions/skills/dutchie-support-ticket/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Dutchie Support Ticket

Turn a defect or feature gap observed during client work into a ticket Dutchie support can act on
without a round-trip. Two lanes (potential bug / product feedback), two queues (Backoffice / Ecom),
one header grammar. Output is always a **Gmail draft Adam reviews and sends** plus a local record —
never an autonomous send.

## When to Use

- A Dutchie behavior looks wrong mid-session (BI, MDM, catalog, inventory, ecom) and it's worth filing.
- Adam says "file that", "ticket that", "send this to Dutchie", "park that for a ticket".
- A workaround has been found for a Dutchie limitation and the underlying gap should be on record.
- Batch-drafting the parked queue at session close.

## When NOT to Use

- The behavior is documented as designed — check the KB first (step 2). That converts a bug into
  product feedback, or into nothing.
- The issue is in Looker/BI *content Adam owns* (a tile calc, a filter mapping). That's
  `dutchie-bi-looker`, not a Dutchie defect.
- Dead data with no business impact. A real UI defect on a zero-sales, zero-inventory SKU is not
  worth a ticket; note it and move on.

## Inputs

- **Observation** (required): what happened, on what surface, with the identifiers that pin it down.
- **Client slug** (required for bugs; N/A for product feedback): drives the header block and the CC.
  Product feedback is client-agnostic by design.
- **Lane** (optional): bug vs product feedback. Infer it; confirm only when genuinely 50/50.
- **Evidence** (optional): screenshots, API responses, export rows, dashboard IDs.

If the client slug is missing on a bug ticket, ask. Everything else is inferable or gatherable.

## Lane Decision

| | Potential Bug | Product Feedback |
|---|---|---|
| **Trigger** | System does something it shouldn't, or fails to do what it claims | System works as designed, but the design is wrong or incomplete |
| **Scope** | Tied to one client tenant | General across any client |
| **Subject** | `Bug \| [Bug Shorthand]` | `Product Feedback \| [Feedback Shorthand]` |
| **Body head** | `Description of Issue:` | `Product Feedback:` |
| **Header block** | Full (Server/LSP/Location/Timestamp/User) | Minimal (Timestamp/User) — no tenant fields |

**"Potential" is load-bearing.** A bug is called potential for two reasons: (1) we may be wrong, and
(2) the behavior may be the designed intention — in which case the ticket converts to product
feedback. Write bugs so that a "this is expected behavior" reply is a *useful* answer, not a dead
end: state what you expected and why, so their reply either fixes it or teaches us the rule.

## Queue Routing

| Surface | URL | Send to | `Server Name:` |
|---|---|---|---|
| Backoffice (formerly LeafLogix) | `<server>.backoffice.dutchie.com` | `possupport@dutchie.com` | **required** |
| Dutchie Ecom | `admin.dutchie.com` | `support@dutchie.com` | **omit — not applicable** |
| Dutchie Pro (tied to the website) | client site | `support@dutchie.com` | omit |
| Dutchie Kiosk (in-store, mimics Ecom) | in-store device | `support@dutchie.com` | omit |

Ecom / Pro / Kiosk are one queue — `support@dutchie.com` — because Pro and Kiosk hang off the Ecom
product. If an issue spans both Backoffice and Ecom (e.g. a catalog attribute that fails to
propagate to the menu), file to **Backoffice** and name the Ecom symptom in the body; the data
originates there.

## Subject Grammar

**The prefix is the LANE, not the client** — `Bug | ...` and `Product Feedback | ...`. Ruled by Adam
2026-08-30, matching his existing sent tickets (reqs 692030, 692041). The client is already pinned
by the header block and the CC, so a client tag in the subject is redundant; the lane is the thing
triage needs at a glance. Do not put a client shorthand in the subject.

## Addressing

- **From:** `adam@freedsolutions.com` (canonical outbound).
- **CC:** the client-side alias from that client's routing block. The CC is what makes Adam's Gmail
  filters auto-label the thread by *both* Dutchie and client — it is the tracking mechanism, so it
  is not optional on a bug ticket.
- Product feedback has no client CC (it isn't a client thread).

## Per-Client Routing Block

Header values are client canon and **never live in this skill** (`freed-solutions/` is committed;
client identifiers are not). They live in the gitignored per-client context file:

`clients/<slug>/CLAUDE.md` → a `## Dutchie Ticket Routing` section:

```markdown
## Dutchie Ticket Routing
- Server Name: <prefix from <prefix>.backoffice.dutchie.com>
- LSP Name: <LSP as it appears in Backoffice>
- Location Name(s): <store name(s) exactly as named in Dutchie>
- Dutchie login (User Name): <the email Adam's Backoffice seat uses>
- Ticket CC: <client-side alias for Gmail auto-labeling>
- Surfaces in use: Backoffice | Ecom | Pro | Kiosk
```

If the block is missing, or a field the ticket needs still holds a `<...>` placeholder, ask Adam for
that one value and **write it back into the block** before drafting. Capture once, reuse forever.

## Header Grammar

Use only the fields the ticket actually needs — an unused field is noise, not thoroughness.

```
Server Name:      <required for possupport@ only>
LSP Name:         <client-specific>
Location Name:    <client-specific>
Timestamp:        <when the incident occurred; NOW if not incident-specific>
User Name:        <Adam's login, unless filing on behalf of a named user>

Description of Issue:      (bugs)
  - SKU / Product Name / Batch ID / Package ID / Order # / Dashboard ID — whatever pins it
  - ...

Product Feedback:          (feedback)
```

Identifier sub-bullets go **at the top of the description section**, before the prose. Triage reads
top-down and needs the handle before the story.

## Workflow

### 1. Classify and route

Pick the lane and the queue from the tables above. If the surface is ambiguous, ask which URL Adam
was on — the URL decides the queue, not the topic.

### 2. KB pre-check (bugs only)

Search `support.dutchie.com` for the behavior before calling it a bug.

- The site **403s plain fetchers — read it through the browser**, not WebFetch.
- If an article says the behavior is intended, switch lanes to Product Feedback and cite the article.
- If an article documents different behavior than observed, cite it in the ticket — a doc-vs-reality
  contradiction is the strongest bug evidence there is.
- Record the article URL + read date in the local record either way.

Then check `freed-solutions/skills/dutchie-bi-looker/references/dutchie-platform-kb.md` — a
`[DOC]`/`[PROBE]` entry may already settle it.

### 3. Load client context

Read `clients/<slug>/CLAUDE.md` → `## Dutchie Ticket Routing`. Fill gaps per above.

### 4. Gather the specifics

Every ticket needs enough for Dutchie to reproduce on their side:

- **Identifiers** — SKU, Product Name, Batch ID, Package ID, Order #, Dashboard/Tile ID, whatever applies.
- **Steps to reproduce** — numbered, from a known starting URL.
- **Expected vs Actual** — two lines. This is what turns "it's broken" into a triageable report.
- **Scope / blast radius** — one SKU or a class? one location or all? one user or every seat?
- **Reproducibility** — consistent / intermittent / one-time. Say which.
- **First observed** — when it started, if known, and whether it followed a Dutchie release or a
  change on our side.
- **Business impact** — what's blocked and what it costs. Drives their priority.
- **Current workaround** — if one exists, state it *and* its cost. "No workaround" is also a fact
  worth stating.

### 5. Draft

Fill the matching template below. Then re-read it as if you were Dutchie support with no context:
can they reproduce it from the body alone? If not, the gap is in step 4.

### 6. Screenshots

Attach them when they help, but **their AI first-responder cannot read images**. Every screenshot
must have a text equivalent in the body — narrate what it shows. A ticket whose evidence is
image-only will bounce off the automated layer.

### 7. Create the Gmail draft

`mcp__google-workspace__gmail_createDraft` — To per routing, CC per routing, From
`adam@freedsolutions.com`. **Never send.** Adam reviews and sends. Report the draft back and say
plainly that it is a draft.

### 8. Save the local record

- Bug: `clients/<slug>/tickets/YYYY-MM-DD-<bug-slug>.md`
- Product feedback: `freed-solutions/dutchie-tickets/YYYY-MM-DD-<feedback-slug>.md`

**Both paths are gitignored, and must stay that way.** `clients/` is ignored wholesale;
`freed-solutions/dutchie-tickets/` has its own `.gitignore` entry because the rest of
`freed-solutions/` is committed. Product-feedback tickets are client-agnostic in their *framing*
but routinely cite client data as evidence — SKU counts, brand coverage, sales figures — so the
record never belongs in a tracked path.

Body = the drafted text, plus a short header block: lane, queue, KB articles checked, evidence
paths. The directory listing is the ledger — no separate tracker, since the Gmail labels carry
thread status. When Dutchie replies with a ticket number, append `Dutchie ref: <id>` to the file.

## Parking a Ticket Mid-Session

Bugs surface during BI/MDM work and chasing them derails the session. Don't. Append one line to
`clients/<slug>/tickets/QUEUE.md` and keep working:

```markdown
- [ ] 2026-08-29 | Backoffice | <one-line observation> | ids: <SKU/PID/tile> | evidence: <path or "none">
```

Drain the queue at session close or in a spawned session (below). A parked line only needs enough
to reconstruct the observation — full detail is gathered at draft time.

## Spawning a Ticket-Drafting Session

Ticket drafting is a clean unit of work to spin out. Use `spawn_task` with a prompt that stands alone.

**Critical:** task-chip worktrees do NOT contain `clients/` (gitignored), so a spawned session
cannot see client canon through a relative path. Every path in the spawn prompt — reads *and*
writes — must be an **absolute path into the main checkout**
(`C:\Users\adamj\Code\FreedSolutions\...`), and the prompt must say not to create a local
`clients\` tree.

Spawn prompt template:

```text
Draft a Dutchie support ticket using the `dutchie-support-ticket` skill.

Observation: <one paragraph — what was seen, on what surface, with identifiers>
Client slug: <slug>   Lane: <bug|product feedback>   Surface: <Backoffice|Ecom|Pro|Kiosk>

Read client routing from the MAIN CHECKOUT (absolute paths only; this worktree has no clients/):
  C:\Users\adamj\Code\FreedSolutions\clients\<slug>\CLAUDE.md
Evidence: <absolute paths>
Write the record to:
  C:\Users\adamj\Code\FreedSolutions\clients\<slug>\tickets\<YYYY-MM-DD>-<slug>.md
Do NOT create a clients\ directory inside this worktree.

Run the KB pre-check through the browser (support.dutchie.com 403s plain fetchers).
Create the Gmail draft — do not send. Report the draft and the record path back.
```

## House Style Notes

- **TL;DR body.** Minimum words, bullets over paragraphs, short subject lines. Dutchie triage skims.
- **Report, don't diagnose.** State observed behavior and expected behavior. A single "our read:"
  line offering a hypothesis is fine and often helps; a paragraph of speculation invites them to
  argue with the theory instead of reproducing the bug.
- **No hedging in the observation.** "Potential" lives in the framing, not in every sentence. Say
  what happened flatly, then say what you expected.
- **One issue per ticket.** Two symptoms with one suspected cause are still two tickets unless they
  share a reproduction path.
- **Verbatim identifiers.** Product names, SKUs, and error strings copied exactly — no cleanup, no
  paraphrase, no smart quotes.

## Template: Potential Bug

```text
Subject: Bug | [Bug Shorthand]

Server Name: <server>
LSP Name: <lsp>
Location Name: <location>
Timestamp: <when observed>
User Name: <login>

Description of Issue:
- SKU: <...>
- Product Name: <...>
- <Batch/Package/Order/Dashboard ID as applicable>

Steps to reproduce:
1. <from a known URL>
2. ...

Expected: <what should happen, and why we expect it>
Actual: <what happens instead>

Scope: <one SKU / a class / all locations>
Reproducibility: <consistent | intermittent | one-time>
First observed: <date, and any correlating change>
Impact: <what is blocked, and the cost>
Workaround: <the workaround and its cost, or "none">

<Screenshot narration if images attached>
```

## Template: Product Feedback

```text
Subject: Product Feedback | [Feedback Shorthand]

Timestamp: <now>
User Name: <login>

Product Feedback:
- Surface: <Backoffice module / Ecom area>
- <identifiers if the example is concrete>

Current behavior: <what the product does today>
Desired behavior: <what it should do>
Why: <the job this blocks — operator workflow, not a feature wish>

Workaround today: <what we do instead, and its cost per week/month>
Who this affects: <roles / how general — this is what makes it product feedback>
```

## References

- `freed-solutions/skills/dutchie-bi-looker/` — BI/Looker mechanics; its
  `references/dutchie-platform-kb.md` holds `[DOC]`/`[PROBE]` platform-behavior facts and the
  support-article source list. Check it in step 2 before filing.
- `clients/<slug>/CLAUDE.md` → `## Dutchie Ticket Routing` — the per-client header values.
- Dutchie KB: `support.dutchie.com` (browser only — 403s plain fetchers).
- Live chat: Backoffice top-right `?` → **Live chat** → modal bottom-right (may default to the last
  thread). First layer is a bot. Manual step; use it when a quick "is this expected?" would settle
  the lane faster than an email round-trip, then file with what it told you.
