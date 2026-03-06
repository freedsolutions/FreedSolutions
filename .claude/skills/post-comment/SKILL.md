---
name: post-comment
description: Pull a LinkedIn post's comment text from Notion, navigate to the post on LinkedIn, paste the comment, and auto-submit. Then mark the Notion task Done.
argument-hint: "[MM/DD/YYYY date, or blank for today]"
---

# Post Comment — LinkedIn Post Live Commenter

After a scheduled LinkedIn post goes live, this skill:
1. Finds the post in Notion by Due date
2. Pulls the **Description** field (the comment text)
3. Navigates to LinkedIn, locates the post, and **posts the Description as a comment**
4. Marks the Notion task as Done

## Usage

```
/post-comment                  # Find LinkedIn post due today
/post-comment 03/11/2026       # Find LinkedIn post due on specific date
```

## Constants

- **Notion data source:** `collection://319adb01-222f-8059-bd33-000b029a2fdd`
- **Notion company filter:** `🔗 Linkedin Posts`
- **LinkedIn profile activity:** `https://www.linkedin.com/in/adam-freed-60173568/recent-activity/all/`

## Execution Protocol

### Step 1: Resolve target date

Parse the argument as a date in MM/DD/YYYY format. If no argument, use today's date.
Store both:
- `TARGET_DATE_DISPLAY` — MM/DD/YYYY (e.g., `03/06/2026`)
- `TARGET_DATE_ISO` — YYYY-MM-DD (e.g., `2026-03-06`)

If the argument cannot be parsed as a valid date, stop and report:
```
POST COMMENT
────────────
[FAIL] Invalid date: "<argument>". Expected format: MM/DD/YYYY
```

### Step 2: Search Notion for the LinkedIn post

Use `notion-search` to find LinkedIn posts in the To Do List database:

```
notion-search:
  query: "LinkedIn"
  data_source_url: "collection://319adb01-222f-8059-bd33-000b029a2fdd"
```

From the results, fetch each candidate page with `notion-fetch` and filter to pages where:
- **Company** contains `🔗 Linkedin Posts`
- **Due date** matches `TARGET_DATE_ISO`

### Step 3: Handle match results

**No matches:**
```
POST COMMENT
────────────
[FAIL] No LinkedIn post found with Due date = TARGET_DATE_DISPLAY
       Searched: collection://319adb01-222f-8059-bd33-000b029a2fdd
       Tip: Check the Due date in Notion, or specify a date: /post-comment MM/DD/YYYY
```

**Multiple matches:**
List all and ask the user to pick:
```
POST COMMENT
────────────
[INFO] Multiple LinkedIn posts found for TARGET_DATE_DISPLAY:

  1. "Post title one" (Status: In progress)
  2. "Post title two" (Status: Not started)

Which post went live? Reply with the number.
```
Wait for user response, then proceed with the selected page.

**One match:** Proceed to Step 4.

### Step 4: Extract comment text from Notion

From the matched page's properties, read:
- `TASK_NAME` — Task name (title)
- `COMMENT_TEXT` — Description field (this becomes the LinkedIn comment)
- `DUE_DATE` — Due date (formatted MM/DD/YYYY)
- `STATUS_BEFORE` — current Status value

**If Description is empty**, stop and report:
```
POST COMMENT
────────────
Post:    "TASK_NAME"
[FAIL] Description field is empty — nothing to comment
       Add comment text to the Description property in Notion and retry
```

**If Status is already Done**, warn but continue:
```
[WARN] Post is already marked Done — proceeding anyway
```

### Step 5: Prepare output directory

```bash
mkdir -p test-results
```

### Step 6: Find the post on LinkedIn (Playwright MCP)

1. `browser_navigate` to `https://www.linkedin.com/in/adam-freed-60173568/recent-activity/all/`
2. `browser_wait_for` the activity feed to load (timeout: 15s)
3. If the page shows a login wall or CAPTCHA:
   - `browser_take_screenshot` → `test-results/post-comment-01-login-required.png`
   - `browser_close`
   - Stop and report:
     ```
     [FAIL] LinkedIn login required — log in first, then retry
     Screenshot: test-results/post-comment-01-login-required.png
     Browser: closed
     ```

4. `browser_snapshot` to get the accessibility tree of the activity feed
5. Identify the post that matches the target date. Look for:
   - Posts from today (or the target date) in the feed
   - Content that matches keywords from `TASK_NAME`
   - The most recent post if the date matches today

6. If the correct post **cannot be confidently identified**:
   - `browser_take_screenshot` → `test-results/post-comment-02-feed.png`
   - Ask the user: "I found these posts in your activity feed. Which one should I comment on? (screenshot attached)"
   - Wait for user response

7. `browser_take_screenshot` → `test-results/post-comment-02-post-found.png`

### Step 7: Post the comment on LinkedIn (Playwright MCP)

1. Click the **comment button/icon** on the identified post (use ref from snapshot)
2. `browser_wait_for` the comment input field to appear
3. `browser_snapshot` to locate the comment text input
4. Use `browser_click` on the comment input to focus it
5. Use `browser_type` to enter `COMMENT_TEXT` (the Description from Notion)
6. `browser_snapshot` to locate the Post/Submit button for the comment
7. Click the **Post/Submit** button to submit the comment
8. Wait briefly for the comment to appear
9. `browser_take_screenshot` → `test-results/post-comment-03-comment-posted.png`

### Step 8: Close the browser (CRITICAL)

**No matter what happens** — pass, fail, error, timeout — you MUST close the browser before reporting:
```
browser_close
```
This is a hard requirement. Never skip this step.

### Step 9: Update Notion status to Done

Use `notion-update-page` to mark the task as Done:

```
notion-update-page:
  page_id: "<page_id>"
  command: "update_properties"
  properties:
    Status: "Done"
```

### Step 10: Archive artifacts

```bash
node scripts/archive-smoke-artifacts.js
```

### Step 11: Report results

```
POST COMMENT
────────────
Post:     "TASK_NAME"
Due:      DUE_DATE
Comment:  "First 50 chars of COMMENT_TEXT..."
Status:   STATUS_BEFORE → Done

[PASS] Notion post found
[PASS] LinkedIn post located
[PASS] Comment posted on LinkedIn
[PASS] Notion status updated to Done

Screenshots: test-results/post-comment-*.png
Browser: closed
Artifacts: archived
```

## Failure Handling

If any step fails:
1. Take a screenshot of the current state (if browser is open)
2. Close the browser (CRITICAL — do this before reporting)
3. Report which step failed and why
4. Include screenshot paths in the report

**Partial success** — report each step independently:
```
POST COMMENT
────────────
Post:     "TASK_NAME"
Due:      DUE_DATE

[PASS] Notion post found
[PASS] LinkedIn post located
[FAIL] Comment submission failed: <error>
[SKIP] Notion status not updated (comment failed)

Screenshots: test-results/post-comment-01-login.png, ...
Browser: closed
Action: Post the comment manually on LinkedIn, then update Notion status
```

## Output Format

Always use this header and structure:

```
POST COMMENT
────────────
Post:     "<task name>"
Due:      <MM/DD/YYYY>
Comment:  "<first 50 chars>..."
Status:   <before> → Done

[PASS/FAIL] Notion post found
[PASS/FAIL] LinkedIn post located
[PASS/FAIL] Comment posted on LinkedIn
[PASS/FAIL] Notion status updated to Done

Screenshots: test-results/post-comment-*.png
Browser: closed
Artifacts: archived
```

Always end with `Browser: closed` and `Artifacts: archived` confirmation.
