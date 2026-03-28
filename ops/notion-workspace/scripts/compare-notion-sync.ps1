param(
    [Parameter(Mandatory = $true)]
    [string]$LocalFile,

    [Parameter(Mandatory = $true)]
    [string]$RemoteFile
)

$ErrorActionPreference = 'Stop'

function Convert-HtmlTablesToCanonical {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $lines = $Text -split "`n"
    $output = New-Object System.Collections.Generic.List[string]
    $outsideFenceLines = New-Object System.Collections.Generic.List[string]
    $inFence = $false
    $fenceMarker = ''

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        $wasInFence = $inFence
        $fenceState = Update-MarkdownFenceState -Line $line -InFence $inFence -FenceMarker $fenceMarker
        $inFence = $fenceState.InFence
        $fenceMarker = $fenceState.FenceMarker

        if ($fenceState.IsFenceLine) {
            if (-not $wasInFence -and $outsideFenceLines.Count -gt 0) {
                $output.Add((Convert-HtmlTableBlockToCanonical -Text ($outsideFenceLines -join "`n")))
                $outsideFenceLines.Clear()
            }

            $output.Add($line)
            continue
        }

        if ($line -match '^(?: {4}|\t)') {
            if ($outsideFenceLines.Count -gt 0) {
                $output.Add((Convert-HtmlTableBlockToCanonical -Text ($outsideFenceLines -join "`n")))
                $outsideFenceLines.Clear()
            }

            $output.Add($line)
            continue
        }

        if ($inFence) {
            $output.Add($line)
            continue
        }

        $outsideFenceLines.Add($line)
    }

    if ($outsideFenceLines.Count -gt 0) {
        $output.Add((Convert-HtmlTableBlockToCanonical -Text ($outsideFenceLines -join "`n")))
    }

    return $output -join "`n"
}

function Convert-HtmlTableBlockToCanonical {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    if ($Text.Length -eq 0) {
        return ''
    }

    $tablePattern = [regex]::new('(?is)<table\b[^>]*>(.*?)</table>')

    return $tablePattern.Replace($Text, [System.Text.RegularExpressions.MatchEvaluator]{
        param($match)

        $rowMatches = [regex]::Matches($match.Value, '(?is)<tr\b[^>]*>\s*(.*?)\s*</tr>')
        $canonicalRows = New-Object System.Collections.Generic.List[string]

        foreach ($rowMatch in $rowMatches) {
            $cellMatches = [regex]::Matches($rowMatch.Groups[1].Value, '(?is)<t[dh]\b[^>]*>\s*(.*?)\s*</t[dh]>')
            if ($cellMatches.Count -eq 0) {
                continue
            }

            $cells = New-Object System.Collections.Generic.List[string]
            foreach ($cellMatch in $cellMatches) {
                $cells.Add((Normalize-CanonicalTableCellText -Text $cellMatch.Groups[1].Value))
            }

            $canonicalRows.Add((Convert-CanonicalTableCellsToRow -Cells @($cells)))
        }

        if ($canonicalRows.Count -eq 0) {
            return '[TABLE][/TABLE]'
        }

        return "[TABLE]`n$($canonicalRows -join "`n")`n[/TABLE]"
    })
}

function Test-IsMarkdownTableSeparatorLine {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    return $Line -match '^\s*\|?(?:\s*:?-+:?\s*\|)+(?:\s*:?-+:?\s*)?$'
}

function Test-IsMarkdownEscapedCharacter {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [int]$Index
    )

    if ($Index -le 0 -or $Index -gt ($Text.Length - 1)) {
        return $false
    }

    $backslashCount = 0
    for ($i = $Index - 1; $i -ge 0 -and $Text[$i] -eq '\'; $i--) {
        $backslashCount++
    }

    return (($backslashCount % 2) -eq 1)
}

function Get-MarkdownInlineSegments {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $segments = New-Object System.Collections.Generic.List[object]
    $buffer = New-Object System.Text.StringBuilder
    $i = 0

    while ($i -lt $Text.Length) {
        if (($Text[$i] -eq '`') -and (-not (Test-IsMarkdownEscapedCharacter -Text $Text -Index $i))) {
            $tickCount = 1
            while (($i + $tickCount) -lt $Text.Length -and $Text[$i + $tickCount] -eq '`') {
                $tickCount++
            }

            $ticks = '`' * $tickCount
            $closingIndex = -1
            $searchIndex = $i + $tickCount

            while ($searchIndex -lt $Text.Length) {
                $candidateIndex = $Text.IndexOf($ticks, $searchIndex)
                if ($candidateIndex -lt 0) {
                    break
                }

                if (-not (Test-IsMarkdownEscapedCharacter -Text $Text -Index $candidateIndex)) {
                    $closingIndex = $candidateIndex
                    break
                }

                $searchIndex = $candidateIndex + 1
            }

            if ($closingIndex -ge 0) {
                if ($buffer.Length -gt 0) {
                    $segments.Add([pscustomobject]@{
                        Text   = $buffer.ToString()
                        IsCode = $false
                    })
                    [void]$buffer.Clear()
                }

                $segments.Add([pscustomobject]@{
                    Text   = $Text.Substring($i, ($closingIndex + $tickCount) - $i)
                    IsCode = $true
                })

                $i = $closingIndex + $tickCount
                continue
            }
        }

        [void]$buffer.Append($Text[$i])
        $i++
    }

    if ($buffer.Length -gt 0 -or $segments.Count -eq 0) {
        $segments.Add([pscustomobject]@{
            Text   = $buffer.ToString()
            IsCode = $false
        })
    }

    return $segments.ToArray()
}

function Get-MarkdownIndentWidth {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Indent
    )

    $indentWidth = 0
    foreach ($char in $Indent.ToCharArray()) {
        if ($char -eq "`t") {
            $indentWidth += 4
            continue
        }

        $indentWidth += 1
    }

    return $indentWidth
}

function Get-MarkdownCodeSpanInnerText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    if ($Text.Length -eq 0 -or $Text[0] -ne '`') {
        return $Text
    }

    $tickCount = 1
    while ($tickCount -lt $Text.Length -and $Text[$tickCount] -eq '`') {
        $tickCount++
    }

    if ($Text.Length -lt ($tickCount * 2)) {
        return $Text
    }

    $ticks = '`' * $tickCount
    if (-not $Text.EndsWith($ticks)) {
        return $Text
    }

    return $Text.Substring($tickCount, $Text.Length - ($tickCount * 2))
}

function Convert-CanonicalTableCellsToRow {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string[]]$Cells
    )

    return '[ROW]' + (ConvertTo-Json -InputObject @($Cells) -Compress)
}

function Update-MarkdownFenceState {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line,

        [Parameter(Mandatory = $true)]
        [bool]$InFence,

        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$FenceMarker
    )

    $trimmed = $Line.Trim()
    $nextInFence = $InFence
    $nextFenceMarker = $FenceMarker
    $isFenceLine = $false

    if ($trimmed -match '^(?<fence>`{3,}|~{3,})') {
        if (-not $InFence) {
            $nextInFence = $true
            $nextFenceMarker = $Matches['fence']
            $isFenceLine = $true
        } elseif ($trimmed -match ('^(?:' + [regex]::Escape($FenceMarker.Substring(0, 1)) + '{' + $FenceMarker.Length + ',})\s*$')) {
            $nextInFence = $false
            $nextFenceMarker = ''
            $isFenceLine = $true
        }
    }

    return [pscustomobject]@{
        IsFenceLine = $isFenceLine
        InFence     = $nextInFence
        FenceMarker = $nextFenceMarker
    }
}

function Test-IsMarkdownTableRowLine {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    $trimmed = $Line.Trim()
    if ($trimmed.Length -eq 0) {
        return $false
    }

    return (@(Get-MarkdownTableCells -Line $Line).Count -gt 1)
}

function Get-MarkdownTableCells {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    $trimmed = $Line.Trim()
    $cells = New-Object System.Collections.Generic.List[string]
    $current = New-Object System.Text.StringBuilder

    foreach ($segment in (Get-MarkdownInlineSegments -Text $trimmed)) {
        if ($segment.IsCode) {
            [void]$current.Append($segment.Text)
            continue
        }

        for ($i = 0; $i -lt $segment.Text.Length; $i++) {
            $char = $segment.Text[$i]

            if ($char -eq '[') {
                $linkEnd = Get-MarkdownLinkEndIndex -Text $segment.Text -StartIndex $i
                if ($linkEnd -ge $i) {
                    [void]$current.Append($segment.Text.Substring($i, ($linkEnd - $i) + 1))
                    $i = $linkEnd
                    continue
                }
            }

            if ($char -eq '<') {
                $autolinkEnd = Get-MarkdownAutolinkEndIndex -Text $segment.Text -StartIndex $i
                if ($autolinkEnd -ge $i) {
                    [void]$current.Append($segment.Text.Substring($i, ($autolinkEnd - $i) + 1))
                    $i = $autolinkEnd
                    continue
                }
            }

            if ($char -eq '\') {
                if ($i + 1 -lt $segment.Text.Length -and $segment.Text[$i + 1] -eq '|') {
                    [void]$current.Append('|')
                    $i++
                    continue
                }

                [void]$current.Append($char)
                continue
            }

            if ($char -eq '|') {
                $cells.Add($current.ToString().Trim())
                [void]$current.Clear()
                continue
            }

            [void]$current.Append($char)
        }
    }

    $cells.Add($current.ToString().Trim())

    if ($trimmed.StartsWith('|') -and $cells.Count -gt 0 -and $cells[0] -eq '') {
        $cells.RemoveAt(0)
    }

    if ($trimmed.EndsWith('|') -and $cells.Count -gt 0 -and $cells[$cells.Count - 1] -eq '') {
        $cells.RemoveAt($cells.Count - 1)
    }

    return @($cells)
}

function Get-MarkdownAutolinkEndIndex {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [int]$StartIndex
    )

    if ($StartIndex -lt 0 -or $StartIndex -ge $Text.Length -or $Text[$StartIndex] -ne '<') {
        return -1
    }

    $autolinkEnd = $Text.IndexOf('>', $StartIndex + 1)
    if ($autolinkEnd -le $StartIndex) {
        return -1
    }

    $autolinkText = $Text.Substring($StartIndex + 1, $autolinkEnd - $StartIndex - 1)
    if (
        ($autolinkText -match '^[a-z][a-z0-9+.-]*://') -or
        ($autolinkText -match '^[^@\s<>]+@[^@\s<>]+$')
    ) {
        return $autolinkEnd
    }

    return -1
}

function Get-MarkdownLinkEndIndex {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [int]$StartIndex
    )

    if ($StartIndex -lt 0 -or $StartIndex -ge $Text.Length -or $Text[$StartIndex] -ne '[') {
        return -1
    }

    $labelEnd = -1
    for ($i = $StartIndex + 1; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq '\') {
            $i++
            continue
        }

        if ($Text[$i] -eq ']' -and ($i + 1) -lt $Text.Length -and $Text[$i + 1] -eq '(') {
            $labelEnd = $i
            break
        }
    }

    if ($labelEnd -lt 0) {
        return -1
    }

    $depth = 1
    for ($i = $labelEnd + 2; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq '\') {
            $i++
            continue
        }

        if ($Text[$i] -eq '(') {
            $depth++
            continue
        }

        if ($Text[$i] -eq ')') {
            $depth--
            if ($depth -eq 0) {
                return $i
            }
        }
    }

    return -1
}

function Convert-MarkdownLinksToPlainText {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = New-Object System.Text.StringBuilder

    for ($i = 0; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq '<') {
            $autolinkEnd = Get-MarkdownAutolinkEndIndex -Text $Text -StartIndex $i
            if ($autolinkEnd -ge $i) {
                [void]$normalized.Append($Text.Substring($i + 1, $autolinkEnd - $i - 1))
                $i = $autolinkEnd
                continue
            }
        }

        if ($Text[$i] -eq '[') {
            $linkEnd = Get-MarkdownLinkEndIndex -Text $Text -StartIndex $i
            if ($linkEnd -ge $i) {
                $labelEnd = -1
                for ($j = $i + 1; $j -lt $Text.Length; $j++) {
                    if ($Text[$j] -eq '\') {
                        $j++
                        continue
                    }

                    if ($Text[$j] -eq ']' -and ($j + 1) -lt $Text.Length -and $Text[$j + 1] -eq '(') {
                        $labelEnd = $j
                        break
                    }
                }

                if ($labelEnd -gt $i) {
                    [void]$normalized.Append($Text.Substring($i + 1, $labelEnd - $i - 1))
                    $i = $linkEnd
                    continue
                }
            }
        }

        [void]$normalized.Append($Text[$i])
    }

    return $normalized.ToString()
}

function Remove-MarkdownEmphasisMarkers {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = $Text
    $normalized = [regex]::Replace($normalized, '\*\*([^*\n]+)\*\*', '$1')
    $normalized = [regex]::Replace($normalized, '__([^_\n]+)__', '$1')
    $normalized = [regex]::Replace($normalized, '(?<!\*)\*([^*\n]+)\*(?!\*)', '$1')
    $normalized = [regex]::Replace($normalized, '(?<!_)_([^_\n]+)_(?!_)', '$1')
    return $normalized
}

function Normalize-MarkdownNonCodeSegmentText {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = [regex]::Replace($Text, '(?is)<br\s*/?>', "`n")
    $normalized = [regex]::Replace($normalized, '(?is)</?(?:a|em|strong|b|i|code|p|span|div|ul|ol|li)\b[^>]*>', '')
    $normalized = [System.Net.WebUtility]::HtmlDecode($normalized)
    $normalized = Convert-MarkdownLinksToPlainText -Text $normalized
    $normalized = Remove-MarkdownEmphasisMarkers -Text $normalized
    return $normalized
}

function Normalize-CanonicalTableCellText {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = $Text -replace "`r`n?", "`n"
    $normalizedBuilder = New-Object System.Text.StringBuilder

    foreach ($segment in (Get-MarkdownInlineSegments -Text $normalized)) {
        $segmentText = $segment.Text

        if ($segment.IsCode) {
            $segmentText = Get-MarkdownCodeSpanInnerText -Text $segmentText
            $segmentText = [System.Net.WebUtility]::HtmlDecode($segmentText)
        } else {
            $segmentText = Normalize-MarkdownNonCodeSegmentText -Text $segmentText
        }

        [void]$normalizedBuilder.Append($segmentText)
    }

    $normalized = $normalizedBuilder.ToString()
    $normalized = [regex]::Replace($normalized, '[ \t]+(?=\n)', '')
    $normalized = [regex]::Replace($normalized, '\n+', ' ')
    $normalized = [regex]::Replace($normalized, '\s{2,}', ' ')
    return $normalized.Trim()
}

function Normalize-SpacedArrowEscapesOutsideCode {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = New-Object System.Text.StringBuilder

    foreach ($segment in (Get-MarkdownInlineSegments -Text $Text)) {
        $segmentText = $segment.Text
        if (-not $segment.IsCode) {
            $segmentText = $segmentText -replace '-\\>', '->'
        }

        [void]$normalized.Append($segmentText)
    }

    return $normalized.ToString()
}

function Normalize-MarkdownLinksOutsideCode {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = New-Object System.Text.StringBuilder

    foreach ($segment in (Get-MarkdownInlineSegments -Text $Text)) {
        $segmentText = $segment.Text
        if (-not $segment.IsCode) {
            $segmentText = Convert-MarkdownLinksToPlainText -Text $segmentText
        }

        [void]$normalized.Append($segmentText)
    }

    return $normalized.ToString()
}

function Normalize-QuotedFenceMarkers {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    if ($Line -match '^(?<indent>\s*)>\s*(?:`{1,}|~{1,})\s*$') {
        return ($Matches['indent'] + '> ```')
    }

    return $Line
}

function Normalize-BlockquoteSpacing {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    if ($Line -notmatch '^(?<indent>\s*)(?<markers>(?:>\s*)+)(?<rest>.*)$') {
        return $Line
    }

    $markerCount = [regex]::Matches($Matches['markers'], '>').Count
    $prefix = $Matches['indent'] + (('> ' * $markerCount).TrimEnd())

    if ([string]::IsNullOrWhiteSpace($Matches['rest'])) {
        return $prefix
    }

    return ($prefix + ' ' + $Matches['rest'].TrimStart())
}

function Normalize-BlockquoteListMarkers {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    if ($Line -notmatch '^(?<prefix>\s*(?:>\s*)+)(?<marker>(?:[-*+]|\d+\.))\s+(?<rest>.*)$') {
        return $Line
    }

    $marker = if ($Matches['marker'] -match '^\d+\.$') { '1.' } else { $Matches['marker'] }
    return ($Matches['prefix'] + $marker + ' ' + $Matches['rest'])
}

function Test-IsNestedMarkdownListLine {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line,

        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$PreviousNonBlankLine,

        [Parameter(Mandatory = $true)]
        [bool]$PreviousLineWasBlank
    )

    $lineMatch = [regex]::Match($Line, '^(?<indent>[ \t]+)(?:[-*+]|\d+\.)\s+')
    if (-not $lineMatch.Success) {
        return $false
    }

    if ($PreviousNonBlankLine -notmatch '^\s*(?:[-*+]|\d+\.)\s+') {
        return $false
    }

    return (-not $PreviousLineWasBlank)
}

function Normalize-MarkdownListIndentation {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    if ($Line -notmatch '^(?<indent>\s*)(?<marker>(?:[-*+]|\d+\.))\s+(?<rest>.*)$') {
        return $Line
    }

    $indentWidth = Get-MarkdownIndentWidth -Indent $Matches['indent']

    $marker = if ($Matches['marker'] -match '^\d+\.$') { '1.' } else { $Matches['marker'] }
    if ($indentWidth -eq 0) {
        return ($marker + ' ' + $Matches['rest'])
    }

    $depth = [Math]::Max(1, [int][Math]::Ceiling($indentWidth / 4.0))
    return (('    ' * $depth) + $marker + ' ' + $Matches['rest'])
}

function Test-IsLikelyMarkdownTableDataRow {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line,

        [Parameter(Mandatory = $true)]
        [int]$ExpectedCellCount
    )

    if (-not (Test-IsMarkdownTableRowLine -Line $Line)) {
        return $false
    }

    $trimmed = $Line.Trim()
    $cells = @(Get-MarkdownTableCells -Line $Line)
    if ($cells.Count -ne $ExpectedCellCount) {
        return $false
    }

    return $trimmed.StartsWith('|') -or $trimmed.EndsWith('|') -or ($Line -match '\s\|\s')
}

function Test-IsOptionalBlankNeighborLine {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    if ($Line -match '^\s*#+\s+') {
        return $true
    }

    if ($Line -match '^\s*>') {
        return $true
    }

    if ($Line -match '^\s*(?:[-*+]|\d+\.)\s+') {
        return $true
    }

    if ($Line -match '^\s*(?:\*\*[^*\n]+\*\*|__[^_\n]+__)\s*$') {
        return $true
    }

    if ($Line -match '^\s*(?:---+|\*\*\*+|___+)\s*$') {
        return $true
    }

    if ($Line -match '^\s*(?:\[/?TABLE\]|\[ROW\])') {
        return $true
    }

    if ($Line -match '^\s*(?:`{3,}|~{3,})') {
        return $true
    }

    if ($Line -match ':\s*$') {
        return $true
    }

    return $false
}

function Convert-MarkdownTablesToCanonical {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $lines = $Text -split "`n"
    $output = New-Object System.Collections.Generic.List[string]
    $inFence = $false
    $fenceMarker = ''

    for ($i = 0; $i -lt $lines.Count;) {
        $line = $lines[$i]
        $fenceState = Update-MarkdownFenceState -Line $line -InFence $inFence -FenceMarker $fenceMarker
        $inFence = $fenceState.InFence
        $fenceMarker = $fenceState.FenceMarker

        if ($fenceState.IsFenceLine) {
            $output.Add($line)
            $i++
            continue
        }

        if ($inFence) {
            $output.Add($line)
            $i++
            continue
        }

        if ($line -match '^(?: {4}|\t)') {
            $output.Add($line)
            $i++
            continue
        }

        if (
            (Test-IsMarkdownTableRowLine -Line $line) -and
            ($i + 1 -lt $lines.Count) -and
            (Test-IsMarkdownTableSeparatorLine -Line $lines[$i + 1])
        ) {
            $canonicalRows = New-Object System.Collections.Generic.List[string]
            $headerCells = @(Get-MarkdownTableCells -Line $line)
            $expectedCellCount = $headerCells.Count
            $canonicalRows.Add((Convert-CanonicalTableCellsToRow -Cells @($headerCells | ForEach-Object { Normalize-CanonicalTableCellText -Text $_ })))
            $i += 2

            while ($i -lt $lines.Count -and (Test-IsLikelyMarkdownTableDataRow -Line $lines[$i] -ExpectedCellCount $expectedCellCount)) {
                $canonicalRows.Add((Convert-CanonicalTableCellsToRow -Cells @(Get-MarkdownTableCells -Line $lines[$i] | ForEach-Object { Normalize-CanonicalTableCellText -Text $_ })))
                $i++
            }

            $output.Add('[TABLE]')
            foreach ($canonicalRow in $canonicalRows) {
                $output.Add($canonicalRow)
            }
            $output.Add('[/TABLE]')
            continue
        }

        $output.Add($line)
        $i++
    }

    return $output -join "`n"
}

function Normalize-NotionSyncText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [bool]$StripRepoOnlyPageId
    )

    $normalized = $Text -replace "`r`n?", "`n"
    $normalized = [regex]::Replace($normalized, "^\uFEFF", '')
    $normalized = $normalized.Replace([char]0x00A0, ' ')

    if ($StripRepoOnlyPageId) {
        $normalized = [regex]::Replace($normalized, '(?m)^\s*<!--\s*Notion Page ID:\s*.*?-->\s*\n?', '')
    }

    $normalized = Convert-HtmlTablesToCanonical -Text $normalized
    $normalized = Convert-MarkdownTablesToCanonical -Text $normalized

    $normalizedLines = $normalized -split "`n"
    $previousNonBlankLines = New-Object 'string[]' $normalizedLines.Count
    $nextNonBlankLines = New-Object 'string[]' $normalizedLines.Count
    $normalizedOutput = New-Object System.Collections.Generic.List[string]
    $inFence = $false
    $fenceMarker = ''

    $lastNonBlankLine = ''
    for ($i = 0; $i -lt $normalizedLines.Count; $i++) {
        $previousNonBlankLines[$i] = $lastNonBlankLine
        if ($normalizedLines[$i].Trim().Length -gt 0) {
            $lastNonBlankLine = [regex]::Replace($normalizedLines[$i], '[ \t]+$', '')
        }
    }

    $nextNonBlankLine = ''
    for ($i = $normalizedLines.Count - 1; $i -ge 0; $i--) {
        $nextNonBlankLines[$i] = $nextNonBlankLine
        if ($normalizedLines[$i].Trim().Length -gt 0) {
            $nextNonBlankLine = [regex]::Replace($normalizedLines[$i], '[ \t]+$', '')
        }
    }

    for ($i = 0; $i -lt $normalizedLines.Count; $i++) {
        $rawLine = $normalizedLines[$i]
        $rawLineWithoutTrailingWhitespace = [regex]::Replace($rawLine, '[ \t]+$', '')
        $previousNonBlankRawLine = $previousNonBlankLines[$i]
        $previousLineWasBlank = ($i -gt 0) -and ($normalizedLines[$i - 1].Trim().Length -eq 0)

        $isNestedListLine = Test-IsNestedMarkdownListLine -Line $rawLineWithoutTrailingWhitespace -PreviousNonBlankLine $previousNonBlankRawLine -PreviousLineWasBlank $previousLineWasBlank
        $isIndentedCode = (
            ($rawLine -match '^(?: {4}|\t)') -and
            (-not $isNestedListLine)
        )
        $fenceState = Update-MarkdownFenceState -Line $rawLineWithoutTrailingWhitespace -InFence $inFence -FenceMarker $fenceMarker
        $inFence = $fenceState.InFence
        $fenceMarker = $fenceState.FenceMarker

        if ($fenceState.IsFenceLine) {
            $normalizedOutput.Add($rawLineWithoutTrailingWhitespace)
            continue
        }

        if ($inFence) {
            $normalizedOutput.Add($rawLine)
            continue
        }

        $line = $rawLineWithoutTrailingWhitespace

        if (-not $isIndentedCode) {
            if ($line -match '^\s*(?:[-*+]|\d+\.)\s+') {
                $line = Normalize-MarkdownListIndentation -Line $line
            } else {
                $line = $line -replace "`t", '  '
            }

            $line = Normalize-QuotedFenceMarkers -Line $line
            $line = Normalize-BlockquoteSpacing -Line $line
            $line = Normalize-BlockquoteListMarkers -Line $line
            $line = Normalize-MarkdownLinksOutsideCode -Text $line
            $line = Normalize-SpacedArrowEscapesOutsideCode -Text $line

            if ($line.Trim() -eq '>') {
                $line = ''
            }
        } else {
            $line = $line -replace "`t", '  '
        }

        if ($line.Trim().Length -eq 0) {
            $previousNonBlank = $previousNonBlankLines[$i]
            $nextNonBlank = $nextNonBlankLines[$i]

            if (
                (($previousNonBlank.Length -gt 0) -and (Test-IsOptionalBlankNeighborLine -Line $previousNonBlank)) -or
                (($nextNonBlank.Length -gt 0) -and (Test-IsOptionalBlankNeighborLine -Line $nextNonBlank))
            ) {
                continue
            }

            if ($normalizedOutput.Count -eq 0 -or $normalizedOutput[$normalizedOutput.Count - 1] -eq '') {
                continue
            }

            $normalizedOutput.Add('')
            continue
        }

        $normalizedOutput.Add($line)
    }

    return ($normalizedOutput -join "`n").Trim()
}

function Read-Utf8Text {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $encoding = [System.Text.UTF8Encoding]::new($false, $true)
    return $encoding.GetString($bytes)
}

function Get-FirstDiff {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Left,

        [Parameter(Mandatory = $true)]
        [string]$Right
    )

    $leftLines = $Left -split "`n"
    $rightLines = $Right -split "`n"
    $max = [Math]::Max($leftLines.Length, $rightLines.Length)

    for ($i = 0; $i -lt $max; $i++) {
        $leftLine = if ($i -lt $leftLines.Length) { $leftLines[$i] } else { '<missing>' }
        $rightLine = if ($i -lt $rightLines.Length) { $rightLines[$i] } else { '<missing>' }

        if ($leftLine -cne $rightLine) {
            return [pscustomobject]@{
                Line   = $i + 1
                Local  = $leftLine
                Remote = $rightLine
            }
        }
    }

    return $null
}

$localRaw = Read-Utf8Text -Path $LocalFile
$remoteRaw = Read-Utf8Text -Path $RemoteFile

if ($remoteRaw -match '<!--\s*Notion Page ID: .*?-->') {
    throw "Live content still contains the repo-only Notion Page ID comment."
}

$localNormalized = Normalize-NotionSyncText -Text $localRaw -StripRepoOnlyPageId $true
$remoteNormalized = Normalize-NotionSyncText -Text $remoteRaw -StripRepoOnlyPageId $false

if ($localNormalized -cne $remoteNormalized) {
    $diff = Get-FirstDiff -Left $localNormalized -Right $remoteNormalized
    $message = "Notion sync parity failed between '$LocalFile' and '$RemoteFile'."

    if ($null -ne $diff) {
        $message += " First difference at line $($diff.Line). Local: $($diff.Local) | Remote: $($diff.Remote)"
    }

    throw $message
}

Write-Output "Notion sync parity OK: $LocalFile <-> $RemoteFile"
