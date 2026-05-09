[CmdletBinding()]
param(
    [switch]$InstallDeps,
    [switch]$NoBackend,
    [switch]$NoFrontend,
    [switch]$NoDiagnostics,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogsDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

function Write-Step {
    param([string]$Message)
    Write-Host "[WNRT] $Message"
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WNRT][WARN] $Message" -ForegroundColor Yellow
}

function Test-PortListening {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($null -ne $conn) {
            return $true
        }
    }
    catch {
    }
    try {
        $pattern = "[:\.]$Port\s+.*LISTENING"
        $hit = netstat.exe -ano | Select-String -Pattern $pattern
        return $null -ne $hit
    }
    catch {
        return $false
    }
}

function Get-ListeningPid {
    param([int]$Port)
    try {
        $pattern = "[:\.]$Port\s+.*LISTENING\s+(\d+)"
        $hit = netstat.exe -ano | Select-String -Pattern $pattern | Select-Object -First 1
        if ($hit -and $hit.Matches.Count -gt 0) {
            return [int]$hit.Matches[0].Groups[1].Value
        }
    }
    catch {
    }
    return $null
}

function Get-AvailablePort {
    param([int]$PreferredPort)
    for ($port = $PreferredPort; $port -lt ($PreferredPort + 20); $port++) {
        if (-not (Test-PortListening -Port $port)) {
            return $port
        }
    }
    return $PreferredPort
}

function Resolve-WorkingPython {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:WNRT_PYTHON) {
        $candidates.Add($env:WNRT_PYTHON)
    }
    $candidates.Add((Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"))
    $candidates.Add((Join-Path $RepoRoot ".venv\Scripts\python.exe"))
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $candidates.Add($cmd.Source)
    }

    foreach ($candidate in $candidates) {
        if (-not $candidate) {
            continue
        }
        if (($candidate -like "*.exe") -and -not (Test-Path $candidate)) {
            continue
        }
        try {
            $out = & $candidate -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                return $candidate
            }
        }
        catch {
            continue
        }
    }
    return $null
}

function Resolve-NpmCommand {
    if ($env:WNRT_NPM -and (Test-Path $env:WNRT_NPM)) {
        return $env:WNRT_NPM
    }
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $psCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($psCmd) {
        $cmdSibling = Join-Path (Split-Path $psCmd.Source -Parent) "npm.cmd"
        if (Test-Path $cmdSibling) {
            return $cmdSibling
        }
        return $psCmd.Source
    }
    return $null
}

function Resolve-NodeCommand {
    if ($env:WNRT_NODE -and (Test-Path $env:WNRT_NODE)) {
        return $env:WNRT_NODE
    }
    $cmd = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (Test-Path $bundled) {
        return $bundled
    }
    return $null
}

function Test-BackendDeps {
    param([string]$Python)
    try {
        & $Python -c "import fastapi, uvicorn, jose; print('ok')" 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Run-LoggedCommand {
    param(
        [string]$Name,
        [string]$Exe,
        [string[]]$CommandArgs,
        [string]$WorkingDirectory
    )
    $log = Join-Path $LogsDir "$Name.log"
    Write-Step "Running $Name -> $log"
    Push-Location $WorkingDirectory
    $oldErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Exe @CommandArgs *> $log
        $code = $LASTEXITCODE
    }
    catch {
        $code = 1
        $_ | Out-File -FilePath $log -Append -Encoding utf8
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Warn "$Name exited with code $code. Review $log"
    }
    return $code
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$Exe,
        [string[]]$CommandArgs,
        [string]$WorkingDirectory,
        [int]$Port
    )
    if (Test-PortListening -Port $Port) {
        Write-Step "$Name appears already available on port $Port"
        return $null
    }

    $stdout = Join-Path $LogsDir "one_click_$Name.log"
    $stderr = Join-Path $LogsDir "one_click_$Name.err.log"
    $pidPath = Join-Path $LogsDir "one_click_$Name.pid"
    $cmdPath = Join-Path $LogsDir "one_click_$Name.cmd"
    $launchCmdPath = Join-Path $LogsDir "one_click_$Name.launch.cmd"

    function ConvertTo-CmdQuoted {
        param([string]$Value)
        return '"' + ($Value -replace '"', '""') + '"'
    }

    $parts = New-Object System.Collections.Generic.List[string]
    $parts.Add((ConvertTo-CmdQuoted $Exe))
    foreach ($arg in $CommandArgs) {
        $parts.Add((ConvertTo-CmdQuoted $arg))
    }
    $command = ($parts -join " ")
    Set-Content -Path $stdout -Value @(
        "Started by scripts\start_everything_safe.ps1",
        "Command: $command",
        "WorkingDirectory: $WorkingDirectory",
        "Output: see the minimized dev-server console window",
        "Wrapper: $cmdPath"
    )

    $quotedWorkingDirectory = '"' + ($WorkingDirectory -replace '"', '""') + '"'
    $cmdLines = @(
        "@echo off",
        "cd /d $quotedWorkingDirectory",
        "echo [WNRT] Starting $Name on port $Port",
        $command,
        "echo.",
        "echo [WNRT] $Name exited with errorlevel %ERRORLEVEL%.",
        "pause"
    )
    Set-Content -Path $cmdPath -Value $cmdLines -Encoding ASCII
    $quotedCmdPath = '"' + ($cmdPath -replace '"', '""') + '"'
    $launchLines = @(
        "@echo off",
        "start `"WNRT $Name`" /min `"%ComSpec%`" /d /k call $quotedCmdPath"
    )
    Set-Content -Path $launchCmdPath -Value $launchLines -Encoding ASCII
    $launcher = New-Object System.Diagnostics.ProcessStartInfo
    $launcher.FileName = $launchCmdPath
    $launcher.WorkingDirectory = $LogsDir
    $launcher.UseShellExecute = $true
    $launcher.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    [System.Diagnostics.Process]::Start($launcher) | Out-Null

    Start-Sleep -Seconds 6
    $ownerPid = Get-ListeningPid -Port $Port
    if (Test-PortListening -Port $Port) {
        if ($ownerPid) {
            Set-Content -Path $pidPath -Value ([string]$ownerPid)
            Write-Step "Started $Name listening PID $ownerPid. Launch log: $stdout"
        }
        else {
            Write-Step "Started $Name on port $Port. Launch log: $stdout"
        }
    }
    else {
        if (Test-Path $pidPath) {
            Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        }
        Write-Warn "$Name did not begin listening on port $Port. Review the minimized console window."
    }
    return $ownerPid
}

Write-Step "Repository: $RepoRoot"
$Python = Resolve-WorkingPython
if (-not $Python) {
    throw "No working Python interpreter found. Set WNRT_PYTHON to a valid python.exe."
}
Write-Step "Python: $Python"

if (-not $NoDiagnostics) {
    Run-LoggedCommand -Name "diagnostic_proxy_guard_report" -Exe $Python -CommandArgs @("-m", "proxy_guard", "report", "--json") -WorkingDirectory $RepoRoot | Out-Null
    Run-LoggedCommand -Name "diagnostic_proxy_writer_report" -Exe $Python -CommandArgs @("-m", "proxy_guard", "writer-report", "--json") -WorkingDirectory $RepoRoot | Out-Null
    Run-LoggedCommand -Name "diagnostic_proxy_writer_once" -Exe $Python -CommandArgs @("-m", "proxy_guard", "watch-writer", "--once") -WorkingDirectory $RepoRoot | Out-Null
}

if (-not $NoBackend) {
    $BackendPort = Get-AvailablePort -PreferredPort $BackendPort
    if (-not (Test-BackendDeps -Python $Python)) {
        if ($InstallDeps) {
            Write-Step "Installing backend Python dependencies"
            Run-LoggedCommand -Name "install_backend_deps" -Exe $Python -CommandArgs @("-m", "pip", "install", "-r", "backend\requirements.txt") -WorkingDirectory $RepoRoot | Out-Null
        }
        else {
            Write-Warn "Backend dependencies missing. Re-run with -InstallDeps to install backend\requirements.txt."
        }
    }

    if (Test-BackendDeps -Python $Python) {
        $env:AUTH_BYPASS_USER_ID = "local-demo"
        $env:AUTH_BYPASS_EMAIL = "local-demo@example.com"
        Start-ManagedProcess `
            -Name "backend" `
            -Exe $Python `
            -CommandArgs @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", ([string]$BackendPort)) `
            -WorkingDirectory $RepoRoot `
            -Port $BackendPort | Out-Null
    }
    else {
        Write-Warn "Backend not started because dependencies are unavailable."
    }
}

if (-not $NoFrontend) {
    $FrontendPort = Get-AvailablePort -PreferredPort $FrontendPort
    $Npm = Resolve-NpmCommand
    $Node = Resolve-NodeCommand
    $frontendDir = Join-Path $RepoRoot "frontend"
    $nextCmd = Join-Path $frontendDir "node_modules\.bin\next.cmd"
    $nextJs = Join-Path $frontendDir "node_modules\next\dist\bin\next"
    if (-not $Npm) {
        Write-Warn "npm was not found. Frontend cannot start."
    }
    else {
        Write-Step "npm: $Npm"
        if (-not (Test-Path $nextCmd)) {
            if ($InstallDeps) {
                Write-Step "Installing frontend npm dependencies"
                Run-LoggedCommand -Name "install_frontend_deps" -Exe $Npm -CommandArgs @("install") -WorkingDirectory $frontendDir | Out-Null
            }
            else {
                Write-Warn "Frontend dependencies missing. Re-run with -InstallDeps to run npm install."
            }
        }

        if ((Test-Path $nextCmd) -and (Test-Path $nextJs) -and $Node) {
            Write-Step "node: $Node"
            $env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:$BackendPort"
            $env:NEXT_PUBLIC_PLATFORM_API = "http://127.0.0.1:$BackendPort"
            if (-not $env:NEXT_PUBLIC_SUPABASE_URL) {
                $env:NEXT_PUBLIC_SUPABASE_URL = "http://127.0.0.1:54321"
            }
            if (-not $env:NEXT_PUBLIC_SUPABASE_ANON_KEY) {
                $env:NEXT_PUBLIC_SUPABASE_ANON_KEY = "local-demo-anon-key"
            }
            Start-ManagedProcess `
                -Name "frontend" `
                -Exe $Node `
                -CommandArgs @($nextJs, "dev", "-H", "127.0.0.1", "-p", ([string]$FrontendPort)) `
                -WorkingDirectory $frontendDir `
                -Port $FrontendPort | Out-Null
        }
        else {
            Write-Warn "Frontend not started because node_modules or node.exe is unavailable."
        }
    }
}

Write-Host ""
Write-Step "One-click startup finished."
Write-Host "Backend docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Frontend:     http://127.0.0.1:$FrontendPort"
Write-Host "Logs:         $LogsDir"
Write-Host ""
Write-Host "To stop launcher-managed dev servers:"
Write-Host "  scripts\stop_everything_safe.bat"
