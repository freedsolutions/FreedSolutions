"""receive.py - phase 2 (Receiving) of the dutchie-intake lane. NOT BUILT: this is a stub.

  python receive.py [...]            prints the pointer to the phase 2 plan and exits 2
  python receive.py --check ...      NotImplemented; exits 2
  python receive.py --selftest       proves the stub refuses (exit 0 when it does)

The receiving plan lives in the TENANT estate (the plan file the tenant's intake kickoff names), not
in this skill. Its kickoff is owed after phase 1 closes. Phase 1 leaves the hooks it needs on the
intake CSV v3: landed_unit_cost (R103), expiry_date, po_line_ref, flags, package_id.

Intended signatures (documented so phase 2 builds to them; none of these runs today):

  receive.py --prep  <intake-vN.csv> [--po <po.csv>] --inventory <inventory.csv> --tenant <CLAUDE.md>
      -> a NEW receipt prep sheet, one row per package (a `;`-joined package_id splits into one row per
         tag): package_id, SKU, qty, invoice unit cost, landed unit cost
         (R103), the `PKG - ` tag decision with its rule (R62 / R72 / R84), room (hold for FIFO vs
         floor), expiry, flags. Human: reviews physical vs sheet, rules the PROMO_UNDECIDED rows.
  receive.py --enter <prep.csv> --tenant <CLAUDE.md>
      -> the inventory receipt, one package per write-channel call (route still to be probed).
  receive.py --check <prep.csv> <receipt-detail.csv> [--tenant <CLAUDE.md>]
      -> JOIN KEY: package_id (the intake CSV v3 column, carried onto the prep sheet) = the package
         tag on the Receipt Detail export row. Per joined package: qty, landed unit cost vs received
         unit cost, `PKG - ` tag present per R62 / R84, room per the tenant's room rule. The Receipt
         Detail export is the arbiter. Exit 1 on DEFECT.
  receive.py --vendor <prep.csv>
      -> the vendor-issue list (near expiry, cost drift, short ships) for the vendor thread.
"""
import sys

sys.dont_write_bytecode = True

EXIT_OK, EXIT_ABORT = 0, 2
CHECK_JOIN_KEY = "package_id"   # the documented `--check` join key: an intake CSV v3 column
MSG = ("receive: phase 2, not built. See the receiving plan named in the tenant estate "
       "(the intake kickoff points at it). Nothing was read or written.")


def check(prep_csv, receipt_detail_csv, tenant=None):
    """Phase 2 `--check`: prep sheet vs Receipt Detail export, joined on CHECK_JOIN_KEY. Not implemented."""
    raise NotImplementedError("receive --check is phase 2; see the receiving plan in the tenant estate")


def main(argv):
    if "--selftest" in argv:
        rc1, rc2 = main([]), main(["--check", "a.csv", "b.csv"])
        ok = rc1 == EXIT_ABORT and rc2 == EXIT_ABORT
        print(f"  {'PASS' if ok else 'FAIL'}  the stub refuses with exit 2 on both paths ({rc1}, {rc2})")
        print(f"receive selftest: {1 if ok else 0} passed, {0 if ok else 1} failed")
        return EXIT_OK if ok else 1
    if "--check" in argv:
        try:
            i = argv.index("--check")
            check(*(argv[i + 1:i + 3] + [None, None])[:2])
        except NotImplementedError as e:
            print(f"receive --check: NotImplemented - {e}")
            return EXIT_ABORT
    print(MSG)
    return EXIT_ABORT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
