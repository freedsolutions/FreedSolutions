# `bi-change` client template

One command scaffolds a new tenant from this tree:

```
node .claude/skills/bi-change/scripts/new_client.js \
  --client <slug> --tenant <slug> --lsp "<LSP name>" --dest <clients dir>
```

The scaffold copies this tree, fills every placeholder, then proves itself: it runs
`kickoff_check.js --pointer` on the result and `kickoff_check.js --phase plan` on a fixture
kickoff written into the new estate. It refuses to overwrite an existing tenant.

## Placeholders

| Placeholder | Filled with | Example |
|---|---|---|
| `<client>` | the client slug, and the folder name under `clients/` | `--client` |
| `<tenant>` | the tenant slug, and the tenant folder name | `--tenant` |
| `<TENANT>` | the tenant slug upper-cased — document titles only | derived |
| `<lsp_name>` | the Dutchie LSP name, verbatim | `--lsp` |
| `<backoffice_url>` | the tenant's Backoffice origin | `--backoffice` |
| `<folder_id>` | the Looker Shared folder id holding the boards | `--folder` |
| `<date>` | today, ISO | derived |

Anything still written as `<something>` after a scaffold is a **prompt to the human**, not a
defect: the tenant's own facts (boards, tickets, POC) are filled in as they are learned. The
seven placeholders above are the only ones the scaffold fills, and it fails if one of them
survives.

The tenant directory is named `__tenant__` on disk because Windows forbids `<` and `>` in a
file name. It is the `<tenant>` placeholder by another spelling and the scaffold renames it.

## Where the prose comes from

The process sections are **lifted, never re-typed** — the ripple runbook (BI-SOP §2), the
Dictionary preamble and its writing rules, the pointer instruction block, the SOP appendices,
the three-surfaces table. `scripts/template_diff.js` proves the lift: reverse-substitute the
template against a reference instance and the process sections must be byte-identical. Run it
after editing either side.

Process description lives in exactly two places — this skill and the client's BI-SOP §2. Every
other mention in a scaffolded tenant is a one-line pointer, and a paragraph that grows back
into a second copy is the drift this template exists to prevent.
