# Example Tenant (synthetic fixture for selftest_all.py)

Not a real tenant. Relative paths resolve against this file's folder.

## BI Change Pointers

- **Estate dir:** `./` - fixture only
- **Backoffice login:** `https://<server>.backoffice.dutchie.com/` - the login stop opens this
- **Write channel:** `neo` (agent browser, one tab) -> fallback `playwright` -> `pane`. Reads: any channel.

## Intake Pointers
- Operator: Pat Example                  # the human at the pre-create STOP
- Mail label: Intake/Example             # `pull` reads this
- Drive invoices folder: fixture-folder-id
- Intake dir: ./intake-out               # never written by selftest_all (it passes --out-dir)
- Exports dir: ./
- Standard cost: lane Cost (R50)
- Expiry threshold days: 90
- PO source: apex
- Watermark: 500
- Notice template: ../templates/notice.md
- Floor sheet: python floor_sheet.py <intake.csv>
- Export QC / Inventory QC: (the BI Change Pointers lines)
