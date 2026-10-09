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
- Floor sheet: <command>                 # printed (never run) when a NEW_PL / NEW_CATEGORY / NEW_BRAND row exists;
                                         # `<intake.csv>` in the command is replaced by the intake path
- Vendor deal tag: <PKG - tag>           # the ruled one-time vendor cost deal package tag (R62); must
                                         # start `PKG - `; DEAL_UNDECIDED names it in the STOP
- Export QC / Inventory QC: (the BI Change Pointers lines)
- New line tag: <ITM - tag>              # OPTIONAL (R83): the tag a NEW_PL create carries; default `ITM - New PL`
- Active tag: <ITM - tag>                # OPTIONAL (R96): the standard state a mixed lane's copy reads; default `ITM - Active`
- Market center: <lat,lng>               # MSRP read (intake_msrp.py): the centre of the comparables set
- Market radius mi: <n>                  # MSRP read: the comparables radius in miles
- Market box: <S,W,N,E>                  # OPTIONAL: the live-feed listing box; default = twice the radius
- Market archive: <abs path>             # OPTIONAL: a dated menu harvest (menu_*.json + dispensaries_*.json)
- Own store: <token[, token]>            # MSRP read: the tenant's own store(s), dropped before matching
- MSRP anchor: <market | own lanes>      # OPTIONAL (ruled): which evidence sets the number; default `market`
- MSRP floor x cost: <n>                 # OPTIONAL (ruled): the number is never below cost x n (2 = keystone)
- FL EQ classes: <abs path .toml>        # OPTIONAL (R1-R3, R6): the tenant's fl_eq class map - [master.<Master category>]
                                         # tables with fl_eq = product_g_x<k> | thc_g_x<k> | composite | sentinel_<v> | none;
                                         # the lane derives Flower equiv (and the dose unit) from it. Absent: Flower equiv
                                         # stays at the create stop on every new line
```

The MSRP keys are read only by `intake_msrp.py`; the other runners ignore them. `MSRP anchor` and
`MSRP floor x cost` are the business's pricing ruling: write the ruled values and name the record.

The `Write channel` line in `## BI Change Pointers` is read as an ORDERED LADDER: the first channel
named is tried first, the next is the fallback. Example: `neo` -> `playwright` -> `pane`.
