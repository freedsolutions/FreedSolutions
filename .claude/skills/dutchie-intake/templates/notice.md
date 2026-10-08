<!-- dutchie-intake new-items notice template. Copy it into the tenant and point `Notice template:` at the copy.
  Filled by scripts/intake_notice.py from the intake CSV. Markers (a marker line is replaced or dropped):
    [[items]]       one line per created item (verdict NEW_ITEM_WITH_SIBLING / NEW_PL / NEW_BRAND, approved = Y):
                    "- <final name> - SKU <sku>"; the SKU segment is left out while the row has no read-back SKU
    [[needs-hand]]  one bullet per open attribute; "- Nothing." when none. An image bullet fires for every
                    created item with no image unless `image_source` records a sourced image (`sourced: <url>`);
                    `not found: <where>` prints where the lane looked, `not attempted` / blank says so.
                    An online-title bullet fires for a created item with no `online_title`.
    [[new-line]]    the line is kept only when a NEW_PL / NEW_BRAND row was created (approved = Y); <new lines>
                    names those items by final name with SKU / ProductId when the row has them, never an
                    approved = N row and never an invoice line
  A created NEW_PL item's [[items]] line is marked "NEW LINE, tagged `<new line tag>`: please review".
  Angle-bracket fields filled by the script: <Brand> <n> <invoice number> <invoice date> <new line tag>
  <Operator> <new lines>. Anything still written <like this> after the fill is for the Operator.
  One email per intake run, plain text, under fifteen lines. The Operator adds recipients and sends.
  This comment block is stripped from the output. -->
**Subject:** New SKUs in Dutchie - <Brand> (<n> items)

Hi team,

<n> new items were created in Dutchie today from <Brand> invoice <invoice number> (<invoice date>).

[[items]]

What is in place: category, dosage, flower equivalent, price, cost, vendor, brand, strain, online title and description.

What still needs a hand:
[[needs-hand]]

[[new-line]] New line: <new lines> - a new product line for us. The floor sheet is attached (one page). Please get it in front of the budtenders.

Every new item shows on the new-items queue until its first package is received.

[[new-line]] The new-line items carry `<new line tag>`: please review them. The tag comes off the item when the receipt is prepped, and stays on the packages for the new-line carousel.

Questions to <Operator>.

Thanks,
<Operator>
