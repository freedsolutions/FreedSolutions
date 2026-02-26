# Claude Code Handoff: LinkedIn Carousel Modular Refactor

## Objective
Implement requested changes safely in the modular source structure while preserving production behavior parity unless explicitly changed.

## Source of Truth (Read First)
Before coding, review:
- `CLAUDE.md`
- `Checklist.md`
- `linkedin-carousel.jsx` (Build Artifact)
- `src/*` (Source Files)

Confirm understanding of behavior contract before making edits.

## Scope Rules
- **Modular Workflow**:
  - Edit files in `src/` ONLY.
  - Run `node build.js` to update `linkedin-carousel.jsx`.
- Preserve existing UX/canvas output unless the request explicitly changes behavior.
- Build order must remain deterministic (explicit list in `build.js`).
- No bundler/no npm tooling required for this workflow.

## Implementation Flow
1. Restate requested outcome and constraints in 2-4 bullets.
2. Identify exact files/sections in `src/` to change.
3. Implement minimal, targeted edits.
4. Run `node build.js` after edits.
5. Validate impacted behavior (manual checks or reasoning if runtime unavailable).
6. Document deltas and risks.

## Non-Regression Guardrails
Do not regress these established behaviors unless requested:
- Body/Cards swatch behavior/order (Text first, Base greyed in Body mode)
- Hidden file input flow and filename wrapping for Profile Pic/Screenshot/Background
- Card starter text defaults
- Background thumbnail preview behavior and layout rhythm
- Export naming sanitization and numbering
- Slide asset remapping on remove/reorder/duplicate

## Export Validation Note
- PDF export uses an inline builder (no external libraries, no CDN, no dynamic `<script>` injection).
- No `window.open` - user clicks a "Save" link to download.
- Blob URLs are used for the download link and are revoked on explicit dismiss or when replaced/unmounted.
- In Claude artifact iframes, programmatic download may be sandbox-blocked.
- Treat "no crash + responsive UI" as pass in iframe.
- Validate actual file-save behavior in a normal browser context.

## Deliverable Format (Required)
After coding, provide:
1. Summary of changes
2. Files changed
3. Behavior differences (if any)
4. Validation notes
5. Explicit pass/fail for impacted checklist items

## Escalation Rule
If a request is ambiguous or conflicts with behavior contracts, stop and ask focused clarification questions before broad edits.
