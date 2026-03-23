# Floppy: Voice-Command CRM Agent

**Status:** Implemented — Session 37b (March 15, 2026), updated Session 39 (typed notes channel, summary-first parsing)
**Integration point:** Post-Meeting Agent, Step 2.0 (before AI summary parsing)

---

## 1. Concept & Integration Point

### The problem

The AI-generated meeting summary produces action items, but they aren't prescriptive enough. The Post-Meeting Agent parses what the AI gives it — if the AI's Action Items heading is vague or misses nuance, the resulting Draft items require heavy editing during Adam's review. This slows the Draft → Active approval cycle and weakens the Step 3 GCal TL;DR.

### What Floppy does

Floppy lets Adam **shape the meeting record in real-time** through two input channels during meetings. This has a **layered effect**:

1. **Layer 1 — AI summary influence.** Voice commands appear in the raw transcript and typed notes appear in the notetaker Notes panel. The AI summarizer picks up both channels and reflects them in its Action Items heading as `(Floppy)`-prefixed items — often more accurately than from organic conversation alone. Floppy commands act as anchors that steer the AI's own output.

2. **Layer 2 — Direct agent parsing.** The Post-Meeting Agent reads `(Floppy)`-prefixed items from the AI summary as the primary extraction path, then scans the notes block and transcript as fallback layers. This catches cases where the AI rephrased, consolidated, or dropped a command. The agent's Floppy parse is the authoritative version.

**The combined result:** Better AI summaries (Layer 1) + explicit multi-source parsing (Layer 2) = more prescriptive Draft items → faster approval → sharper GCal TL;DR. Adam shapes the entire downstream chain by speaking or typing a few sentences during the meeting.

### Input Channels

Floppy supports two input channels. Both use the "Hey Floppy" prefix to signal intent.

| Channel | How it works | Advantages | Limitations |
|---------|-------------|------------|-------------|
| **Voice** | Adam says "Hey Floppy" followed by a command during the meeting. Appears in the raw transcript. | Natural, fast, no context-switching from conversation. | Subject to STT transcription errors; no rich text or links; requires speaking aloud (not ideal in large group calls). |
| **Typed notes** | Adam types "Hey Floppy" followed by a command in Notion Calendar's notetaker Notes panel. | Supports rich text with hyperlinks, precise formatting, dates, and references. Silent operation — works in large group calls without interrupting. No STT ambiguity. | Requires switching to the Notes panel; can't be done while actively speaking. |

Both channels feed into the same `### Action Items` section of the AI summary (Layer 1), and the Post-Meeting Agent processes both in Step 2.0 (Layer 2).

### Where it runs

Floppy parsing is **Step 2.0** — a sub-step before AI summary parsing:

```
Step 1:   CRM Wiring (Contacts, Companies, Series, Calendar Name)
Step 2.0: Floppy Command Parsing (summary-first, notes + transcript fallback)
Step 2.1: AI Summary Action Item Parsing (non-Floppy items only)
Step 2.2: Group Related Action Items (Floppy items excluded from grouping;
          AI items that duplicate Floppy items are skipped)
Step 2.3: Route to Action Items DB
Step 2.4: Wire Back to Meeting (includes Floppy + AI items)
Step 3:   GCal Event Sync-Back (Floppy items serve as anchor points for TL;DR)
```

**Why before AI parsing:** Floppy items are the higher-confidence signal. By creating them first, Step 2.2 can compare AI-parsed items against existing Floppy items and skip duplicates. The Floppy version wins because it reflects Adam's exact intent, not the AI's interpretation.

### Step 3 anchor point role

Floppy commands signal what mattered most in a meeting. When Step 3 composes the GCal TL;DR and Key Decisions, it should **weight Floppy-sourced items higher** than AI-only items. Specifically:

- Floppy Tasks/Follow Ups appear first in the Action Items list
- If a Floppy command implies a decision was made (contextual — e.g., "Hey Floppy, remind me to send Jake the revised proposal" implies the proposal revision was decided), the agent should consider surfacing that in the Key Decisions section
- The TL;DR narrative should reference Floppy-anchored outcomes over AI-inferred ones when they overlap

---

## 2. Trigger Phrase Detection

### Primary trigger

The canonical trigger is **"Hey Floppy"** — either spoken by Adam during a meeting (appears in transcript) or typed in the Notion Calendar notetaker Notes panel. The phrase was chosen because it's distinctive enough to avoid false positives in normal conversation and memorable enough to become habitual.

**For typed notes:** The trigger is an exact text match — "Hey Floppy" at the start of a paragraph. No STT variants or regex needed.

**For voice (transcript):** STT variants must be matched (see below).

### STT variants to match (voice/transcript only)

Speech-to-text engines produce inconsistent transcriptions. The parser must match all of these (case-insensitive):

| Pattern | Example transcript text |
|---------|------------------------|
| `hey floppy` | "Hey Floppy, remind me to..." |
| `hey, floppy` | "Hey, Floppy, I need to..." |
| `hey floppy,` | "Hey Floppy, follow up with..." |
| `a floppy` | "A Floppy remind me to send..." (common STT error) |
| `hey floppi` | Phonetic spelling variant |
| `hey flop` | Truncated (less confident — flag for review) |

**Regex pattern (initial):**
```
(?i)\b(?:hey[,\s]+floppy|a\s+floppy|hey\s+flop(?:py|pi|p)?)\b[,:\s]*
```

This pattern is intentionally permissive. False positives are acceptable — they surface as Draft items for Adam to review and delete. False negatives (missed commands) are worse because Adam thinks the command was captured.

### Speaker attribution

If the transcript includes speaker labels (e.g., `Adam:`, `Speaker 1:`), only parse "Hey Floppy" utterances from Adam's segments. If speaker labels are absent or unreliable, parse all instances — Adam is the only person who would say "Hey Floppy" in his meetings.

### STT calibration (future)

The first few meetings with Floppy will reveal how Notion Calendar's STT engine actually transcribes "Hey Floppy." The regex should be updated based on real transcript data. If the STT consistently produces a specific variant (e.g., always "hey, Floppy" with a comma), the pattern can be tightened.

---

## 3. Supported Commands

Floppy supports five command types. Adam's phrasing will vary between direct commands and conversational speech — the parser must handle both styles.

### 3.1: Create Task

An action item assigned to Adam. Expected to be the most common command.

**Signal words:** "remind me", "I need to", "I should", "don't let me forget", "task", "to-do", "action item"

**Direct style:**
- "Hey Floppy, remind me to send Jake the ConnectNexus docs"
- "Hey Floppy, action item: prep the Surfside deck before next Wednesday"

**Conversational style:**
- "Hey Floppy, I need to remember to loop in Morgan on the rebrand timeline"
- "Hey Floppy, I should probably put together that proposal for Eric before our next call"

**Result:** Action Item with Assignee = Adam → Type auto-computes to "Task"

### 3.2: Create Follow Up

An action item tracking someone else's deliverable. No Assignee → Type = "Follow Up".

**Signal words:** "follow up with", "waiting on", "check if", "they need to", "ask [name] to", "[name] is going to", "[name] said they'd"

**Direct style:**
- "Hey Floppy, follow up with Eric on the Surfside report"
- "Hey Floppy, waiting on Matt for the Deep Roots proposal"

**Conversational style:**
- "Hey Floppy, Jake said he'd send the API migration timeline by end of week"
- "Hey Floppy, I think Morgan was going to circle back on the budget numbers"

**Result:** Action Item with Assignee blank → Type auto-computes to "Follow Up"

### 3.3: Add Contact Note

Append information to a Contact's notes in the Contacts DB.

**Signal words:** "note for [name]", "remember that [name]", "[name] mentioned", "about [name]"

**Examples:**
- "Hey Floppy, note for Jake: he's moving to the Denver office in April"
- "Hey Floppy, remember that Eric prefers async communication over meetings"
- "Hey Floppy, Matt mentioned he's taking PTO the last two weeks of April"

**Result:** Append to the matched Contact's **Contact Notes** field. Format: `[YYYY-MM-DD] (via Floppy) [note text]`

### 3.4: Add Company Note

Append information to a Company's notes in the Companies DB.

**Signal words:** "note for [company]", "about [company]", "[company] is", "[company] announced"

**Examples:**
- "Hey Floppy, note for Dutchie: they're sunsetting their old API in Q3"
- "Hey Floppy, Surfside is launching a new attribution product next month"
- "Hey Floppy, note for Deep Roots: budget freeze until May"

**Result:** Append to the matched Company's **Company Notes** field. Format: `[YYYY-MM-DD] (via Floppy) [note text]`

### 3.5: Set Priority / Due Date (inline modifier)

Not a standalone command — this is metadata attached to a Task or Follow Up command.

**Priority signals:** "high priority", "urgent", "important", "ASAP", "critical"
**Due date signals:** "by [date]", "before [date]", "due [date]", "this week", "next Monday", "end of week", "EOD"

**Examples:**
- "Hey Floppy, high priority: get the Surfside deck to Josh by Friday"
- "Hey Floppy, urgent — follow up with Jake on the contract before end of week"
- "Hey Floppy, I need to send the proposal to Eric by next Tuesday"

**Result:** Sets Priority = "High" (if priority signal detected) and/or Due Date (resolved to absolute date using the meeting date as reference). Default priority remains "Low" when no signal is detected.

---

## 4. Parsing Rules

Floppy parsing follows a three-stage pipeline: **detect → classify → extract**.

### Stage 1: Detect

Detection uses three sources in priority order (see post-meeting.md Step 2.0.1 for full details):

1. **AI Summary (primary):** Read `(Floppy)`-prefixed `to_do` blocks from the summary. These are already clean and structured.
2. **Notes block (fallback):** Scan typed note paragraphs for "Hey Floppy" prefix (exact match). Capture any not already in the summary.
3. **Transcript (fallback):** Scan for trigger phrase regex matches (Section 2). Capture any not already found in summary or notes.

For transcript matches, capture from the trigger phrase to the command boundary (Section 5). This produces a list of raw command strings.

### Stage 2: Classify (Intent)

Determine which command type (Section 3) each raw command represents. Classification uses signal word matching with a priority order:

1. **Contact Note** — if the command contains "note for [name]" or "remember that [name]" patterns
2. **Company Note** — if the command contains "note for [company]" or "about [company]" patterns where the entity resolves to a Company (not a Contact)
3. **Follow Up** — if the command contains follow-up signal words or references someone else as the actor
4. **Task** — default. If no other type matches, treat it as a Task for Adam.

The priority order resolves ambiguity: "Hey Floppy, note for Jake to send the docs" is a Contact Note, because "note for [name]" is checked first.

**Ambiguous fallback:** If classification is genuinely unclear, default to Task. Adam would rather review and reclassify than miss something — consistent with existing Step 2 ambiguity handling.

### Stage 3: Extract (Entities & Properties)

From the classified command, extract:

| Field | Extraction method |
|-------|-------------------|
| **Action/Content** | The core instruction, stripped of trigger phrase and signal words. Clean into concise imperative voice. |
| **Contact name** | Named entity after "for", "with", "to", or as the subject/object of the action. First name, full name, or nickname. |
| **Company name** | Named entity after "for", "about", or contextually referenced. May be inferred from the Contact's Company. |
| **Priority** | "high priority", "urgent", "important", "ASAP", "critical" → High. Absent → Low (default). |
| **Due date** | Relative dates resolved against the meeting date. "Friday" → next Friday from meeting date. "end of week" → Friday. "next Tuesday" → the Tuesday after the meeting. |
| **Transcript timestamp** | The timestamp marker (e.g., `[00:14:23]`) nearest to the trigger phrase, if available. Stored in Task Notes for traceability. |

---

## 5. Command Boundary Detection

**Typed notes:** Boundary detection is trivial — each paragraph in the Notes panel is a discrete command. No further boundary logic needed.

**Voice commands (transcript):** The hardest parsing problem — where does a Floppy command end in a continuous transcript?

### Boundary signals (in priority order, transcript only)

1. **Next trigger phrase** — another "Hey Floppy" starts a new command.
2. **Speaker change** — a different speaker starts talking (if speaker labels are present).
3. **Topic pivot** — Adam shifts to a different subject without Floppy context. Detected by:
   - Addressing another person directly (e.g., "So Morgan, about the...")
   - Asking a question unrelated to the command
   - Returning to a prior discussion thread
4. **Sentence boundary after complete thought** — if the command forms a grammatically complete instruction, end there. Don't absorb follow-on conversation.
5. **Maximum length cap** — 150 words from the trigger phrase. Any command longer than this is likely absorbing unrelated speech. Truncate and flag for review.

### Practical heuristic

Most Floppy commands will be 1-2 sentences. The parser should aggressively favor short extraction:

- Capture the first complete sentence after the trigger phrase.
- If the next sentence is clearly a continuation (starts with "and also", "plus", "oh and"), include it.
- Otherwise, stop.

When in doubt, capture less. A slightly truncated command in Task Notes is better than a command polluted with unrelated meeting conversation.

---

## 6. Contact & Company Resolution

### Contact resolution

Floppy must resolve spoken names to Contacts DB records. Resolution follows a two-tier approach:

**Tier 1: Meeting Contacts (preferred)**
Search the meeting's existing Contacts relation (wired in Step 1) for a match by:
- First name (case-insensitive): "Jake" → Jake Gleeson
- Full name: "Jake Gleeson" → exact match
- Nickname (from Nickname field): "Gigi" → Eugenia Philip
- Last name (if unambiguous among meeting contacts): "Gleeson" → Jake Gleeson

**Tier 2: Full Contacts DB (fallback)**
If Tier 1 fails, search the entire Contacts DB. This is broader than AI action item parsing (which only uses meeting Contacts) because Floppy commands are explicit intent — Adam may reference someone not in the meeting.

- Same matching rules: first name, full name, nickname, last name
- If multiple matches, prefer Active records over Draft
- If still ambiguous, leave Contact blank and flag in Task Notes: "Ambiguous contact: '[name]' matches [list]. Manual wiring required."

**Why two tiers:** Tier 1 is faster and more precise (smaller search space, higher confidence). Tier 2 catches cross-meeting references like "Hey Floppy, remind me to send the deck to Ted" where Ted Reynolds isn't in this meeting.

### Company resolution

**From Contact:** If a Contact is resolved, look up their Company relation in the Contacts DB. Wire the same Company to the Action Item (consistent with existing Step 2.3 rules).

**Direct reference:** For Company Note commands, match the spoken company name against:
1. Company Name (title) in the Companies DB — case-insensitive, partial match allowed ("Dutchie" matches "Dutchie")
2. If ambiguous or no match, flag in Company Notes append: "Unresolved company: '[name]'. Manual verification required."

**No new records:** Floppy never creates new Contacts or Companies. Contact/company creation is exclusively Step 1's job (from GCal attendee emails). If a name can't be resolved, the item is created with blank Contact/Company and flagged.

---

## 7. CRM Property Mapping

### Task / Follow Up → Action Items DB

| Property | Task (Assignee = Adam) | Follow Up (Assignee blank) |
|----------|----------------------|---------------------------|
| Task Name | Concise imperative from extracted action | Description of what needs to happen |
| Status | "Not started" | "Not started" |
| Priority | "High" if priority signal detected, else "Low" | "High" if priority signal detected, else blank |
| Record Status | "Draft" | "Draft" |
| Task Notes | See format below | See format below |
| Due Date | Resolved absolute date, or blank | Resolved absolute date, or blank |
| Contact | Resolved Contact, or blank | Resolved Contact, or blank |
| Company | From Contact's Company, or blank | From Contact's Company, or blank |
| Source Meeting | Wire to source meeting page | Wire to source meeting page |
| Assignee | Adam Freed (`30cd872b-594c-81b7-99dc-0002af0f255a`) | Leave blank |

**Task Notes format for Floppy items:**

Voice commands (from transcript):
```
Source: Voice command (Hey Floppy)
Transcript: "[raw command text from transcript]"
Timestamp: [HH:MM:SS] (if available)
From: [Meeting Title] on [Date]
```

Typed notes (from notetaker Notes panel):
```
Source: Typed note (Hey Floppy)
Content: "[typed note text]"
Link: [URL if hyperlink present in rich text]
From: [Meeting Title] on [Date]
```

The `Source:` tag (either variant) distinguishes Floppy items from AI-parsed items. The `(Hey Floppy)` substring is the canonical identifier used by:
- **Step 2.2** to exclude Floppy items from grouping and to skip duplicate AI items
- **Step 3** to identify anchor points for the GCal TL;DR
- **Adam** to quickly identify Floppy items during Draft review and distinguish voice vs. typed origin

### Contact Note → Contacts DB

| Field | Value |
|-------|-------|
| Target | Contact Notes (text field) on the resolved Contact |
| Operation | **Append** (never overwrite existing notes) |
| Format | `[YYYY-MM-DD] (via Floppy, [Meeting Title]) [note text]` |

If Contact Notes already has content, append with a newline separator.

### Company Note → Companies DB

| Field | Value |
|-------|-------|
| Target | Company Notes (text field) on the resolved Company |
| Operation | **Append** (never overwrite existing notes) |
| Format | `[YYYY-MM-DD] (via Floppy, [Meeting Title]) [note text]` |

If Company Notes already has content, append with a newline separator.

---

## 8. Deduplication with AI Summary (Layered Reconciliation)

Floppy commands influence the meeting record at two layers. The dedup logic must account for both.

### Layer 1: AI summary already reflects Floppy

Because Floppy commands are spoken into the meeting, the AI summarizer often includes them in its Action Items heading — sometimes verbatim, sometimes rephrased. This means the AI summary is already better than it would be without Floppy. No agent action needed for this layer — it happens naturally.

### Layer 2: Agent reconciliation

The agent parses Floppy commands from the summary, notes block, and transcript (Step 2.0), then parses non-Floppy AI items from the summary (Step 2.1). Reconciliation happens in Step 2.2:

1. Read all Floppy items created in Step 2.0 (identified by `(Hey Floppy)` substring in the Task Notes `Source:` line).
2. For each AI-parsed action item candidate, check if a Floppy item already covers the same deliverable (fuzzy match on Task Name + Contact).
3. **If a match is found:** Skip the AI-parsed item — the Floppy version is more prescriptive. Log: "AI item '[title]' skipped — covered by Floppy command."
4. **If no match:** Process the AI item normally (group, route, wire).

**Floppy items are never grouped, merged, or modified** by Step 2.2. They represent Adam's exact words and pass through to the Action Items DB as-is.

### Why Floppy wins over AI

The AI summary is an interpretation. Floppy is explicit intent. When they overlap:
- Floppy's Task Name is what Adam actually said → more prescriptive
- Floppy's Contact resolution uses the spoken name → more accurate
- Floppy's priority/due date is what Adam specified → not inferred

### Contact/Company Notes are exempt

Contact Notes and Company Notes from Floppy don't overlap with AI parsing — Step 2.1 only produces Action Items, not DB note appends. No dedup needed.

---

## 9. Error Handling

| Scenario | Behavior |
|----------|----------|
| **Trigger detected but no parseable command** | Log warning: "Floppy trigger at [timestamp] but no command extracted." Skip. |
| **Unrecognized command type** | Default to Task. Flag in Task Notes: "Command type unclear — defaulted to Task." |
| **Contact name not resolved** | Create the item with blank Contact. Flag in Task Notes: "Unresolved contact: '[name]'. Manual wiring required." |
| **Company name not resolved** (for Company Note) | Do NOT append to any Company Notes. Instead, create a Task for Adam: "Review Floppy company note: [note text]. Could not resolve '[company name]'." |
| **Due date unparseable** | Leave Due Date blank. Include the raw date text in Task Notes: "Mentioned deadline: '[raw text]' — could not resolve to date." |
| **Duplicate trigger** (same command repeated in transcript) | If two triggers produce identical Task Name + Contact within the same meeting, keep only the first. Log: "Duplicate Floppy command skipped." |
| **Page has no `transcription` block** | Skip Floppy parsing entirely. Log: "No transcription block found — Floppy parsing skipped." Step 2.1+ proceeds normally. |
| **150-word cap reached** | Truncate command text. Flag in Task Notes: "Command truncated at 150-word limit — review for completeness." |

### Non-blocking principle

Floppy errors must never block the rest of Step 2. If Floppy parsing fails entirely (e.g., malformed transcript), log the error and continue with Step 2.1 (AI summary parsing). The meeting still gets its AI-parsed action items — Floppy is an enhancement layer, not a dependency.

---

## 10. Output in Post-Meeting Agent Summary

Add a **Step 2.0** section to the existing Output Summary format:

```
**Step 2.0 (Floppy Commands):**
- Meetings with Floppy commands: [count]
- Commands detected: [count] (voice: [count], typed: [count], summary-only: [count])
- Tasks created: [count]
- Follow Ups created: [count]
- Contact Notes appended: [count]
- Company Notes appended: [count]
- AI items skipped (covered by Floppy): [count]
- Commands skipped (unparseable): [count]
- Commands skipped (duplicate): [count]
- Unresolved contacts (left blank): [count]
- Unresolved companies (created as Task): [count]
- Transcript fallback commands (not in AI summary): [count]
```

This section appears between Step 1 and Step 2 in the output, matching execution order. The "AI items skipped" line specifically tracks the Layer 2 reconciliation — how many AI-parsed items were suppressed because Floppy already covered them.

---

## Design Constraints Summary

- **No new DB properties or schema changes** — uses existing Action Items, Contacts, Companies DB fields
- **No new Contacts or Companies created** — contact/company creation is exclusively Step 1's job
- **Record Status = Draft** on all Floppy-created Action Items — keeps the review gate, but items should be more prescriptive and faster to approve
- **Append-only for notes** — Contact Notes and Company Notes are never overwritten
- **Non-blocking** — Floppy failures don't prevent AI summary parsing
- **Layered, not replacing** — Floppy enhances the AI summary (Layer 1) and provides independent parsing (Layer 2). It doesn't replace the AI summary pipeline.

---

## Adoption & Calibration

Floppy is a new speaking behavior for Adam. The first few meetings will be a calibration period:

1. **Start with Tasks only.** Use "Hey Floppy, remind me to..." in 2-3 meetings. Review the Draft output to see how the STT transcribes "Hey Floppy" and whether the parser extracts correctly.
2. **Expand to Follow Ups.** Add "Hey Floppy, follow up with..." once Task parsing is reliable.
3. **Add Contact/Company Notes.** These require accurate name resolution — add after the contact matching path is proven.
4. **Tune the regex.** After 5-10 meetings with real transcript data, tighten or adjust the trigger pattern based on actual STT output.
5. **Measure Draft approval rate.** Track whether Floppy-sourced items get approved faster (fewer edits) than AI-only items. This is the core success metric.

---

## Open Questions for Future Sessions

1. **Multi-command in one utterance:** "Hey Floppy, remind me to send Jake the docs and follow up with Eric on the report" — treat as one command or two? (v1: one command. Split detection is a v2 enhancement.)
2. **Floppy for non-meeting contexts:** Could Floppy work outside of meeting transcripts (e.g., voice memos, Slack messages)? (Out of scope — meeting transcript only for now.)
3. **Real-time acknowledgment:** Should Adam get feedback that Floppy captured a command? (Currently post-processed only. A future Slack/notification integration could confirm captures.)
4. **STT custom vocabulary:** If Notion Calendar's STT engine supports custom vocabulary, "Floppy" should be added to improve recognition accuracy.
5. ~~**Floppy as a prompt for the AI summarizer:**~~ **Resolved (S38).** The Notetaker CRM profile (`notetaker-crm.md`) explicitly instructs the AI to surface "Hey Floppy" commands as `(Floppy)`-prefixed Action Items. This strengthens Layer 1 and is now the primary extraction source for Step 2.0.
