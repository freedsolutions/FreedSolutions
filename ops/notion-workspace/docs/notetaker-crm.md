# Notetaker CRM

Last synced: Session 56 (March 18, 2026)

**Type:** Notion Calendar AI Notetaker Profile
**Status:** Active — Session 38 (March 15, 2026), updated Session 39 (source reference format)
**Purpose:** Produce structured meeting summaries optimized for the Post-Meeting Agent's parsing pipeline and Floppy voice-command surfacing.

## Input Channels

Action Items are **human-driven**. The Post-Meeting Agent does NOT mine the transcript for AI-inferred action items. There are exactly two canonical sources:

- **Typed notes (primary)** — Notes typed directly into Notion Calendar's notetaker panel during the meeting. Every non-Floppy line Adam types is treated as a candidate action item by the Post-Meeting Agent (Step 2.1). This is the primary input channel — Adam types what matters, and the agent captures it.
- **Voice commands (secondary)** — "Hey Floppy" spoken during the meeting appears in the transcript. The notetaker surfaces these as `(Floppy)`-prefixed Action Items (Layer 1). The Post-Meeting Agent also parses them independently from the raw transcript (Layer 2 — Step 2.0).

The **transcript** is a conversation record only — used for TL;DR summary (Step 3) and Floppy voice command extraction, but NOT mined for action items. This eliminates AI-inferred noise and puts Adam in control of what becomes an Action Item.

---

## How to Apply

Open the **AI Meeting Notes summary instructions** page in Notion Calendar and fill in each section as shown below. The page title should be **"Notetaker CRM"**.

Notion's template has four sections: Context, Summary format (with named section blocks), and Summary style. The content below maps directly to those sections.

---

## Context

> This is a CRM-optimized notetaker for business meetings. The summary will be parsed by an automated Post-Meeting Agent that creates action items, wires CRM contacts, and syncs back to Google Calendar. The meeting host is Adam. Structure output precisely as described below.

---

## Summary format

### Section 1: Action Items

> This is the most important section. Always place it first. Format every action item as a markdown checklist item: `- [ ] [Person name] to [action] [source reference]`. Lead with the person's name (first name as spoken). Use imperative voice: "send", "review", "schedule" — not "will send". Include deadlines when mentioned. One item per line — never combine two actions. Include source references in brackets. Do not editorialize — capture commitments, not hypotheticals. If the speaker assigns something to themselves, use their name explicitly, never "I" or "me".
>
> CRITICAL — "Hey Floppy" commands (voice AND typed notes): Adam may say "Hey Floppy" (or "Hey, Floppy", "A Floppy", "Hey Floppi") followed by a command, or type "Hey Floppy" followed by a command in the Notes panel. These are the highest-priority items. Always include them as Action Items. Preserve Adam's exact wording. Place Floppy items FIRST in the list. Prefix with "(Floppy)": `- [ ] (Floppy) Adam to send Jake the ConnectNexus docs [00:14:23]`. For items sourced from typed notes rather than voice, use `[Notes]` as the source reference instead of a timestamp: `- [ ] (Floppy) Adam to write LinkedIn post discussing the Dime podcast episode [Notes]`. If a Floppy command overlaps with an organically discussed item, keep both — the downstream agent handles dedup.
>
> END-OF-MEETING RECAP: When the meeting is nearing its end (final 2-3 minutes, or when participants begin wrapping up), prompt Adam with a brief recap: "Before we wrap — any action items to capture?" This gives Adam a last chance to type or speak any remaining items. The Post-Meeting Agent parses typed Notes directly, so anything Adam types at this point becomes a candidate Action Item automatically.

### Section 2: Key Decisions

> Only include decisions that were explicitly agreed upon during the meeting. Format: `- [Decision statement] [source reference]`. If a Floppy command implies a decision was made, consider noting it here. If no decisions were made, omit this section entirely — do not include an empty heading.

### Section 3: Discussion Topics

> After Action Items and Key Decisions, organize remaining discussion into topic headings. Use clear, descriptive topic names. Keep summary points concise — 1-2 sentences each. Include source references for traceability. Use full names on first mention (e.g., "Jake Gleeson"), then first names after. Attribute statements to speakers when identifiable — never use "the team" or "participants".

---

## Summary style

> - Prefer bulleted lists over paragraphs
> - No separate "Summary" or "Overview" paragraph — topic headings serve this purpose
> - No attendee lists — the CRM agent handles this from calendar data
> - No timestamps in body text (only in source reference brackets)
> - No filler like "The meeting began with..." or "The group discussed..."
> - Concise, information-dense — every word serves a purpose

---

## Why This Format

The Post-Meeting Agent (see [post-meeting.md](post-meeting.md)) uses a **human-driven model** for Action Items:

1. **Typed Notes (primary):** The agent parses ALL non-Floppy content from the Notes panel (Step 2.1). Every line Adam types becomes a candidate Action Item. The AI summary's `### Action Items` heading still captures Floppy items (Layer 1) but is no longer mined for AI-inferred items.
2. **Floppy commands (secondary):** The `(Floppy)` prefix serves Layer 1 of the Floppy design — the AI summary surfaces "Hey Floppy" commands as structured `to_do` blocks. The Post-Meeting Agent reads these (Step 2.0 Source 1) and also independently parses the transcript (Layer 2).
3. **Transcript:** Conversation record only — used for TL;DR summary and Floppy voice command extraction. NOT mined for action items.

This means the notetaker's Action Items section is primarily a reflection of what Adam typed and spoke via Floppy — not AI-inferred commitments. The downstream agent trusts Adam's input over AI interpretation.

## Notetaker Profiles Roadmap

This is the first notetaker profile (**Notetaker CRM**). Future profiles for different meeting types:

| Profile | Use Case | Status |
|---------|----------|--------|
| **Notetaker CRM** (this doc) | Default for all business meetings. Structured for Post-Meeting Agent parsing. | Active |
| **Strategy / Workshop** | Longer brainstorm or planning sessions. Heavier on topic summaries, lighter on action items. | Planned |
| **1:1 / Check-in** | Quick syncs. Minimal structure, focus on decisions and follow-ups. | Planned |

Each profile will be a separate doc with its own instruction text, registered in agent-sops.md.
