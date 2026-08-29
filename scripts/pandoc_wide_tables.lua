-- pandoc_wide_tables.lua — fix for the GFM reader's non-wrapping pipe tables.
--
-- The commonmark/gfm reader never assigns relative column widths, so pandoc emits
-- natural-width (l l l) longtable columns and long cells run off the PDF page.
-- This filter measures each table's natural width; when it would overflow one text
-- line, it assigns proportional relative widths (with a floor so no column
-- vanishes), which makes the LaTeX writer emit wrapping p-columns. Small tables
-- are left at natural width — they look better that way.
--
-- Used by the pandoc-deliverable house recipe: pass --lua-filter=<this file>
-- on both DOCX and PDF builds.

local CHAR_BUDGET = 95 -- ~chars fitting one body line at Calibri 10pt / 0.75in margins
local FLOOR = 0.08     -- minimum relative width per column
local TOTAL = 0.98     -- total width to distribute (breathing room)

local function scan_rows(rows, maxlen, ncols)
  for _, row in ipairs(rows) do
    for i, cell in ipairs(row.cells) do
      if i <= ncols then
        local l = #pandoc.utils.stringify(cell.contents)
        if l > maxlen[i] then maxlen[i] = l end
      end
    end
  end
end

function Table(tbl)
  local ncols = #tbl.colspecs
  if ncols == 0 then return nil end
  local maxlen = {}
  for i = 1, ncols do maxlen[i] = 1 end
  if tbl.head then scan_rows(tbl.head.rows, maxlen, ncols) end
  for _, body in ipairs(tbl.bodies) do
    scan_rows(body.head, maxlen, ncols)
    scan_rows(body.body, maxlen, ncols)
  end
  if tbl.foot then scan_rows(tbl.foot.rows, maxlen, ncols) end

  local total = 0
  for i = 1, ncols do total = total + maxlen[i] end
  if total <= CHAR_BUDGET then return nil end -- fits on one line; leave natural

  local widths, sumw = {}, 0
  for i = 1, ncols do
    widths[i] = math.max(maxlen[i] / total, FLOOR)
    sumw = sumw + widths[i]
  end
  local newspecs = {}
  for i = 1, ncols do
    newspecs[i] = { tbl.colspecs[i][1], (widths[i] / sumw) * TOTAL }
  end
  tbl.colspecs = newspecs
  return tbl
end
