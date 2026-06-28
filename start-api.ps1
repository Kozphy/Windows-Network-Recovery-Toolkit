# Start API entrypoint.
#
# Purpose:
# - Always start the backend API through the repo-controlled script.
# - Avoid accidentally using a global uvicorn / Python / Hermes environment from PATH.
# - Fail fast when the requested port is already occupied.
#
# Usage from repo root:
#   .\start-api.ps1
#   .\start-api.ps1 -Reload
#   .\start-api.ps1 -Port 8001
#   .\start-api.ps1 -ListenHost 0.0.0.0 -Port 8000
#
# Safety principle:
# - This script detects port conflicts but does NOT kill processes automatically.
# - The user must explicitly decide whether to change port or stop the occupying process.

param(
    # ListenHost controls where the API binds.
    #
    # 127.0.0.1 means local machine only.
    # This is safer for development because other devices cannot access the API.
    #
    # Use 0.0.0.0 only when you intentionally want other machines on the network
    # to reach this API.
    [string]$ListenHost = "127.0.0.1",

    # Default API port.
    #
    # Common FastAPI / uvicorn development port is 8000.
    # If this port is occupied, run:
    #   .\start-api.ps1 -Port 8001
    [int]$Port = 8000,

    # Enables development reload mode.
    #
    # When enabled, backend changes may automatically restart the server.
    # Useful during development, but not recommended for stable demo/review runs.
    [switch]$Reload
)

# Check whether the requested TCP port is already listening.
#
# This prevents confusing failures such as:
# - "address already in use"
# - "[Errno 10048] Only one usage of each socket address is normally permitted"
#
# ErrorAction SilentlyContinue avoids noisy errors when no listener exists.
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "ERROR: Port $Port is already in use." -ForegroundColor Red
    Write-Host ""
    Write-Host "Current listener(s):"

    foreach ($conn in $existing) {
        # OwningProcess is the PID that owns the listening socket.
        # We use it to identify which application is occupying the port.
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue

        # Keep these values explicit for better Windows PowerShell compatibility
        # and easier debugging.
        $processName = if ($proc) { $proc.ProcessName } else { "<unknown>" }
        $processPath = if ($proc) { $proc.Path } else { "<unknown>" }

        # Print structured information about the listener.
        #
        # This is observation only:
        # the script reports the occupying process but does not stop it.
        [PSCustomObject]@{
            LocalAddress  = $conn.LocalAddress
            LocalPort     = $conn.LocalPort
            OwningProcess = $conn.OwningProcess
            ProcessName   = $processName
            Path          = $processPath
        }
    }

    Write-Host ""
    Write-Host "Use a different port, for example:" -ForegroundColor Yellow
    Write-Host "  .\start-api.ps1 -Port 8001"
    Write-Host ""
    Write-Host "Or manually stop the process that is occupying port $Port if you are sure it is safe."

    # Exit with non-zero code so CI, scripts, or reviewers can detect startup failure.
    exit 1
}

# Delegate the actual backend startup to scripts\run-backend.ps1.
#
# This keeps start-api.ps1 as a clean public entrypoint while the lower-level
# backend runtime details stay inside scripts\run-backend.ps1.
#
# $PSScriptRoot means the folder where this script lives.
# Join-Path makes the script path stable even if the current working directory changes.
#
# The call operator (&) executes the target script path.
& (Join-Path $PSScriptRoot "scripts\run-backend.ps1") `
    -ListenHost $ListenHost `
    -Port $Port `
    -Reload:$Reload
