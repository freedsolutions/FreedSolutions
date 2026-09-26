# Intake Pointers - paste into the tenant CLAUDE.md

Paste the block below into the tenant's gitignored `CLAUDE.md`, directly under `## BI Change Pointers`
(the `dutchie-intake` skill also reads `Backoffice login` and `Write channel` from that block). Replace
every `<placeholder>`. A value still written `<like this>` counts as MISSING and every runner aborts
on it: `python <skill>/scripts/intake_pointers.py --tenant <tenant CLAUDE.md>` must print
`contract complete`. Paths are absolute: task worktrees do not contain the gitignored tenant tree.

The thresholds are RULED by the business, never tuned from data. Write the ruled number and name the
record that ruled it in the tenant's DECISIONS.

```
## Intake Pointers
- Operator: <name>                       # the human at the pre-create STOP; the notice signs as them
- Mail label: <Gmail label>              # `pull` reads this; a shared inbox later = one line change
- Drive invoices folder: <folder id>     # the <Client>/Invoices/ root; <Vendor>/<YYYY>/ below it
- Intake dir: <abs path>                 # inbox/, manifest.jsonl, intake CSVs, exceptions, notices
- Exports dir: <abs path>                # freshest Catalog Active / Retired / Strains / Receipt Detail
- Standard cost: lane Cost (R50)         # what COST_DRIFT compares to (the only standard implemented)
- Expiry threshold days: <n>             # EXPIRY_NEAR fires under this many days (ruled)
- PO source: <apex | vendor pdf | none>  # PO_MISMATCH input; `none` makes the flag n/a
- Watermark: <product_id>                # the go-live watermark of the new-items queue
- Notice template: <abs path>            # a tenant copy of the skill's templates/notice.md
- Floor sheet: <command>                 # printed (never run) when a NEW_PL / NEW_BRAND row exists;
                                         # `<intake.csv>` in the command is replaced by the intake path
- Export QC / Inventory QC: (the BI Change Pointers lines)
```

The `Write channel` line in `## BI Change Pointers` is read as an ORDERED LADDER: the first channel
named is tried first, the next is the fallback. Example: `neo` -> `playwright` -> `pane`.
