# dutchie-intake

Invoice -> Dutchie item creation, one command per stage, one human stop. Generic: every tenant fact
lives in the tenant's gitignored `CLAUDE.md`. The workflow and the rules of the road are in `SKILL.md`.

## Pipeline

```
 mail label ──pull──▶ Drive <Client>/Invoices/<Vendor>/<YYYY>/  +  <Intake dir>/inbox/ + manifest.jsonl
                                  │
 invoice.pdf ──intake_parse──▶ lines.csv ──intake_match──▶ intake-v1 ──intake_exceptions──▶ intake-v2
 (or --text rendering, --lines)        (Active / Retired /           (R102 flags, R62 read,
                                            Strains exports)              R103 landed cost)
                                                                               │
                                                        ══ STOP: Operator fills `approved`, replies ══
                                                                               │
          intake-v3 ◀──create (write channel, Operator's login, one Copy item per call)──┘
              │
              ├──intake_certify (pre / post exports) ──▶ -certify-<ts>.md   (A / B / C, exit 1 on C)
              └──intake_notice ──▶ -notice-<ts>.md  (+ floor-sheet command on NEW_PL / NEW_BRAND)
                                                     receive ──▶ phase 2 stub (exit 2)
```

## Modes

| Mode | Script | Login | Output |
|---|---|---|---|
| `pull` | session procedure (Gmail + Drive connectors) | connector only | Drive copy, inbox mirror, `manifest.jsonl` |
| `intake` | `intake_parse.py` -> `intake_match.py` -> `intake_exceptions.py` | none | lines CSV, intake v1 + v2, exceptions CSV, STOP message |
| `create` | session procedure in the write channel | Operator's | a new intake version with the read-back keys |
| `certify` | `intake_certify.py` (`--no-create` for hand writes) | none | `-certify-<ts>.md` |
| `notice` | `intake_notice.py` | none | `-notice-<ts>.md` (a draft; the Operator sends) |
| `receive` | `receive.py` | - | stub, exit 2 |

Exit codes everywhere: 0 clean, 1 DEFECT, 2 ABORT. Proof: `python scripts/selftest_all.py`.

## Layouts and the intake CSV

- Invoice layouts are plugins in `scripts/parsers/`, tried in order: `apex`, `fernway`,
  `generic_table`. A parser is detected by layout features, never by the vendor name.
- Every parser emits `package_id` per product line (blank when the layout prints none). It rides into
  the intake CSV v3 (54 columns, ending `parse_source`, `package_id`) and is the `receive --check`
  join key.
- A line that names no form word, where brand + body + grams hit exactly one active item, reads
  `EXISTS` + `FORM_UNREAD` (a STOP flag): the Operator confirms the match.

## Plug in a tenant

1. Paste `templates/intake-pointers.md` into the tenant `CLAUDE.md` under `## BI Change Pointers`
   and fill every `<placeholder>`.
2. Copy `templates/notice.md` into the tenant and point `Notice template:` at the copy.
3. `python scripts/intake_pointers.py --tenant <tenant CLAUDE.md>` must print `contract complete`.
4. Create the mail label and the Drive `<Client>/Invoices/` root; put its folder id in the pointer.
5. First invoice: run `intake` with explicit export paths, read the STOP, and check the verdicts by
   hand before trusting a freshest-file pick.
