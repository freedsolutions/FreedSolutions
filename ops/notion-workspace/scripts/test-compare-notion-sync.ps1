param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$compareScript = Join-Path $scriptDir 'compare-notion-sync.ps1'
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("notion-sync-test-" + [guid]::NewGuid().ToString())

New-Item -ItemType Directory -Path $tempDir | Out-Null

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content,

        [Parameter(Mandatory = $false)]
        [bool]$WithBom = $false
    )

    $encoding = [System.Text.UTF8Encoding]::new($WithBom)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Expect-Pass {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Local,

        [Parameter(Mandatory = $true)]
        [string]$Remote
    )

    try {
        & $compareScript -LocalFile $Local -RemoteFile $Remote | Out-Null
    }
    catch {
        throw "Expected pass for '$Name' but failed: $($_.Exception.Message)"
    }
}

function Expect-Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Local,

        [Parameter(Mandatory = $true)]
        [string]$Remote
    )

    $failed = $false

    try {
        & $compareScript -LocalFile $Local -RemoteFile $Remote | Out-Null
    }
    catch {
        $failed = $true
    }

    if (-not $failed) {
        throw "Expected failure for '$Name' but the comparison passed."
    }
}

try {
    $local1 = Join-Path $tempDir 'local-lf.md'
    $remote1 = Join-Path $tempDir 'remote-crlf.md'
    Write-Utf8File -Path $local1 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote1 -Content "# Title`r`nBody`r`n"
    Expect-Pass -Name 'line-ending-normalization' -Local $local1 -Remote $remote1

    $local2 = Join-Path $tempDir 'local-comment.md'
    $remote2 = Join-Path $tempDir 'remote-comment.md'
    Write-Utf8File -Path $local2 -Content "<!-- Notion Page ID: 123 -->`n`n# Title`nBody`n" -WithBom $true
    Write-Utf8File -Path $remote2 -Content "# Title`nBody`n"
    Expect-Pass -Name 'repo-only-comment-strip' -Local $local2 -Remote $remote2

    $local2b = Join-Path $tempDir 'local-comment-tight.md'
    $remote2b = Join-Path $tempDir 'remote-comment-tight.md'
    Write-Utf8File -Path $local2b -Content "<!-- Notion Page ID: 123-->`n# Title`nBody`n"
    Write-Utf8File -Path $remote2b -Content "# Title`nBody`n"
    Expect-Pass -Name 'repo-only-comment-strip-tight-close' -Local $local2b -Remote $remote2b

    $local3 = Join-Path $tempDir 'local-case.md'
    $remote3 = Join-Path $tempDir 'remote-case.md'
    Write-Utf8File -Path $local3 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote3 -Content "# Title`nbody`n"
    Expect-Fail -Name 'case-sensitive-diff' -Local $local3 -Remote $remote3

    $local4 = Join-Path $tempDir 'local-remote-comment.md'
    $remote4 = Join-Path $tempDir 'remote-remote-comment.md'
    Write-Utf8File -Path $local4 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote4 -Content "<!-- Notion Page ID: 123 -->`n# Title`nBody`n"
    Expect-Fail -Name 'live-comment-detection' -Local $local4 -Remote $remote4

    $local5 = Join-Path $tempDir 'local-whitespace.md'
    $remote5 = Join-Path $tempDir 'remote-whitespace.md'
    Write-Utf8File -Path $local5 -Content "# Title`n`tBody  `n`n`nTail`n"
    Write-Utf8File -Path $remote5 -Content "# Title`n  Body`n`nTail`n"
    Expect-Pass -Name 'tab-trailing-space-normalization' -Local $local5 -Remote $remote5

    $local5b = Join-Path $tempDir 'local-blank-lines.md'
    $remote5b = Join-Path $tempDir 'remote-blank-lines.md'
    Write-Utf8File -Path $local5b -Content "# Title`n`n`n`nBody`n"
    Write-Utf8File -Path $remote5b -Content "# Title`n`nBody`n"
    Expect-Pass -Name 'blank-line-normalization' -Local $local5b -Remote $remote5b

    $local6 = Join-Path $tempDir 'local-remote-bom.md'
    $remote6 = Join-Path $tempDir 'remote-remote-bom.md'
    Write-Utf8File -Path $local6 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote6 -Content "# Title`nBody`n" -WithBom $true
    Expect-Pass -Name 'remote-bom-normalization' -Local $local6 -Remote $remote6

    $local7 = Join-Path $tempDir 'local-unicode.md'
    $remote7 = Join-Path $tempDir 'remote-unicode.md'
    Write-Utf8File -Path $local7 -Content "# Title`nCafe - launch 🚀`n"
    Write-Utf8File -Path $remote7 -Content "# Title`nCafe - launch 🚀`n"
    Expect-Pass -Name 'unicode-utf8-read' -Local $local7 -Remote $remote7

    $local8 = Join-Path $tempDir 'local-nbsp.md'
    $remote8 = Join-Path $tempDir 'remote-nbsp.md'
    Write-Utf8File -Path $local8 -Content "# Title`nAlpha Beta`n"
    Write-Utf8File -Path $remote8 -Content ("# Title`nAlpha" + [char]0x00A0 + "Beta`n")
    Expect-Pass -Name 'nbsp-normalization' -Local $local8 -Remote $remote8

    $local9 = Join-Path $tempDir 'local-markdown-table.md'
    $remote9 = Join-Path $tempDir 'remote-html-table.md'
    Write-Utf8File -Path $local9 -Content "# Title`n`n| Property | Value |`n| --- | --- |`n| Foo | Bar |`n"
    Write-Utf8File -Path $remote9 -Content "# Title`n<table header-row=`"true`">`n<tr>`n<td>Property</td>`n<td>Value</td>`n</tr>`n<tr>`n<td>Foo</td>`n<td>Bar</td>`n</tr>`n</table>`n"
    Expect-Pass -Name 'markdown-html-table-normalization' -Local $local9 -Remote $remote9

    $local10 = Join-Path $tempDir 'local-arrow.md'
    $remote10 = Join-Path $tempDir 'remote-arrow.md'
    Write-Utf8File -Path $local10 -Content "# Title`nStep -> Done`n"
    Write-Utf8File -Path $remote10 -Content "# Title`nStep -\> Done`n"
    Expect-Pass -Name 'escaped-arrow-normalization' -Local $local10 -Remote $remote10

    $local11 = Join-Path $tempDir 'local-single-blank.md'
    $remote11 = Join-Path $tempDir 'remote-no-blank.md'
    Write-Utf8File -Path $local11 -Content "# Title`n`nBody`n"
    Write-Utf8File -Path $remote11 -Content "# Title`nBody`n"
    Expect-Pass -Name 'single-blank-line-normalization' -Local $local11 -Remote $remote11

    $local11b = Join-Path $tempDir 'local-list-lead-in.md'
    $remote11b = Join-Path $tempDir 'remote-list-lead-in-blank.md'
    Write-Utf8File -Path $local11b -Content "Checklist:`n- One`n- Two`n"
    Write-Utf8File -Path $remote11b -Content "Checklist:`n`n- One`n- Two`n"
    Expect-Pass -Name 'list-lead-in-blank-line-normalization' -Local $local11b -Remote $remote11b

    $local11c = Join-Path $tempDir 'local-nested-list-tab.md'
    $remote11c = Join-Path $tempDir 'remote-nested-list-spaces.md'
    Write-Utf8File -Path $local11c -Content ("1. Parent`n`t- Child`n")
    Write-Utf8File -Path $remote11c -Content ("1. Parent`n    - Child`n")
    Expect-Pass -Name 'nested-list-indentation-normalization' -Local $local11c -Remote $remote11c

    $local11c2 = Join-Path $tempDir 'local-indented-dash-code.md'
    $remote11c2 = Join-Path $tempDir 'remote-top-level-dash-list.md'
    Write-Utf8File -Path $local11c2 -Content ("Example:`n    - dash-in-code`n")
    Write-Utf8File -Path $remote11c2 -Content ("Example:`n- dash-in-code`n")
    Expect-Fail -Name 'indented-dash-code-preserved' -Local $local11c2 -Remote $remote11c2

    $local11c3 = Join-Path $tempDir 'local-indented-number-code.md'
    $remote11c3 = Join-Path $tempDir 'remote-top-level-number-list.md'
    Write-Utf8File -Path $local11c3 -Content ("Example:`n    1. number-in-code`n")
    Write-Utf8File -Path $remote11c3 -Content ("Example:`n1. number-in-code`n")
    Expect-Fail -Name 'indented-number-code-preserved' -Local $local11c3 -Remote $remote11c3

    $local11c4 = Join-Path $tempDir 'local-list-context-indented-code.md'
    $remote11c4 = Join-Path $tempDir 'remote-list-context-indented-code.md'
    Write-Utf8File -Path $local11c4 -Content ("- Parent`n    - code-lookalike`n")
    Write-Utf8File -Path $remote11c4 -Content ("- Parent`n- code-lookalike`n")
    Expect-Fail -Name 'list-context-indented-code-preserved' -Local $local11c4 -Remote $remote11c4

    $local11d = Join-Path $tempDir 'local-ordered-list-number.md'
    $remote11d = Join-Path $tempDir 'remote-ordered-list-number.md'
    Write-Utf8File -Path $local11d -Content ("13. Parent`n")
    Write-Utf8File -Path $remote11d -Content ("1. Parent`n")
    Expect-Pass -Name 'ordered-list-number-normalization' -Local $local11d -Remote $remote11d

    $local11d2 = Join-Path $tempDir 'local-nested-ordered-list-number.md'
    $remote11d2 = Join-Path $tempDir 'remote-nested-ordered-list-number.md'
    Write-Utf8File -Path $local11d2 -Content ("- Parent`n    7. Child`n")
    Write-Utf8File -Path $remote11d2 -Content ("- Parent`n    1. Child`n")
    Expect-Pass -Name 'nested-ordered-list-number-normalization' -Local $local11d2 -Remote $remote11d2

    $local11d3 = Join-Path $tempDir 'local-multi-level-nested-list-tabs.md'
    $remote11d3 = Join-Path $tempDir 'remote-multi-level-nested-list-spaces.md'
    Write-Utf8File -Path $local11d3 -Content ("- Parent`n`t- Child`n`t`t- Grandchild`n")
    Write-Utf8File -Path $remote11d3 -Content ("- Parent`n    - Child`n        - Grandchild`n")
    Expect-Pass -Name 'multi-level-nested-list-depth-preserved' -Local $local11d3 -Remote $remote11d3

    $local11e = Join-Path $tempDir 'local-code-fence-spacing.md'
    $remote11e = Join-Path $tempDir 'remote-code-fence-spacing.md'
    Write-Utf8File -Path $local11e -Content ('```text' + "`n" + 'Body' + "`n" + '```' + "`n")
    Write-Utf8File -Path $remote11e -Content ("`n" + '```text' + "`n" + 'Body' + "`n" + '```' + "`n")
    Expect-Pass -Name 'code-fence-blank-line-normalization' -Local $local11e -Remote $remote11e

    $local11f = Join-Path $tempDir 'local-bold-lead-in.md'
    $remote11f = Join-Path $tempDir 'remote-bold-lead-in-blank.md'
    Write-Utf8File -Path $local11f -Content ("**Tier 2: Full Contacts DB (fallback)**`nIf Tier 1 fails.`n")
    Write-Utf8File -Path $remote11f -Content ("**Tier 2: Full Contacts DB (fallback)**`n`nIf Tier 1 fails.`n")
    Expect-Pass -Name 'bold-lead-in-blank-line-normalization' -Local $local11f -Remote $remote11f

    $local11g = Join-Path $tempDir 'local-empty-blockquote-line.md'
    $remote11g = Join-Path $tempDir 'remote-empty-blockquote-line.md'
    Write-Utf8File -Path $local11g -Content (">`n> **Grouped as 1 Action Item:**`n")
    Write-Utf8File -Path $remote11g -Content ("`n> **Grouped as 1 Action Item:**`n")
    Expect-Pass -Name 'empty-blockquote-line-normalization' -Local $local11g -Remote $remote11g

    $local11h = Join-Path $tempDir 'local-blockquote-fence.md'
    $remote11h = Join-Path $tempDir 'remote-blockquote-fence.md'
    Write-Utf8File -Path $local11h -Content (('>   ' + '```') + "`n" + '>   body' + "`n" + ('>   ' + '```') + "`n")
    Write-Utf8File -Path $remote11h -Content ('> `' + "`n`n" + '>   body' + "`n`n" + '> `' + "`n")
    Expect-Pass -Name 'blockquote-fence-normalization' -Local $local11h -Remote $remote11h

    $local11i = Join-Path $tempDir 'local-blockquote-spacing.md'
    $remote11i = Join-Path $tempDir 'remote-blockquote-spacing.md'
    Write-Utf8File -Path $local11i -Content ('>   ## Sub-tasks' + "`n")
    Write-Utf8File -Path $remote11i -Content ('> ## Sub-tasks' + "`n")
    Expect-Pass -Name 'blockquote-spacing-normalization' -Local $local11i -Remote $remote11i

    $local11j = Join-Path $tempDir 'local-blockquote-list.md'
    $remote11j = Join-Path $tempDir 'remote-blockquote-list.md'
    Write-Utf8File -Path $local11j -Content ('>   - Child' + "`n")
    Write-Utf8File -Path $remote11j -Content ('> - Child' + "`n")
    Expect-Pass -Name 'blockquote-list-normalization' -Local $local11j -Remote $remote11j

    $local11k = Join-Path $tempDir 'local-blockquote-ordered-list.md'
    $remote11k = Join-Path $tempDir 'remote-blockquote-ordered-list.md'
    Write-Utf8File -Path $local11k -Content ('>   7. Child' + "`n")
    Write-Utf8File -Path $remote11k -Content ('> 1. Child' + "`n")
    Expect-Pass -Name 'blockquote-ordered-list-normalization' -Local $local11k -Remote $remote11k

    $local12 = Join-Path $tempDir 'local-escaped-pipe.md'
    $remote12 = Join-Path $tempDir 'remote-escaped-pipe.md'
    Write-Utf8File -Path $local12 -Content "| Name | Value |`n| --- | --- |`n| Foo \| Bar | Baz |`n"
    Write-Utf8File -Path $remote12 -Content "<table><tr><td>Name</td><td>Value</td></tr><tr><td>Foo | Bar</td><td>Baz</td></tr></table>`n"
    Expect-Pass -Name 'escaped-pipe-table-normalization' -Local $local12 -Remote $remote12

    $local13 = Join-Path $tempDir 'local-html-decode.md'
    $remote13 = Join-Path $tempDir 'remote-html-decode.md'
    Write-Utf8File -Path $local13 -Content "| Name | Value |`n| --- | --- |`n| A & B | C |`n"
    Write-Utf8File -Path $remote13 -Content "<table><tr><td>Name</td><td>Value</td></tr><tr><td>A &amp; B</td><td>C</td></tr></table>`n"
    Expect-Pass -Name 'html-decode-table-normalization' -Local $local13 -Remote $remote13

    $local14 = Join-Path $tempDir 'local-code-fence.md'
    $remote14 = Join-Path $tempDir 'remote-code-fence.md'
    $codeFenceSample = '```md' + "`n" + '| not | a table |' + "`n" + '| --- | --- |' + "`n" + '```'
    Write-Utf8File -Path $local14 -Content $codeFenceSample
    Write-Utf8File -Path $remote14 -Content $codeFenceSample
    Expect-Pass -Name 'fenced-code-table-safety' -Local $local14 -Remote $remote14

    $local15 = Join-Path $tempDir 'local-table-followed-by-pipe-paragraph.md'
    $remote15 = Join-Path $tempDir 'remote-table-followed-by-pipe-paragraph.md'
    Write-Utf8File -Path $local15 -Content "| Name | Value |`n| --- | --- |`n| Foo | Bar |`nA|B`n"
    Write-Utf8File -Path $remote15 -Content "<table><tr><td>Name</td><td>Value</td></tr><tr><td>Foo</td><td>Bar</td></tr></table>`nA|B`n"
    Expect-Pass -Name 'table-followed-by-pipe-paragraph' -Local $local15 -Remote $remote15

    $local16 = Join-Path $tempDir 'local-code-fence-arrow.md'
    $remote16 = Join-Path $tempDir 'remote-code-fence-arrow.md'
    Write-Utf8File -Path $local16 -Content ('```md' + "`n" + 'Step -> Done' + "`n" + '```')
    Write-Utf8File -Path $remote16 -Content ('```md' + "`n" + 'Step -\> Done' + "`n" + '```')
    Expect-Fail -Name 'code-fence-arrow-preserved' -Local $local16 -Remote $remote16

    $local17 = Join-Path $tempDir 'local-no-trailing-pipe.md'
    $remote17 = Join-Path $tempDir 'remote-no-trailing-pipe.md'
    Write-Utf8File -Path $local17 -Content "Name | Value`n--- | ---`nFoo | Bar`n"
    Write-Utf8File -Path $remote17 -Content "<table><tr><td>Name</td><td>Value</td></tr><tr><td>Foo</td><td>Bar</td></tr></table>`n"
    Expect-Pass -Name 'no-trailing-pipe-table-normalization' -Local $local17 -Remote $remote17

    $local18 = Join-Path $tempDir 'local-link-cell.md'
    $remote18 = Join-Path $tempDir 'remote-link-cell.md'
    Write-Utf8File -Path $local18 -Content "| Label | Value |`n| --- | --- |`n| [Settings](https://example.com) | Done |`n"
    Write-Utf8File -Path $remote18 -Content "<table><tr><td>Label</td><td>Value</td></tr><tr><td><a href=`"https://example.com`">Settings</a></td><td>Done</td></tr></table>`n"
    Expect-Pass -Name 'link-cell-normalization' -Local $local18 -Remote $remote18

    $local19 = Join-Path $tempDir 'local-indented-code-arrow.md'
    $remote19 = Join-Path $tempDir 'remote-indented-code-arrow.md'
    Write-Utf8File -Path $local19 -Content ('    Step -> Done' + "`n")
    Write-Utf8File -Path $remote19 -Content ('    Step -\> Done' + "`n")
    Expect-Fail -Name 'indented-code-arrow-preserved' -Local $local19 -Remote $remote19

    $local19b = Join-Path $tempDir 'local-tab-indented-code-arrow.md'
    $remote19b = Join-Path $tempDir 'remote-tab-indented-code-arrow.md'
    Write-Utf8File -Path $local19b -Content ("`tStep -> Done`n")
    Write-Utf8File -Path $remote19b -Content ("`tStep -\> Done`n")
    Expect-Fail -Name 'tab-indented-code-arrow-preserved' -Local $local19b -Remote $remote19b

    $local19c = Join-Path $tempDir 'local-indented-markdown-table-code.md'
    $remote19c = Join-Path $tempDir 'remote-indented-markdown-table-code.md'
    $indentedMarkdownTable = '    | not | a table |' + "`n" + '    | --- | --- |' + "`n" + '    | code | block |' + "`n"
    Write-Utf8File -Path $local19c -Content $indentedMarkdownTable
    Write-Utf8File -Path $remote19c -Content $indentedMarkdownTable
    Expect-Pass -Name 'indented-markdown-table-safety' -Local $local19c -Remote $remote19c

    $local19d = Join-Path $tempDir 'local-indented-html-table-code.md'
    $remote19d = Join-Path $tempDir 'remote-indented-html-table-code.md'
    $indentedHtmlTable = '    <table>' + "`n" + '    <tr><td>Name</td><td>Value</td></tr>' + "`n" + '    <tr><td>Foo</td><td>Bar</td></tr>' + "`n" + '    </table>' + "`n"
    Write-Utf8File -Path $local19d -Content $indentedHtmlTable
    Write-Utf8File -Path $remote19d -Content $indentedHtmlTable
    Expect-Pass -Name 'indented-html-table-safety' -Local $local19d -Remote $remote19d

    $local20 = Join-Path $tempDir 'local-inline-code-pipe-table.md'
    $remote20 = Join-Path $tempDir 'remote-inline-code-pipe-table.md'
    Write-Utf8File -Path $local20 -Content ('| Name | Value |' + "`n" + '| --- | --- |' + "`n" + '| `A|B` | C |' + "`n")
    Write-Utf8File -Path $remote20 -Content "<table><tr><td>Name</td><td>Value</td></tr><tr><td>A|B</td><td>C</td></tr></table>`n"
    Expect-Pass -Name 'inline-code-pipe-table-normalization' -Local $local20 -Remote $remote20

    $local20b = Join-Path $tempDir 'local-inline-code-angle-table.md'
    $remote20b = Join-Path $tempDir 'remote-inline-code-angle-table.md'
    Write-Utf8File -Path $local20b -Content ('| Name | Value |' + "`n" + '| --- | --- |' + "`n" + '| `<Config>` | C |' + "`n")
    Write-Utf8File -Path $remote20b -Content ('<table><tr><td>Name</td><td>Value</td></tr><tr><td><code>&lt;Config&gt;</code></td><td>C</td></tr></table>' + "`n")
    Expect-Pass -Name 'inline-code-angle-brackets-table-normalization' -Local $local20b -Remote $remote20b

    $local20c = Join-Path $tempDir 'local-autolink-table.md'
    $remote20c = Join-Path $tempDir 'remote-autolink-table.md'
    Write-Utf8File -Path $local20c -Content ('| Label | Value |' + "`n" + '| --- | --- |' + "`n" + '| Link | <https://example.com/docs(test)> |' + "`n")
    Write-Utf8File -Path $remote20c -Content ('<table><tr><td>Label</td><td>Value</td></tr><tr><td>Link</td><td><a href="https://example.com/docs(test)">https://example.com/docs(test)</a></td></tr></table>' + "`n")
    Expect-Pass -Name 'autolink-table-normalization' -Local $local20c -Remote $remote20c

    $local20d = Join-Path $tempDir 'local-email-autolink-table.md'
    $remote20d = Join-Path $tempDir 'remote-email-autolink-table.md'
    Write-Utf8File -Path $local20d -Content ('| Label | Value |' + "`n" + '| --- | --- |' + "`n" + '| Email | <adam@example.com> |' + "`n")
    Write-Utf8File -Path $remote20d -Content ('<table><tr><td>Label</td><td>Value</td></tr><tr><td>Email</td><td><a href="mailto:adam@example.com">adam@example.com</a></td></tr></table>' + "`n")
    Expect-Pass -Name 'email-autolink-table-normalization' -Local $local20d -Remote $remote20d

    $local20d2 = Join-Path $tempDir 'local-email-list.md'
    $remote20d2 = Join-Path $tempDir 'remote-email-list.md'
    Write-Utf8File -Path $local20d2 -Content ('- adam@example.com' + "`n")
    Write-Utf8File -Path $remote20d2 -Content ('- [adam@example.com](mailto:adam@example.com)' + "`n")
    Expect-Pass -Name 'email-list-mailto-normalization' -Local $local20d2 -Remote $remote20d2

    $local20d3 = Join-Path $tempDir 'local-domain-list.md'
    $remote20d3 = Join-Path $tempDir 'remote-domain-list.md'
    Write-Utf8File -Path $local20d3 -Content ('- Any email ending in @resource.calendar.google.com' + "`n")
    Write-Utf8File -Path $remote20d3 -Content ('- Any email ending in @[resource.calendar.google.com](http://resource.calendar.google.com)' + "`n")
    Expect-Pass -Name 'domain-link-list-normalization' -Local $local20d3 -Remote $remote20d3

    $local20d5 = Join-Path $tempDir 'local-inline-link-paragraph.md'
    $remote20d5 = Join-Path $tempDir 'remote-inline-link-paragraph.md'
    Write-Utf8File -Path $local20d5 -Content ('See [Settings](https://example.com)' + "`n")
    Write-Utf8File -Path $remote20d5 -Content ('See Settings' + "`n")
    Expect-Pass -Name 'inline-link-paragraph-normalization' -Local $local20d5 -Remote $remote20d5

    $local20d6 = Join-Path $tempDir 'local-inline-link-parentheses.md'
    $remote20d6 = Join-Path $tempDir 'remote-inline-link-parentheses.md'
    Write-Utf8File -Path $local20d6 -Content ('See [Docs](https://example.com/docs(test))' + "`n")
    Write-Utf8File -Path $remote20d6 -Content ('See Docs' + "`n")
    Expect-Pass -Name 'inline-link-parentheses-normalization' -Local $local20d6 -Remote $remote20d6

    $local20d7 = Join-Path $tempDir 'local-escaped-backticks.md'
    $remote20d7 = Join-Path $tempDir 'remote-escaped-backticks.md'
    Write-Utf8File -Path $local20d7 -Content ('Keep \`not code\` and [Docs](https://example.com)' + "`n")
    Write-Utf8File -Path $remote20d7 -Content ('Keep \`not code\` and Docs' + "`n")
    Expect-Pass -Name 'escaped-backticks-not-code' -Local $local20d7 -Remote $remote20d7

    $local20e = Join-Path $tempDir 'local-emphasis-table.md'
    $remote20e = Join-Path $tempDir 'remote-emphasis-table.md'
    Write-Utf8File -Path $local20e -Content ('| Label | Value |' + "`n" + '| --- | --- |' + "`n" + '| *Focus* | **Done** |' + "`n")
    Write-Utf8File -Path $remote20e -Content ('<table><tr><td>Label</td><td>Value</td></tr><tr><td><em>Focus</em></td><td><strong>Done</strong></td></tr></table>' + "`n")
    Expect-Pass -Name 'emphasis-table-normalization' -Local $local20e -Remote $remote20e

    $local20f = Join-Path $tempDir 'local-arrow-no-space.md'
    $remote20f = Join-Path $tempDir 'remote-arrow-no-space.md'
    Write-Utf8File -Path $local20f -Content ('A->B' + "`n")
    Write-Utf8File -Path $remote20f -Content ('A-\>B' + "`n")
    Expect-Pass -Name 'arrow-no-space-normalization' -Local $local20f -Remote $remote20f

    $local20g = Join-Path $tempDir 'local-arrow-multi-space.md'
    $remote20g = Join-Path $tempDir 'remote-arrow-multi-space.md'
    Write-Utf8File -Path $local20g -Content ('A  ->  B' + "`n")
    Write-Utf8File -Path $remote20g -Content ('A  -\>  B' + "`n")
    Expect-Pass -Name 'arrow-multi-space-normalization' -Local $local20g -Remote $remote20g

    $local20h = Join-Path $tempDir 'local-double-pipe-cell.md'
    $remote20h = Join-Path $tempDir 'remote-double-pipe-cell.md'
    Write-Utf8File -Path $local20h -Content ('| Name | Value |' + "`n" + '| --- | --- |' + "`n" + '| Foo \|\| Bar | Baz |' + "`n")
    Write-Utf8File -Path $remote20h -Content ('<table><tr><td>Name</td><td>Value</td></tr><tr><td>Foo || Bar</td><td>Baz</td></tr></table>' + "`n")
    Expect-Pass -Name 'double-pipe-cell-normalization' -Local $local20h -Remote $remote20h

    $local20i = Join-Path $tempDir 'local-link-label-pipe-table.md'
    $remote20i = Join-Path $tempDir 'remote-link-label-pipe-table.md'
    Write-Utf8File -Path $local20i -Content ('| Label | Value |' + "`n" + '| --- | --- |' + "`n" + '| Link | [A|B](https://example.com) |' + "`n")
    Write-Utf8File -Path $remote20i -Content ('<table><tr><td>Label</td><td>Value</td></tr><tr><td>Link</td><td><a href="https://example.com">A|B</a></td></tr></table>' + "`n")
    Expect-Pass -Name 'link-label-pipe-table-normalization' -Local $local20i -Remote $remote20i

    $local20j = Join-Path $tempDir 'local-empty-cell-table.md'
    $remote20j = Join-Path $tempDir 'remote-empty-cell-table.md'
    Write-Utf8File -Path $local20j -Content ('| Name | Email | Notes |' + "`n" + '| --- | --- | --- |' + "`n" + '| Morgan Carlone | [morgan@primitivgroup.com](mailto:morgan@primitivgroup.com) |  |' + "`n")
    Write-Utf8File -Path $remote20j -Content ('<table><tr><td>Name</td><td>Email</td><td>Notes</td></tr><tr><td>Morgan Carlone</td><td><a href="mailto:morgan@primitivgroup.com">morgan@primitivgroup.com</a></td><td></td></tr></table>' + "`n")
    Expect-Pass -Name 'empty-cell-table-normalization' -Local $local20j -Remote $remote20j

    $local21 = Join-Path $tempDir 'local-uppercase-html-table.md'
    $remote21 = Join-Path $tempDir 'remote-uppercase-html-table.md'
    Write-Utf8File -Path $local21 -Content "| Name | Value |`n| --- | --- |`n| Foo | Bar |`n"
    Write-Utf8File -Path $remote21 -Content "<TABLE><THEAD><TR><TH>Name</TH><TH>Value</TH></TR></THEAD><TBODY><TR><TD>Foo</TD><TD>Bar</TD></TR></TBODY></TABLE>`n"
    Expect-Pass -Name 'uppercase-html-table-normalization' -Local $local21 -Remote $remote21

    $local22 = Join-Path $tempDir 'local-tilde-code-fence.md'
    $remote22 = Join-Path $tempDir 'remote-tilde-code-fence.md'
    $tildeFenceSample = '~~~md' + "`n" + '| not | a table |' + "`n" + '| --- | --- |' + "`n" + '~~~'
    Write-Utf8File -Path $local22 -Content $tildeFenceSample
    Write-Utf8File -Path $remote22 -Content $tildeFenceSample
    Expect-Pass -Name 'tilde-code-fence-table-safety' -Local $local22 -Remote $remote22

    $local23 = Join-Path $tempDir 'local-tilde-code-fence-arrow.md'
    $remote23 = Join-Path $tempDir 'remote-tilde-code-fence-arrow.md'
    Write-Utf8File -Path $local23 -Content ('~~~md' + "`n" + 'Step -> Done' + "`n" + '~~~')
    Write-Utf8File -Path $remote23 -Content ('~~~md' + "`n" + 'Step -\> Done' + "`n" + '~~~')
    Expect-Fail -Name 'tilde-code-fence-arrow-preserved' -Local $local23 -Remote $remote23

    $local24 = Join-Path $tempDir 'local-inline-code-arrow.md'
    $remote24 = Join-Path $tempDir 'remote-inline-code-arrow.md'
    Write-Utf8File -Path $local24 -Content ('# Title' + "`n" + '`Step -> Done`' + "`n")
    Write-Utf8File -Path $remote24 -Content ('# Title' + "`n" + '`Step -\> Done`' + "`n")
    Expect-Fail -Name 'inline-code-arrow-preserved' -Local $local24 -Remote $remote24

    $local25 = Join-Path $tempDir 'local-indented-fenced-code-arrow.md'
    $remote25 = Join-Path $tempDir 'remote-indented-fenced-code-arrow.md'
    Write-Utf8File -Path $local25 -Content ('- Example' + "`n" + '    ```md' + "`n" + '    Step -> Done' + "`n" + '    ```' + "`n")
    Write-Utf8File -Path $remote25 -Content ('- Example' + "`n" + '    ```md' + "`n" + '    Step -\> Done' + "`n" + '    ```' + "`n")
    Expect-Fail -Name 'indented-fenced-code-arrow-preserved' -Local $local25 -Remote $remote25

    $local26 = Join-Path $tempDir 'local-fenced-html-table.md'
    $remote26 = Join-Path $tempDir 'remote-fenced-html-table.md'
    $fencedHtmlTable = '```html' + "`n" + '<table><tr><td>Name</td><td>Value</td></tr><tr><td>Foo</td><td>Bar</td></tr></table>' + "`n" + '```'
    Write-Utf8File -Path $local26 -Content $fencedHtmlTable
    Write-Utf8File -Path $remote26 -Content $fencedHtmlTable
    Expect-Pass -Name 'fenced-html-table-safety' -Local $local26 -Remote $remote26

    $local27 = Join-Path $tempDir 'local-fence-content-open-marker.md'
    $remote27 = Join-Path $tempDir 'remote-fence-content-open-marker.md'
    Write-Utf8File -Path $local27 -Content ('```' + "`n" + '```md' + "`n" + 'Step -> Done' + "`n" + '```' + "`n")
    Write-Utf8File -Path $remote27 -Content ('```' + "`n" + '```md' + "`n" + 'Step -\> Done' + "`n" + '```' + "`n")
    Expect-Fail -Name 'fence-content-open-marker-preserved' -Local $local27 -Remote $remote27

    $local28 = Join-Path $tempDir 'local-tilde-fence-content-open-marker.md'
    $remote28 = Join-Path $tempDir 'remote-tilde-fence-content-open-marker.md'
    Write-Utf8File -Path $local28 -Content ('~~~' + "`n" + '~~~md' + "`n" + 'Step -> Done' + "`n" + '~~~' + "`n")
    Write-Utf8File -Path $remote28 -Content ('~~~' + "`n" + '~~~md' + "`n" + 'Step -\> Done' + "`n" + '~~~' + "`n")
    Expect-Fail -Name 'tilde-fence-content-open-marker-preserved' -Local $local28 -Remote $remote28

    $local29 = Join-Path $tempDir 'local-longer-closing-fence.md'
    $remote29 = Join-Path $tempDir 'remote-longer-closing-fence.md'
    Write-Utf8File -Path $local29 -Content ('```' + "`n" + 'code' + "`n" + '````' + "`n" + 'Step -> Done' + "`n")
    Write-Utf8File -Path $remote29 -Content ('```' + "`n" + 'code' + "`n" + '````' + "`n" + 'Step -\> Done' + "`n")
    Expect-Pass -Name 'longer-closing-fence-normalization' -Local $local29 -Remote $remote29

    $local30 = Join-Path $tempDir 'local-longer-closing-tilde-fence.md'
    $remote30 = Join-Path $tempDir 'remote-longer-closing-tilde-fence.md'
    Write-Utf8File -Path $local30 -Content ('~~~' + "`n" + 'code' + "`n" + '~~~~' + "`n" + 'Step -> Done' + "`n")
    Write-Utf8File -Path $remote30 -Content ('~~~' + "`n" + 'code' + "`n" + '~~~~' + "`n" + 'Step -\> Done' + "`n")
    Expect-Pass -Name 'longer-closing-tilde-fence-normalization' -Local $local30 -Remote $remote30

    $local31 = Join-Path $tempDir 'local-fenced-code-tabs.md'
    $remote31 = Join-Path $tempDir 'remote-fenced-code-tabs.md'
    Write-Utf8File -Path $local31 -Content ('```md' + "`n" + "`tStep -> Done" + "`n" + '```' + "`n")
    Write-Utf8File -Path $remote31 -Content ('```md' + "`n" + '    Step -> Done' + "`n" + '```' + "`n")
    Expect-Fail -Name 'fenced-code-tab-preserved' -Local $local31 -Remote $remote31

    Write-Output 'compare-notion-sync tests passed.'
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
