# CRM-Optimized Meeting Notetaker

Last synced: Session 51 (March 16, 2026)

**Type:** Notion Calendar AI Notetaker Profile
**Status:** Active — Session 38 (March 15, 2026), updated Session 39 (source reference format)
**Purpose:** Produce structured meeting summaries optimized for the Post-Meeting Agent's parsing pipeline and Floppy voice-command surfacing.

## Input Channels

The AI notetaker processes two input channels that influence the summary output:

- **Voice commands** — "Hey Floppy" spoken during the meeting appears in the transcript. The notetaker surfaces these as `(Floppy)`-prefixed Action Items (Layer 1). The Post-Meeting Agent also parses them independently from the raw transcript (Layer 2).
- **Typed notes** — Notes typed directly into Notion Calendar's notetaker panel during the meeting. These are treated as first-party input alongside the transcript, giving Adam a second channel to drive prescriptive Action Items without speaking aloud.

Both channels feed into the same `### Action Items` section of the AI summary, which the Post-Meeting Agent parses in Steps 2.0–2.4.

---

## How to Apply

Open the **AI Meeting Notes summary instructions** page in Notion Calendar and fill in each section as shown below. The page title should be **"CRM-Optimized"**.

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

The Post-Meeting Agent (see [post-meeting.md](post-meeting.md)) parses the `### Action Items` heading to extract checklist items. It expects:

- `- [ ]` markdown checklist format (rendered as Notion `to_do` blocks)
- Person names that match Contacts DB records (first name, full name, or nickname)
- Source references in brackets — both `[HH:MM:SS]` timestamps (voice) and `[Notes]` tags (typed notes) are valid formats, stripped during parsing
- Clear imperative voice for the action

The `(Floppy)` prefix serves **Layer 1** of the Floppy design (see [floppy-design.md](floppy-design.md)): by telling the notetaker to explicitly surface "Hey Floppy" commands, the AI summary already reflects Adam's voice commands before the Post-Meeting Agent's independent transcript parse (Layer 2) even runs. This makes the AI summary more prescriptive and the downstream Draft items faster to approve.

## Notetaker Profiles Roadmap

This is the first notetaker profile (**CRM-optimized**). Future profiles for different meeting types:

| Profile | Use Case | Status |
|---------|----------|--------|
| **CRM-Optimized** (this doc) | Default for all business meetings. Structured for Post-Meeting Agent parsing. | Active |
| **Strategy / Workshop** | Longer brainstorm or planning sessions. Heavier on topic summaries, lighter on action items. | Planned |
| **1:1 / Check-in** | Quick syncs. Minimal structure, focus on decisions and follow-ups. | Planned |

Each profile will be a separate doc with its own instruction text, registered in agent-sops.md.
