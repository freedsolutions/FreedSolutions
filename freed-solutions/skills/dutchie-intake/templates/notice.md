<!-- dutchie-intake new-items notice template. Copy it into the tenant and point `Notice template:` at the copy.
  Filled by scripts/intake_notice.py from the intake CSV. Markers (a marker line is replaced or dropped):
    [[items]]       one line per created item: "- <final name> - SKU <sku>"
    [[needs-hand]]  one bullet per open attribute (image, online title); "- Nothing." when none
    [[new-line]]    the line is kept only when the CSV carries a NEW_PL, NEW_CATEGORY or NEW_BRAND row
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
