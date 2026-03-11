# Google Workspace Migration Audit

Audit date: 2026-03-11

## Current finding

No source edit is currently required to keep `FreedSolutions` itself working after the move from `freedsolutions@gmail.com` to `adam@freedsolutions.com`.

- `FreedSolutions` runtime files do not contain either email address. The live contact path is still the Calendly CTA at `https://calendly.com/freedsolutions/30min`.
- The old and new email addresses appear only in historical migration docs under `ops/`.
- `api-gas`, `DataIntegration`, and `ClientCode` do not contain either email address in runtime code.
- The real risk surface is Google account ownership:
  - `api-gas` CI restores `~/.clasprc.json` from `CLASPRC_B64`.
  - `DataIntegration` creates installable time-based triggers owned by the account that runs `createFullRefreshTrigger`.
  - `ClientCode` uses `MailApp.sendEmail(...)` and `Session.getActiveUser().getEmail()` in `DMC_PIM`, so sender identity and audit fields depend on the active Workspace account.

## Repo inventory

### FreedSolutions

- Site domain: `www.freedsolutions.com`
- Live CTA target: `https://calendly.com/freedsolutions/30min`
- Repo hygiene update: `.gitignore` now ignores Google OAuth client-secret downloads named `client_secret_*.apps.googleusercontent.com.json`

### api-gas

Google auth and deploy touchpoints:

- CI secret source: `CLASPRC_B64`
- Local switch/deploy entrypoints:
  - `npm run switch:sandbox`
  - `npm run switch:main`
  - `npm run push:sandbox`
  - `npm run push:main`
  - `npm run deploy:sandbox`
  - `npm run deploy:main`

Known Apps Script target configs:

- `packages/integration-core/.clasp.main.json`
- `packages/integration-core/.clasp.sandbox.json`
- `packages/integration-wrapper/.clasp.main.json`
- `packages/integration-wrapper/.clasp.sandbox.json`
- `packages/client-wrappers/dmc/dmc-apex-backend/.clasp.main.json`
- `packages/client-wrappers/dmc/dmc-dutchie-backend/.clasp.main.json`
- `packages/client-wrappers/primitiv/pri-backend/.clasp.main.json`

### DataIntegration

Environment-specific Apps Script targets:

- `config/env/prod/IntegrationCore.clasp.json`
- `config/env/prod/IntegrationWrapper.clasp.json`
- `config/env/sandbox/IntegrationCore.clasp.json`
- `config/env/sandbox/IntegrationWrapper.clasp.json`

Trigger installers that create a `runFetchAndPush` clock trigger every 10 minutes:

- `IntegrationWrapper/Setup.js`
- `ClientWrappers/DMC_Apex_Backend/Setup.js`
- `ClientWrappers/DMC_Dutchie_Backend/Setup.js`
- `ClientWrappers/DMC_Inventory_Backend/Setup.js`
- `ClientWrappers/Primitiv_Backend/Setup.js`

### ClientCode

Environment-specific Apps Script targets:

- `config/env/prod/DMC_PIM.clasp.json`
- `config/env/prod/PRI_Backend.clasp.json`
- `config/env/sandbox/DMC_PIM.clasp.json`
- `config/env/sandbox/PRI_Backend.clasp.json`

Identity-sensitive runtime behavior:

- `DMC_PIM/Main.js` sends alert emails with `MailApp.sendEmail(...)`
- `DMC_PIM/Email.js` sends QC and summary emails with `MailApp.sendEmail(...)`
- `DMC_PIM/BusinessRules.js` and `DMC_PIM/Modal.js` write `Session.getActiveUser().getEmail()`
- `DMC_PIM/Menu.js` instructs the operator to install the daily-summary time-based trigger manually in the Apps Script UI

Known email recipient currently configured in code:

- `DMC_PIM/Config.js` sends alerts to `systems@thccrafts.com`

## Manual validation checklist

> **Execution order:** Run sections 1–5 in the order listed. Section 2 (credential rotation) should be completed before any CI deploy is attempted. This ordering is assumed based on dependency logic and has not been independently verified.

### 1. FreedSolutions website and Calendly

1. Open `https://www.freedsolutions.com`.
2. Click the primary CTA and confirm it still resolves to `https://calendly.com/freedsolutions/30min`.
3. Run a real test booking.
4. Confirm the event lands in the calendar owned by or connected to `adam@freedsolutions.com`.
5. Confirm any confirmation emails originate from the intended Google Workspace identity.

### 2. api-gas credential rotation

1. In a shell on the machine that normally deploys `api-gas`, authenticate `clasp` with the Workspace account:

   ```powershell
   cd C:\Users\adamj\Code\api-gas
   npx clasp login
   ```

2. Confirm the new account has editor access to every GAS project referenced by the `.clasp*.json` files listed above.
3. Rebuild the GitHub Actions secret payload from the new `~/.clasprc.json`:

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\.clasprc.json"))
   ```

4. Replace the `CLASPRC_B64` repository secret in GitHub with that value.
5. Validate local auth against both environments:

   ```powershell
   npm run switch:sandbox
   npm run push:sandbox
   npm run switch:main
   npm run push:main
   ```

6. Validate CI by letting the next normal deploy workflow run with the rotated secret.

### 3. DataIntegration account and trigger ownership

1. Start with a clean working tree before running switch/deploy scripts. This repo's scripts commit environment changes.
2. Authenticate `clasp` with the Workspace account:

   ```powershell
   cd C:\Users\adamj\Code\DataIntegration
   clasp login
   ```

3. Confirm the Workspace account has editor access to the prod and sandbox scripts referenced by `config/env/`.
4. Refresh sandbox config and push code for IntegrationCore and IntegrationWrapper:

   ```powershell
   bash scripts/switch-env.sh sandbox
   cd IntegrationCore
   npx clasp push --force
   cd ..\IntegrationWrapper
   npx clasp push --force
   ```

5. **ClientWrappers** are synced from IntegrationWrapper and are in scope, but may not need independent pushes. After IntegrationWrapper is confirmed, verify that each ClientWrapper script (`DMC_Apex_Backend`, `DMC_Dutchie_Backend`, `DMC_Inventory_Backend`, `Primitiv_Backend`) reflects the updated code. Push individually only if a discrepancy is found.

6. **Verify trigger ownership before taking action.** In the Apps Script UI for each live project, check the existing time-based triggers:
   - If triggers are already owned by `adam@freedsolutions.com` — no action needed.
   - If triggers are still owned by the old Gmail account — delete them, then run `createFullRefreshTrigger` once while signed in as `adam@freedsolutions.com` to create a replacement.

7. After the next scheduled run, confirm execution succeeds and any downstream fetch/push workflow still has required permissions.

### 4. ClientCode account, triggers, and sender identity

1. Authenticate `clasp` with the Workspace account:

   ```powershell
   cd C:\Users\adamj\Code\ClientCode
   clasp login
   ```

2. Confirm editor access to the GAS projects referenced by:
   - `config/env/prod/DMC_PIM.clasp.json`
   - `config/env/sandbox/DMC_PIM.clasp.json`
   - `config/env/prod/PRI_Backend.clasp.json`
   - `config/env/sandbox/PRI_Backend.clasp.json`
3. Push sandbox first:

   ```powershell
   bash scripts/switch-env.sh DMC_PIM sandbox
   cd DMC_PIM
   npx clasp push --force
   cd ..
   bash scripts/switch-env.sh PRI_Backend sandbox
   cd PRI_Backend
   npx clasp push --force
   ```

4. **Verify trigger ownership before taking action.** Open `Extensions > Apps Script > Triggers` for `DMC_PIM`:
   - If the daily-summary trigger is already owned by `adam@freedsolutions.com` — no action needed.
   - If it is still owned by the old Gmail account — delete it, then reinstall it while signed in as `adam@freedsolutions.com`.

   `setupTriggers()` is a status/info helper only. It does not create the time-based trigger. Install the daily-summary trigger directly in the Apps Script UI as described in `Menu.js`, then confirm only one copy of that trigger is running afterward.

5. Run one end-to-end `DMC_PIM` action that:
   - sends an email
   - writes a `CREATED_BY` or user-email field
6. Confirm for `DMC_PIM`:
   - email delivery still works
   - the sender identity is acceptable
   - `Session.getActiveUser().getEmail()` now resolves as expected
   - no downstream logic assumes the old Gmail address

7. **PRI_Backend verification.** A local code scan did not find `MailApp.sendEmail(...)` or `Session.getActiveUser().getEmail()` usage in `PRI_Backend`. No email-identity-specific follow-up is currently indicated there, but after re-authentication you should still run one normal `PRI_Backend` workflow to confirm the script still executes under `adam@freedsolutions.com`.

### 5. Non-code admin follow-through

Complete these outside the repo:

- Calendly account owner and connected calendar
- Notion account email and any email-to-Notion workflow
- Cowork scheduled tasks — confirm the Outlook invite-forwarding task and Google Calendar to Outlook sync both target `adam@freedsolutions.com`
- LinkedIn contact email and website URL
- GitHub repository secrets and personal access/recovery email settings
- Google Workspace DNS/auth records: MX, SPF, DKIM, DMARC
- 2FA recovery emails and any OAuth clients created under the old Gmail

## What was validated locally

These checks were completed from the workspace:

- Exact-string search for `freedsolutions@gmail.com` and `adam@freedsolutions.com` across `FreedSolutions`, `api-gas`, `DataIntegration`, and `ClientCode`
- Apps Script target inventory from `.clasp*.json` and `config/env/*.clasp.json`
- Trigger-entrypoint inventory from `Setup.js` and menu/setup functions
- Runtime identity touchpoint inventory for `MailApp.sendEmail(...)` and `Session.getActiveUser().getEmail()`

These checks were not executable from this workspace:

- `clasp login` re-authentication
- GitHub secret rotation in the remote repo
- Real deploys to Google Apps Script
- Website click-through and live Calendly booking verification
- Trigger ownership checks in the Apps Script UI
