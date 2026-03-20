# Claude.ai Context

<!-- Notion Page ID: 325adb01-222f-8144-9c87-e0412a17d5ef -->

Lightweight planning context for Claude.ai chat sessions.

Local source-of-truth: `docs/claude-ai-context.md` (repo).

Last updated: March 20, 2026

---

# Workspace Context

This workspace is a CRM and operations automation system for **Freed Solutions**.

**Execution model:**
- **Claude Code + Codex skills** are the primary manual execution layer for high-judgment work, local edits, migrations, and verification.
- **Notion Custom Agents** stay focused on narrow scheduled or reactive automation.
- **Claude.ai** is optional planning and review space. It should point execution back to Claude Code or Codex when the task becomes multi-file, high-risk, or workflow-specific.

For Claude Code and Codex work, the canonical handoff is `ops/notion-workspace/session-active.md`. The Notion `Session - Active` page is a lightweight mirror or pointer for chat-only surfaces.

**Owner:** Adam Freed
**Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

---

# Key Pages

| Page | ID | Purpose |
|---|---|---|
| Automation Hub | `321adb01-222f-810f-8706-e53105950d86` | Root page for agent config and instructions |
| Agent SOPs | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model and runtime baseline |
| Session - Active | `323adb01-222f-81f1-bd4b-d0383d39d47a` | Optional pointer or status mirror for the repo handoff |
| Session - Archive | `323adb01-222f-81dd-a175-c17d8fd8c71a` | Legacy session history |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | Runtime timestamps and state markers |
| Post-Meeting Instructions | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent |
| Curated Notes Instructions | `325adb01-222f-8148-b544-f592271f34e3` | Manual-only QA reviewer |
| Contact & Company Instructions | `323adb01-222f-8126-9db8-df77be5a326f` | Contact and company enrichment |
| Post-Email Instructions | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent |
| Delete Unwiring Instructions | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Delete unwiring workflow |

---

# Database Quick Reference

| Database | Data Source ID |
|---|---|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` |

**Record Status**: Draft -> Active -> Inactive -> Delete
**Calendar Name** live options: `Adam - Business`, `Adam - Personal`

---

# Agent Registry

| Agent | Trigger | Status |
|---|---|---|
| Post-Meeting Agent | Nightly 10 PM ET + Record Status -> Active + manual | Live |
| Post-Email Agent | Nightly about 10:30 PM ET + manual | Live |
| Contact & Company Agent | Nightly 11 PM ET + manual | Live |
| Delete Unwiring Agent | Record Status -> Delete across 5 DBs + manual | Live |
| Curated Notes Agent | Manual `@mention` only | Live - QA reviewer |

**Model baseline:** Opus 4.6

---

# Codex Skills

Use the repo skill sources under `ops/notion-workspace/skills/` when planning hands off to manual execution:

- `notion-action-item`
- `notion-agent-config`
- `notion-agent-test`

These skills are published to `~/.codex/skills` from `ops/notion-workspace/scripts/publish-codex-skills.ps1`.

---

# Rules of Engagement (Chat Mode)

1. Read the repo handoff first when it is available in the current surface. Otherwise use the Notion `Session - Active` page as a mirror and hand execution back to Claude Code or Codex.
2. Plan by default, but hand off execution to Claude Code or Codex skills when the task becomes implementation-heavy.
3. Treat `CLAUDE.md`, `docs/agent-sops.md`, and the workflow docs as the authoritative local sources.
4. Do not assume a Claude.ai-only slash command or planning skill is available.
5. Pause only for ambiguity, destructive work, schema changes, lifecycle changes, new DB record creation, or migration/bulk work.
6. Never change `Record Status` without explicit instruction.
7. Fetch instruction pages on demand when discussing a specific agent.
8. Tag any remaining browser-only work as `Adam - UI step` unless it is fully executed and verified in the same task.
9. For doc changes, Claude Code should push mapped docs, verify parity, run the Codex review gate, and only then update the session log.

**Good Claude.ai tasks**
- Review plans
- Compare workflow options
- Draft instruction-page content
- Analyze runtime drift or schema proposals

**Push to Claude Code or Codex**
- Multi-file repo edits
- Codex skill updates
- Bulk Notion operations
- Browser-driven agent config changes
- Regression testing and review-gated sync work

---

# Local Docs -> Notion Mapping

| Local File | Notion Page ID | Notes |
|---|---|---|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent instructions |
| `docs/curated-notes.md` | `325adb01-222f-8148-b544-f592271f34e3` | Curated Notes QA reviewer |
| `docs/delete-unwiring.md` | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Delete Unwiring instructions |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company instructions |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker CRM profile |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email instructions |
| `docs/notion-agent.md` | `321adb01-222f-8033-ad89-c3f889ae4dec` | Supporting mirror only |
| `docs/claude-ai-context.md` | `325adb01-222f-8144-9c87-e0412a17d5ef` | This file |

Local docs are the source of truth. Push changes to Notion after editing locally.
