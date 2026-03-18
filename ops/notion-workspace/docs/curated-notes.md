<!-- Notion Page ID: 325adb01-222f-8148-b544-f592271f34e3 -->

# Curated Notes Instructions — DEPRECATED

**Deprecated as of Session 57 (March 18, 2026).**

The Curated Notes Agent has been folded into the **Post-Meeting Agent as Step 4**. See `docs/post-meeting.md` for the current instructions.

## Why deprecated

- The Post-Meeting Agent now triggers on Record Status → Active (same trigger Curated Notes used).
- Folding Step 4 into the Post-Meeting pipeline guarantees ordering (Steps 1–3 complete before curation) and eliminates the race condition where both agents fired on the same trigger.
- The Curated Notes Agent in Notion UI should be **disabled but not deleted** (available for rollback).

## Where the logic moved

All guard rails, content generation (TL;DR, Decisions, Action Items Final, Key Discussion Points), block writing, and idempotency (📋 sentinel) are now in Post-Meeting Instructions → Step 4: Curated Notes.

## Historical reference

The original Curated Notes instructions (pre-S57) are preserved in git history for this file.
