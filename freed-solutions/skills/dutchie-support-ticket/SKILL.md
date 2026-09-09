---
name: dutchie-support-ticket
description: Draft Dutchie support tickets — potential bugs and product feedback — routed to the right queue (possupport@ for Backoffice, support@ for Ecom/Pro/Kiosk) with the header block triage needs. Fast by default — it writes up what Adam already caught, it does not investigate. Use when a Dutchie defect or feature gap surfaces and Adam wants it filed or parked.
---

# Dutchie Support Ticket

Turn something Adam noticed into an email Dutchie can act on. Output is always a **Gmail draft Adam
reviews and sends**, plus a short local record — never an autonomous send.

## Default: fast

**Write up what Adam stated. Do not investigate past it.** No root-cause hunt, no hypothesis
ladder, no trip through the support site.

Go deeper only when Adam says so ("dig", "find out why"), or when Dutchie replies asking for
something the ticket did not carry. A thin ticket that draws a clarifying reply is a cheap outcome;
an hour of investigation before the first send is not.

## When to use

A Dutchie behavior looks wrong, or a gap has no workaround, and Adam says file it / ticket it /
park it. Also for draining the parked queue at session close.

**Not** for BI content Adam owns — a tile calc, a filter mapping — that is `dutchie-bi-looker`, not
a Dutchie defect. **Not** for dead data: a real defect on a zero-sales, zero-inventory SKU is a
note, not a ticket.

## Lane

| | Potential Bug | Product Feedback |
|---|---|---|
| **Trigger** | Does something it shouldn't, or fails what it claims | Works as designed; the design is wrong or incomplete |
| **Subject** | `Bug \| [Shorthand]` | `Product Feedback \| [Shorthand]` |
| **Body head** | `Description of Issue:` | `Product Feedback:` |
| **Header** | Full | Timestamp + User only |
| **CC** | the client alias — this is what auto-labels the thread, so not optional | none; feedback is not a client thread |

The subject prefix is the **lane, not the client**. The header block and the CC already pin the
client, so a client tag in the subject is redundant.

**"Potential" is load-bearing.** We may be wrong, or the behavior may be intended. Write bugs so
that a "this is expected" reply is a *useful* answer: state what you expected, so their reply either
fixes the bug or teaches the rule.

## Queue

| Surface | URL | Send to | `Server Name:` |
|---|---|---|---|
| Backoffice (formerly LeafLogix) | `<server>.backoffice.dutchie.com` | `possupport@dutchie.com` | **required** |
| Dutchie Ecom | `admin.dutchie.com` | `support@dutchie.com` | **omit — not applicable** |
| Dutchie Pro (tied to the website) | client site | `support@dutchie.com` | omit |
| Dutchie Kiosk (in-store, mimics Ecom) | in-store device | `support@dutchie.com` | omit |

Pro and Kiosk hang off the Ecom product, so those three are one queue. An issue spanning Backoffice
and Ecom (a catalog attribute that fails to reach the menu) files to **Backoffice**, naming the Ecom
symptom in the body — the data originates there.

## Header block

Use only the fields the ticket needs. An unused field is noise, not thoroughness.

```
Server Name:   <Backoffice tickets only>
LSP Name:
Location Name:
Timestamp:     <when it happened; now if not incident-specific>
User Name:     <Adam's Dutchie login>
```

These values are client canon and never live in this skill. They live in a `## Dutchie Ticket
Routing` block in the gitignored CLAUDE.md of the tenant folder named in the client pointer block:
server, LSP, location(s), Dutchie login, ticket CC, and which surfaces the tenant runs. If a value
is missing or still a placeholder, ask Adam for that one value and write it back into the block.
Capture once, reuse forever.

## Workflow

1. **Route.** Lane and queue from the tables above. If the surface is unclear, ask which URL Adam
   was on — the URL decides the queue, not the topic.
2. **KB check (bugs only, one file).** Read `dutchie-bi-looker/references/dutchie-platform-kb.md`; a
   `[DOC]` or `[PROBE]` entry may settle the lane. That is the whole check. Do not open
   support.dutchie.com unless Adam asks — and if he does, use the browser, since it 403s plain
   fetchers. Record what the entry said, or that there was none.
3. **Client context.** Read the routing block; fill any gap per above.
4. **Draft.** Three required fields, and nothing derived beyond them:
   - **Identifiers** — SKU, product name, batch / package / order / dashboard id. Verbatim.
   - **Expected vs Actual** — two lines. This is what makes it triageable.
   - **One repro path** — numbered, from a known URL.

   Five optional fields — scope, reproducibility, first observed, impact, workaround — go in **only
   if Adam already said them**. Never go looking for them.
5. **Gmail draft.** `mcp__google-workspace__gmail_createDraft`, To and CC per routing, From
   `adam@freedsolutions.com`. **Never send.** Report it back and say plainly that it is a draft.

Screenshots: attach when they help, and narrate what each shows. Their first-response AI cannot read
images, so an image-only evidence ticket bounces off the automated layer.

## The record — 25 lines, hard cap

A receipt, not a case file:

```
# <lane> — <shorthand>
Lane / queue / date / Gmail draft id / Status: DRAFT — not sent
KB: <entry, or "none">

<the email, verbatim>
```

Bugs go in the `tickets/` folder of the tenant folder named in the client pointer block. Product
feedback goes in the shared Dutchie tickets folder, which sits outside every client tree. **Both are
gitignored and must stay that way** — feedback is client-agnostic in its framing but routinely cites
client evidence (SKU counts, brand coverage, sales figures).

Analysis that will not fit belongs in the client estate, not here. When Dutchie replies, append
`Dutchie ref: <id>` — one line. The directory listing is the ledger; Gmail labels carry status.

> Pending a Phase B pass: the two record locations collapse into one, with lane as a field.

## Parking mid-session

Bugs surface during other work and chasing them derails the session. Don't. Append one line to
`QUEUE.md` in that tenant's `tickets/` folder and keep working:

```markdown
- [ ] YYYY-MM-DD | Backoffice | <observation> | ids: <SKU/PID/tile> | evidence: <path or none>
```

Enough to reconstruct the observation; full detail is gathered at draft time. Existing entries in
that file run longer than this — leave them alone until the Phase B pass.

## Spawning a drafting session

`spawn_task` works well here, with one constraint: a task worktree has no client tree, so every read
*and* write path in the prompt must be an absolute path into the main checkout, and the prompt must
say not to create a client tree inside the worktree. Give it the observation, the tenant, the lane,
and the surface.

## House style

- **TL;DR body.** Bullets over paragraphs, short subject. Dutchie triage skims.
- **Report, don't diagnose.** At most one `Our read:` line, and only when Adam offered the read. A
  paragraph of speculation invites them to argue with the theory instead of reproducing the bug.
- **No hedging in the observation.** "Potential" lives in the framing, not in every sentence.
- **One issue per ticket.** Two symptoms with one suspected cause are still two tickets unless they
  share a reproduction path.
- **Verbatim identifiers.** Names, SKUs and error strings copied exactly — no cleanup, no smart quotes.

## Template: Potential Bug

```text
Subject: Bug | [Shorthand]

Server Name: <server>
LSP Name: <lsp>
Location Name: <location>
Timestamp: <when observed>
User Name: <login>

Description of Issue:
- SKU / Product Name / <Batch|Package|Order|Dashboard id as applicable>

Steps to reproduce:
1. <from a known URL>
2. ...

Expected: <what should happen, and why we expect it>
Actual: <what happens instead>

<Optional, only if already known: Scope / Reproducibility / First observed / Impact / Workaround>
<Screenshot narration if images attached>
```

## Template: Product Feedback

```text
Subject: Product Feedback | [Shorthand]

Timestamp: <now>
User Name: <login>

Product Feedback:
- Surface: <Backoffice module / Ecom area>

Current behavior: <what it does today>
Desired behavior: <what it should do>
Why: <the job this blocks — operator workflow, not a feature wish>

<Optional, only if already known: Workaround and its cost / who else this affects>
```

## References

- `dutchie-bi-looker/references/dutchie-platform-kb.md` — the one KB to check, step 2.
- The tenant's `## Dutchie Ticket Routing` block — header values and the CC.
- Live chat: Backoffice top-right `?` → **Live chat** → modal bottom-right (may default to the last
  thread). First layer is a bot. Manual, and Adam's call — worth it when a quick "is this expected?"
  settles the lane faster than an email round-trip.
