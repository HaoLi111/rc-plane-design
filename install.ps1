<# install.ps1 — Install rc-aircraft-design on Windows (PowerShell 5.1+)
.SYNOPSIS
    Sets up the rc-aircraft-design Python environment on Windows.
.PARAMETER Extras
    Optional dependency group(s): core (default), aero, viz, cad, julia, webui, dev, all.
.EXAMPLE
    .\install.ps1              # core only
    .\install.ps1 -Extras all  # everything
    .\install.ps1 -Extras aero # aero simulation extras
    .\install.ps1 -Extras webui # web UI (Dash) only
#>
[CmdletBinding()]
param(
    [string]$Extras = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Write-Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ── Check Python ─────────────────────────────────────────────────────────
Write-Info "Checking Python..."
$py = $null
foreach ($candidate in @("python", "python3", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $py = $candidate; break
    }
}
if (-not $py) { Write-Err "Python 3.11+ is required but not found. Install from https://www.python.org/downloads/" }

$pyVer = & $py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
$parts = $pyVer -split '\.'
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    Write-Err "Python >= 3.11 required (found $pyVer)."
}
Write-Info "Found Python $pyVer"

# ── Check / install uv ──────────────────────────────────────────────────
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Info "Installing uv package manager..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path
}
$uvVer = uv --version
Write-Info "uv $uvVer"

# ── Fortran compiler check (needed for xfoil) ───────────────────────────
function Test-Fortran {
    if ($Extras -match "aero|all") {
        if (Get-Command "gfortran" -ErrorAction SilentlyContinue) {
            Write-Info "gfortran found."
        } else {
            Write-Warn "gfortran not found — needed to compile the xfoil package from source."
            Write-Warn "Options to install a Fortran compiler on Windows:"
            Write-Warn "  1. Install MSYS2 (https://www.msys2.org/) then run:"
            Write-Warn "       pacman -S mingw-w64-x86_64-gcc-fortran"
            Write-Warn "  2. Install MinGW-w64 from https://www.mingw-w64.org/"
            Write-Warn "  3. Use conda:  conda install -c conda-forge gfortran"
            Write-Warn ""
            Write-Warn "If pre-built xfoil wheels are available for your Python version, gfortran is not needed."
        }
    }
}

# ── Install ──────────────────────────────────────────────────────────────
Set-Location $ScriptDir
Test-Fortran

if ($Extras -and $Extras -ne "") {
    Write-Info "Installing rc-aircraft-design with extras [$Extras]..."
    uv sync --extra $Extras
} else {
    Write-Info "Installing rc-aircraft-design (core only)..."
    uv sync
}

# ── Verify ───────────────────────────────────────────────────────────────
Write-Info "Verifying installation..."
uv run python -c "import rc_aircraft_design; print(f'rc-aircraft-design {rc_aircraft_design.__version__} installed OK')"

if ($Extras -match "aero|all") {
    uv run python -c @"
try:
    from xfoil import XFoil
    print('  OK xfoil')
except ImportError:
    print('  MISSING xfoil - install gfortran and retry')
try:
    import aerosandbox
    print('  OK aerosandbox')
except ImportError:
    print('  MISSING aerosandbox')
"@
}

if ($Extras -match "dev|all") {
    Write-Info "Running quick test suite..."
    uv run pytest --tb=short -q
}

# ── Web UI environment (separate venv in webui/) ────────────────────────
if ($Extras -match "webui|all") {
    Write-Info "Setting up Web UI environment (webui/)..."
    Push-Location (Join-Path $ScriptDir "webui")
    uv sync
    Write-Info "Web UI installed. Start with:  cd webui; uv run python app.py"
    Pop-Location
}

Write-Info "Done."
