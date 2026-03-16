# Session 43B — Meetings DB Hardening (Claude Code Prompt)

> **Interface:** Claude Code (VSCode terminal with Notion MCP access)
> **Prerequisite:** Read `CLAUDE.md`, then fetch Session — Active (`323adb01-222f-81f1-bd4b-d0383d39d47a`).
> **Context:** This prompt runs AFTER `session-43-claude-code-prompt.md` Tasks 1–3 are complete. Some items were already done in the S43 chat session (noted below).

---

## Already Done (S43 Chat — do NOT repeat)

- 5 Series Parents set to Record Status = Active, Calendar Name = "Adam - Business"
- `Series Status` rollup added to Meetings DB (pulls Record Status from Series relation via `show_original`)
- Phone normalization (4 contacts + agent docs)

---

## Task A: Rename Created Date → Created Timestamp (3 DBs)

### What
Rename the `Created Date` property to `Created Timestamp` on these 3 databases. Do NOT rename on Action Items DB.

| Database | Data Source ID |
|----------|---------------|
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |

### Steps
1. Use `notion-update-data-source` with `RENAME COLUMN "Created Date" TO "Created Timestamp"` on each DB.
2. Change the display format to **MM/DD/YYYY** with **12-hour time** included (this is a Notion UI property setting — apply via the data source schema if available, otherwise note it for Adam to set manually in Notion UI).
3. Verify each rename by fetching the data source and confirming the property name change.

### Doc Updates
After renaming:
1. **`docs/agent-sops.md`** — Update all 3 Schema Conventions sections (Contacts, Companies, Meetings) to say `Created Timestamp` instead of `Created Date`. Keep the Action Items section as `Created Date` (unchanged).
2. **`docs/unified-post-meeting.md`** — Search for any references to `Created Date` on Contacts, Companies, or Meetings and update to `Created Timestamp`.
3. **`docs/contact-company-review.md`** — Same search-and-replace.
4. **`docs/merge-workflow.md`** — Same search-and-replace.
5. **`CLAUDE.md`** — Update the Key Schema Conventions section if `Created Date` is mentioned for these 3 DBs.
6. **Push all changed docs to their mapped Notion pages** and verify.

---

## Task B: Backfill NULL Record Status → Active

### What
Find all Meetings DB pages where `Record Status` is NULL/empty and set them to `Active`. These are older meetings created before the Record Status migration (S32) or pages that the notetaker created without setting the property.

### Steps
1. Query the Meetings DB for pages where Record Status is empty/NULL. Count them.
2. Present the count and a sample (first 5 titles) for confirmation.
3. After confirmation, batch update all NULL records to `Record Status = "Active"`.
4. Verify by re-querying — zero NULLs remaining.

**Note:** Series Parents were already set to Active in the chat session. This task catches remaining instances and one-off meetings.

---

## Task C: Meetings DB QC Formula — Series Parent Carve-Out

### What
Extend the Meetings DB QC formula so that when `Is Series Parent = true`, the formula always returns `"TRUE"` (skip all field checks). Series Parents will never have Calendar Event ID, Calendar Name, Date, etc. — they are reference records, not real meetings.

### Logic
```
if Is Series Parent = true → "TRUE"
else if Record Status = "Delete" → wired:X checks (from Task 1B)
else → existing missing:fieldname checks
```

### Steps
1. Fetch the current Meetings QC formula.
2. Add the Series Parent carve-out as the first check.
3. Push the updated formula.
4. Verify by fetching a Series Parent — QC should show `"TRUE"`.

---

## Task D: Series View + View Filtering

### What
1. **Create a "Series" view** in the Meetings DB filtered on `Is Series Parent = checked`. This is where Adam manages Series Parents.
2. **Update all other Meetings DB views** to exclude Series Parents by adding `Is Series Parent ≠ checked` to their filters.
3. **Update working views** (Active, Weekly, Upcoming, etc.) to also filter `Series Status ≠ "Inactive"` — this implements the cascade inactivation via rollup. When a Series Parent is set to Inactive, all its instances disappear from working views automatically.

### Steps
1. Fetch the Meetings DB to see all current views.
2. Create the "Series" view with filter: `Is Series Parent = checked`. Show properties: Meeting Title, Calendar Name, Record Status, Instances, Location.
3. For each existing view, add filter: `Is Series Parent ≠ checked`.
4. For working views (Active, Weekly, Upcoming, Today — NOT Draft, Fix, Delete, All), also add: `Series Status ≠ "Inactive"`.
5. Verify by checking that Series Parents no longer appear in normal views but show in the Series view.

---

## Task E: Fill Missing Location from GCal

### What
For existing Meetings DB pages that have a Calendar Event ID but empty Location, fetch the GCal event and backfill the Location property if the event has a `location` field.

### Steps
1. Query the Meetings DB for pages where Location is empty AND Calendar Event ID is not empty AND Is Series Parent is unchecked.
2. Count the results. If more than 50, process in batches of 25.
3. For each page, use `gcal_get_event` to fetch the event details.
4. If the GCal event has a `location` field, update the Meetings DB page's Location property.
5. If the GCal event has no location or returns 404 (deleted event), skip.
6. Report: "[X] locations backfilled, [Y] events had no location, [Z] events not found."

**Note:** Series Parents already have Location in their page content (manually entered). This task only backfills instances that got their Location from GCal during creation but may have been missed.

---

## Task F: Companies Rollup Verification

### What
The Meetings DB already has a `Companies` rollup property. Verify it's working correctly — it should pull unique Company names from the Contacts relation (Contacts → Company → Company Name).

### Steps
1. Fetch the Meetings DB data source and inspect the `Companies` rollup configuration.
2. Pick 2-3 meetings with known Contacts (e.g., meetings with Primitiv contacts should show "Primitiv" in Companies).
3. Fetch those meetings and confirm the Companies rollup shows the expected values.
4. If the rollup is misconfigured or showing duplicates, fix the rollup formula. If it's showing unique companies correctly, log "Companies rollup verified — working as expected."

---

## Task G: Documentation Updates

After all tasks above are complete, ensure these docs reflect all Meetings DB changes:

1. **`docs/agent-sops.md`** — Meetings DB Properties section:
   - Add `Series Status` (rollup) — pulls Record Status from Series Parent
   - Update `Created Date` → `Created Timestamp` (if not already done in Task A)
   - Note the QC carve-out for Series Parents
   - Note the `Series Status` view filtering behavior (instances of inactive series hidden from working views)
2. **`docs/notion-agent-config.md`** — Update Memories section with Meetings DB hardening (S43).
3. **Push all changed docs to Notion** and verify.
4. **Commit all local changes to main.**

---

## End-of-Session Protocol

**IMPORTANT: Simplified protocol (effective S43).** The Archive page no longer gets detailed per-session entries. The new protocol is:

1. **System Evolution Arc** — Append a one-liner to the Arc section of Session — Archive (`323adb01-222f-81dd-a175-c17d8fd8c71a`).
2. **Snapshot** — Duplicate the Active page → move the duplicate as a child page under Session — Archive.
3. **Overwrite Active** — Replace Session — Active (`323adb01-222f-81f1-bd4b-d0383d39d47a`) with the Session 44 handoff below.

**DO NOT write a detailed session entry in the Archive page.** The snapshot IS the detailed record.

Also update `docs/agent-sops.md` End-of-Session Protocol section to reflect this simplified flow (3 steps, not 4).

### Session 43 Summary (for Active page overwrite)

**Date:** March 16, 2026
**Focus:** QC formula enhancements (past_due + delete wiring), Delete Unwiring Agent (instruction page), EAG → Formul8 merge, Meetings DB hardening (Series Status rollup, Created Timestamp rename, NULL Record Status backfill, Series view + QC carve-out, Location backfill), phone normalization, system governance planning.

**S43 Chat session:**
- Phone normalization: 4 contacts fixed to `(XXX) XXX-XXXX`, rule added to agent-sops + all 3 agent docs
- Series Parents: 5 pages set to Record Status = Active, Calendar Name = "Adam - Business"
- Series Status rollup added to Meetings DB (pulls Record Status from Series relation)
- Parked items captured: QC rules, Delete Unwiring Agent, Merge Agent, Calendar Expansion, domain logic
- S44 priorities locked, archive protocol simplified

**S43 Claude Code session (main prompt — Tasks 1-3):**
- Task 1: QC formula enhancements (past_due on Action Items, wired:X on all 4 DBs for Delete records)
- Task 2: Delete Unwiring Agent instruction page created, registered in Agent Registry + CLAUDE.md
- Task 3: EAG → Formul8 merge executed, Primary vs Additional Domains rules added to merge-workflow.md

**S43b Claude Code session (Meetings DB — Tasks A-G):**
- Task A: Created Date → Created Timestamp (3 DBs renamed, display format updated)
- Task B: NULL Record Status backfilled to Active
- Task C: QC formula — Series Parent carve-out (always TRUE when Is Series Parent)
- Task D: Series view created, all other views exclude Series Parents, working views filter Series Status ≠ Inactive
- Task E: Missing Location backfilled from GCal
- Task F: Companies rollup verified
- Task G: All docs updated and pushed

### Session 44 Priorities

#### Priority 1 — Full Agent Audit + Trigger Config
Single pass across all agents, automations, and Notion configs to verify everything is correctly wired after S43 changes:
- **Post-Meeting Agent:** Verify triggers (nightly 10 PM ET + reactive on Meeting Title), instruction page matches local `unified-post-meeting.md`, all DB references current, QC formula changes reflected
- **Contact & Company Review:** Verify instruction page matches local doc, DB references current
- **Delete Unwiring Agent:** (NEW from S43) Configure Notion DB automation triggers on all 4 DBs — fire when Record Status → Delete. Test with a dummy record.
- **Deprecated agents:** Confirm Meeting Sync, Post-Meeting Wiring, Quick Sync triggers are still disabled
- **Agent Config DB:** Verify Last Successful Run is current, all config rows accurate
- **Notion Agent page** (`notion-agent-config.md`): Verify Active agents list, Memories section, Workspace Context all reflect S43 changes
- **Merge Workflow:** Review `docs/merge-workflow.md` — process may have shifted. Update if needed.

#### Priority 2 — Curated Notes Agent
- Verify Adam's updated MD doc against `docs/curated-notes-design.md`
- If complete: build instruction page, register in Agent Registry, configure trigger
- If gaps remain: identify and resolve in design discussion

#### Priority 3 — System Governance Documentation
Create two new docs:
- **`docs/system-architecture.md`** — Where every artifact type lives (Notion vs. repo), sync rules, directory structure conventions, the manual copy/paste constraint, known Notion dependencies
- **`docs/migration-readiness.md`** — Maps each Notion Agent → Claude Code equivalent, each Notion instruction page → local doc, each automation trigger → external trigger mechanism, what's portable today vs. needs new tooling

Additional governance work:
- Move deprecated docs (`meeting-sync.md`, `quick-sync.md`, `post-meeting-wiring.md`) to `docs/archive/`
- Create `docs/design/` for Floppy + Curated Notes design docs
- Update `CLAUDE.md` to reflect new directory structure
- Update `docs/agent-sops.md` with simplified End-of-Session Protocol (Arc + snapshot, no detailed entries)
- Clean up the Archive page (one-time tidy)

#### Priority 4 — Incremental Config Extraction (Ongoing)
As agents get touched in future sessions, extract hardcoded business rules into structured config files (`configs/` directory). Start with easiest wins: email exclude lists, Series Registry, QC required fields. Not a big-bang migration — let it happen naturally.

#### Parked
- Automation: Merge Agent (checkbox-triggered merge flow in Action Items)
- Additional notetaker profiles (Strategy/Workshop, 1:1/Check-in)
- Multi-source Action Items (email, voice memos — not just meetings)
- Additional Calendar Expansion (second calendar + hardened Calendar Name)
- QC: Past Due view cleanup (remove manual OR filter — now baked into QC formula)
- Series inactivation cascade (Option 2 — agent-based cascade, if rollup approach proves insufficient)
- Full repo-first YAML migration (trigger: Notion token costs become material, or Cowork gets native triggers)

### System Status (Post-Session 43)

- **Post-Meeting Agent:** LIVE. Nightly 10 PM ET + reactive trigger. Notetaker + Floppy tested (S43).
- **Delete Unwiring Agent:** Instruction page built. Manual trigger only — automation triggers pending (S44 Priority 1).
- **Contact & Company Review:** Active, manual trigger.
- **Floppy:** Step 2.0 tested in real meeting (S43).
- **Meeting Notetaker:** CRM-Optimized profile active and tested (S43).
- **Schema:** Hardened. QC enhanced (past_due on Action Items, wired:X on Delete for all 4 DBs, Series Parent carve-out on Meetings). Created Timestamp on 3 DBs (Meetings, Companies, Contacts). Created Date on Action Items. Series Status rollup on Meetings.
- **Meetings ↔ Contacts:** Dual relation active.
- **Series:** Option A architecture — dedicated view + rollup-based cascade inactivation. 5 Series Parents set to Active.
- **Agent Docs:** All instruction pages synced to Notion.
- **Legacy agents:** DEPRECATED. Triggers disabled.
- **Data quality:** Phone numbers normalized. EAG merged into Formul8. NULL Record Status backfilled on Meetings.

### Database Quick Reference

| Database | Data Source ID | Icon |
|----------|---------------|------|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` | 👤 |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` | 💼 |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` | 🎬 |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` | 🗓️ |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | ⚙️ |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`
