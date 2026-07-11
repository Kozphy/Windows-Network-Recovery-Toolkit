[CmdletBinding()]
param(
    [switch]$ConfirmOverwrite,
    [string]$JsonOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Sha256Hex {
    param([Parameter(Mandatory)][string]$Text)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Write-ResultJson {
    param(
        [Parameter(Mandatory)][hashtable]$Result,
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $Result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$result = [ordered]@{
    schema_version       = '1.0'
    test                 = 'clipboard_text_round_trip'
    status               = 'ERROR'
    expected_sha256      = $null
    actual_sha256        = $null
    expected_length      = 0
    actual_length        = 0
    duration_ms          = 0
    clipboard_restored   = $false
    restore_scope        = 'text-only'
    error_type           = $null
    error_message        = $null
    timestamp_utc        = (Get-Date).ToUniversalTime().ToString('o')
}

if (-not $ConfirmOverwrite) {
    $answer = Read-Host 'This test temporarily replaces the TEXT clipboard and then restores it. Continue? [y/N]'
    if ($answer -notmatch '^(?i:y|yes)$') {
        $result.status = 'SKIPPED'
        Write-ResultJson -Result $result -Path $JsonOutput
        Write-Host 'SKIPPED: Clipboard was not changed.' -ForegroundColor Yellow
        exit 2
    }
}

$originalText = $null
$originalTextReadable = $false
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    try {
        $originalText = Get-Clipboard -Raw -TextFormatType Text
        $originalTextReadable = $true
    }
    catch {
        # The current clipboard may contain only a non-text format.
        $originalTextReadable = $false
    }

    $testText = @(
        'CLIPBOARD_DIAGNOSTIC'
        [guid]::NewGuid().ToString('N')
        'Unicode: 中文 ✓'
    ) -join "`r`n"

    $result.expected_sha256 = Get-Sha256Hex -Text $testText
    $result.expected_length = $testText.Length

    Set-Clipboard -Value $testText
    Start-Sleep -Milliseconds 150
    $actualText = Get-Clipboard -Raw -TextFormatType Text

    if ($null -eq $actualText) {
        $actualText = ''
    }

    # PowerShell clipboard implementations can append a trailing newline.
    $normalizedActual = $actualText.TrimEnd("`r", "`n")
    $result.actual_sha256 = Get-Sha256Hex -Text $normalizedActual
    $result.actual_length = $normalizedActual.Length

    if ($normalizedActual -ceq $testText) {
        $result.status = 'PASS'
    }
    else {
        $result.status = 'FAIL'
    }
}
catch {
    $result.status = 'ERROR'
    $result.error_type = $_.Exception.GetType().FullName
    $result.error_message = $_.Exception.Message
}
finally {
    $stopwatch.Stop()
    $result.duration_ms = $stopwatch.ElapsedMilliseconds

    if ($originalTextReadable) {
        try {
            Set-Clipboard -Value $originalText
            $result.clipboard_restored = $true
        }
        catch {
            $result.clipboard_restored = $false
            if (-not $result.error_message) {
                $result.error_type = $_.Exception.GetType().FullName
                $result.error_message = "Diagnostic completed, but clipboard restoration failed: $($_.Exception.Message)"
            }
        }
    }

    Write-ResultJson -Result $result -Path $JsonOutput
}

switch ($result.status) {
    'PASS' {
        Write-Host 'PASS: Clipboard text round-trip succeeded.' -ForegroundColor Green
        $exitCode = 0
    }
    'FAIL' {
        Write-Host 'FAIL: Clipboard content did not match the test value.' -ForegroundColor Red
        $exitCode = 1
    }
    default {
        Write-Host "ERROR: $($result.error_message)" -ForegroundColor Red
        $exitCode = 3
    }
}

Write-Host "Clipboard restored: $($result.clipboard_restored)"
Write-Host "Duration: $($result.duration_ms) ms"
if ($JsonOutput) {
    Write-Host "Evidence file: $JsonOutput"
}

exit $exitCode
