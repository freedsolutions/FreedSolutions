param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$saveScript = Join-Path $scriptDir 'save-notion-sync-remote.ps1'
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("notion-sync-save-test-" + [guid]::NewGuid().ToString())
$defaultExpectedPath = $null

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

function Expect-EqualBytes {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [byte[]]$Actual,

        [Parameter(Mandatory = $true)]
        [byte[]]$Expected
    )

    if ($Actual.Length -ne $Expected.Length) {
        throw "Expected byte length $($Expected.Length) for '$Name' but got $($Actual.Length)."
    }

    for ($i = 0; $i -lt $Actual.Length; $i++) {
        if ($Actual[$i] -ne $Expected[$i]) {
            throw "Byte mismatch for '$Name' at index $i."
        }
    }
}

function Expect-Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    $failed = $false

    try {
        & $Action | Out-Null
    }
    catch {
        $failed = $true
    }

    if (-not $failed) {
        throw "Expected failure for '$Name' but the command passed."
    }
}

try {
    $literalOutput = Join-Path $tempDir 'literal.md'
    $literalContent = "# Title`nBody with tabs`tand unicode cafe`n"
    & $saveScript -DocSlug 'agent-sops' -LiteralContent $literalContent -OutputPath $literalOutput | Out-Null
    $literalBytes = [System.IO.File]::ReadAllBytes($literalOutput)
    $expectedLiteralBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($literalContent)
    Expect-EqualBytes -Name 'literal-content-save' -Actual $literalBytes -Expected $expectedLiteralBytes

    $sourcePath = Join-Path $tempDir 'source.md'
    $sourceContent = "# Source`r`nBody`r`n"
    Write-Utf8File -Path $sourcePath -Content $sourceContent -WithBom $true
    $sourceOutput = Join-Path $tempDir 'source-output.md'
    & $saveScript -DocSlug 'post-email' -SourceFile $sourcePath -OutputPath $sourceOutput | Out-Null
    $sourceBytes = [System.IO.File]::ReadAllBytes($sourcePath)
    $savedBytes = [System.IO.File]::ReadAllBytes($sourceOutput)
    Expect-EqualBytes -Name 'source-file-byte-copy' -Actual $savedBytes -Expected $sourceBytes

    $wrappedLiteralOutput = Join-Path $tempDir 'wrapped-literal.md'
    $wrappedLiteral = "Header`n<content>`n# Wrapped`nBody`n</content>`nFooter"
    & $saveScript -DocSlug 'wrapped-doc' -LiteralContent $wrappedLiteral -ExtractPageContent -OutputPath $wrappedLiteralOutput | Out-Null
    $wrappedLiteralText = [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($wrappedLiteralOutput))
    if ($wrappedLiteralText -ne "# Wrapped`nBody") {
        throw "Expected literal wrapper extraction to persist only the inner page body."
    }

    $wrappedSourcePath = Join-Path $tempDir 'wrapped-source.md'
    $wrappedSourceText = "Prefix`r`n<content>`r`n# Source Wrapped`r`nBody`r`n</content>`r`nSuffix"
    Write-Utf8File -Path $wrappedSourcePath -Content $wrappedSourceText
    $wrappedSourceOutput = Join-Path $tempDir 'wrapped-source-output.md'
    & $saveScript -DocSlug 'wrapped-source' -SourceFile $wrappedSourcePath -ExtractPageContent -OutputPath $wrappedSourceOutput | Out-Null
    $wrappedSourceOutputText = [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($wrappedSourceOutput))
    if ($wrappedSourceOutputText -ne "# Source Wrapped`r`nBody") {
        throw "Expected source wrapper extraction to preserve the inner page body."
    }

    $wrappedBomSourcePath = Join-Path $tempDir 'wrapped-bom-source.md'
    $wrappedBomSourceText = "Prefix`r`n<content>`r`n# BOM Wrapped`r`nBody`r`n</content>`r`nSuffix"
    Write-Utf8File -Path $wrappedBomSourcePath -Content $wrappedBomSourceText -WithBom $true
    $wrappedBomOutput = Join-Path $tempDir 'wrapped-bom-output.md'
    & $saveScript -DocSlug 'wrapped-bom' -SourceFile $wrappedBomSourcePath -ExtractPageContent -OutputPath $wrappedBomOutput | Out-Null
    $wrappedBomBytes = [System.IO.File]::ReadAllBytes($wrappedBomOutput)
    if ($wrappedBomBytes.Length -ge 3 -and $wrappedBomBytes[0] -eq 0xEF -and $wrappedBomBytes[1] -eq 0xBB -and $wrappedBomBytes[2] -eq 0xBF) {
        throw 'Expected extracted page content to be saved without a UTF-8 BOM.'
    }

    $blankBoundaryOutput = Join-Path $tempDir 'blank-boundary.md'
    $blankBoundaryLiteral = "Header`n<CONTENT>`n`n# Starts blank`nBody`n`n</CONTENT>`nFooter"
    & $saveScript -DocSlug 'blank-boundary' -LiteralContent $blankBoundaryLiteral -ExtractPageContent -OutputPath $blankBoundaryOutput | Out-Null
    $blankBoundaryText = [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($blankBoundaryOutput))
    if ($blankBoundaryText -ne "`n# Starts blank`nBody`n") {
        throw "Expected extraction to remove only the wrapper newline and preserve intentional blank edge lines."
    }

    $overwriteOutput = Join-Path $tempDir 'overwrite.md'
    & $saveScript -DocSlug 'post-meeting' -LiteralContent 'first' -OutputPath $overwriteOutput | Out-Null
    Expect-Fail -Name 'overwrite-without-force' -Action {
        & $saveScript -DocSlug 'post-meeting' -LiteralContent 'second' -OutputPath $overwriteOutput
    }
    & $saveScript -DocSlug 'post-meeting' -LiteralContent 'second' -OutputPath $overwriteOutput -Force | Out-Null
    $overwrittenText = [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($overwriteOutput))
    if ($overwrittenText -ne 'second') {
        throw "Expected overwrite with -Force to persist the new content."
    }

    Expect-Fail -Name 'invalid-doc-slug' -Action {
        & $saveScript -DocSlug 'Agent SOPs' -LiteralContent 'bad slug' -OutputPath (Join-Path $tempDir 'bad-slug.md')
    }

    Expect-Fail -Name 'invalid-date' -Action {
        & $saveScript -DocSlug 'bad-date' -LiteralContent 'bad date' -Date '20260327' -OutputPath (Join-Path $tempDir 'bad-date.md')
    }

    Expect-Fail -Name 'missing-content-block' -Action {
        & $saveScript -DocSlug 'missing-content' -LiteralContent 'no wrapper here' -ExtractPageContent -OutputPath (Join-Path $tempDir 'missing-content.md')
    }

    Expect-Fail -Name 'outside-output-path' -Action {
        & $saveScript -DocSlug 'outside-path' -LiteralContent 'bad path' -OutputPath 'C:\outside-scope\remote.md'
    }

    $repoRootPath = [System.IO.Path]::GetFullPath((Join-Path $scriptDir '..\..\..'))
    $repoNonScratchPath = Join-Path $repoRootPath 'ops\notion-workspace\docs\not-allowed.md'
    Expect-Fail -Name 'repo-non-scratch-output-path-rejected' -Action {
        & $saveScript -DocSlug 'repo-non-scratch' -LiteralContent 'bad repo path' -OutputPath $repoNonScratchPath
    }

    Expect-Fail -Name 'repo-root-output-path-rejected' -Action {
        & $saveScript -DocSlug 'repo-root' -LiteralContent 'bad repo root path' -OutputPath $repoRootPath
    }

    Expect-Fail -Name 'temp-root-output-path-rejected' -Action {
        & $saveScript -DocSlug 'temp-root' -LiteralContent 'bad temp root path' -OutputPath ([System.IO.Path]::GetTempPath())
    }

    $utf16SourcePath = Join-Path $tempDir 'utf16-source.md'
    [System.IO.File]::WriteAllText($utf16SourcePath, "Prefix`r`n<content>`r`n# UTF16`r`nBody`r`n</content>`r`nSuffix", [System.Text.Encoding]::Unicode)
    Expect-Fail -Name 'utf16-source-rejected' -Action {
        & $saveScript -DocSlug 'utf16-source' -SourceFile $utf16SourcePath -ExtractPageContent -OutputPath (Join-Path $tempDir 'utf16-output.md')
    }

    $defaultSlug = ('default-path-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    $defaultDate = '2026-03-27'
    $defaultExpectedPath = Join-Path $repoRootPath ("ops\notion-workspace\tmp\notion-sync-remote-{0}-{1}.md" -f $defaultDate, $defaultSlug)
    $returnedDefaultPath = & $saveScript -DocSlug $defaultSlug -LiteralContent 'default path' -Date $defaultDate -Force
    if ([System.IO.Path]::GetFullPath($returnedDefaultPath) -ne [System.IO.Path]::GetFullPath($defaultExpectedPath)) {
        throw 'Expected the default output path to resolve under ops/notion-workspace/tmp.'
    }
    if (Test-Path -LiteralPath $defaultExpectedPath) {
        Remove-Item -LiteralPath $defaultExpectedPath -Force
    }

    Write-Output 'save-notion-sync-remote tests passed.'
}
finally {
    if ($defaultExpectedPath -and (Test-Path -LiteralPath $defaultExpectedPath)) {
        Remove-Item -LiteralPath $defaultExpectedPath -Force
    }

    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
