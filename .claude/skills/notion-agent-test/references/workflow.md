<!-- Generated from "ops/notion-workspace/skills/notion-agent-test/references/workflow.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Notion Agent Testing Workflow

## Trigger Options

### Property change

1. Create or identify a test page in the target DB.
2. Set the triggering property to the required value.
3. Make any required body edit if the trigger depends on content changes.
4. Wait for execution and verify outputs.

### Manual `@mention`

1. Navigate to the target page in the browser.
2. Mention the agent in the page body with concise instructions.
3. Wait for execution and inspect both the page and Recent Activity.

### Run button

1. Open the agent settings page.
2. Use the `Run agent` button when it matches the scenario under test.

## Monitoring

- Check Recent Activity first.
- Re-fetch downstream records with Notion MCP.
- Use Agent Config timestamps when the workflow writes runtime markers.

## Cleanup

- Set test records to `Delete` only when that is the documented cleanup path.
- For cleanup tests, verify the current trash or archive workflow clears linked relations and rollups as expected instead of assuming a dedicated unwiring agent exists.

## Report Template

```text
## Test Report: [Agent or workflow]
Trigger method: [Property change / @mention / Run button]
Test data: [What was created or modified]
Agent fired: [Yes / No]
Execution time: [Approximate seconds]
Status: [Pass / Fail / Partial]

Checkpoints
- [Checkpoint]: [Pass/Fail] - [details]

Issues Found
- [Issue]

Cleanup
- [What was cleaned up]
```

Use this template as plain text in the final test report.
