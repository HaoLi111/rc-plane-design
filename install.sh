#!/usr/bin/env bash
# install.sh — Install rc-aircraft-design on Linux / macOS
# Usage:
#   ./install.sh           # core only
#   ./install.sh all       # all optional deps (viz, cad, julia, aero, dev)
#   ./install.sh aero      # just the aero simulation extras
set -euo pipefail

EXTRAS="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Colours ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Check Python ─────────────────────────────────────────────────────────
info "Checking Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    error "Python 3.11+ is required but not found. Install it first."
fi

PY_VER=$($PY -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PY -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PY -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    error "Python >= 3.11 required (found $PY_VER)."
fi
info "Found Python $PY_VER"

# ── Check / install uv ──────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    info "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
info "uv $(uv --version)"

# ── System dependencies for xfoil (Fortran compiler) ────────────────────
install_fortran_linux() {
    if command -v gfortran &>/dev/null; then
        info "gfortran already installed."
        return
    fi
    warn "gfortran not found — needed to compile the xfoil package."
    if command -v apt-get &>/dev/null; then
        info "Installing gfortran via apt..."
        sudo apt-get update -qq && sudo apt-get install -y -qq gfortran gcc
    elif command -v dnf &>/dev/null; then
        info "Installing gfortran via dnf..."
        sudo dnf install -y gcc-gfortran gcc
    elif command -v pacman &>/dev/null; then
        info "Installing gfortran via pacman..."
        sudo pacman -Sy --noconfirm gcc-fortran
    else
        warn "Could not auto-install gfortran. Install it manually if you need the 'aero' extra."
    fi
}

install_fortran_mac() {
    if command -v gfortran &>/dev/null; then
        info "gfortran already installed."
        return
    fi
    warn "gfortran not found — needed to compile the xfoil package."
    if command -v brew &>/dev/null; then
        info "Installing gfortran via Homebrew..."
        brew install gcc
    else
        warn "Install Homebrew (https://brew.sh) then run:  brew install gcc"
    fi
}

if [[ "$EXTRAS" == *"aero"* ]] || [[ "$EXTRAS" == "all" ]]; then
    case "$(uname -s)" in
        Linux*)  install_fortran_linux ;;
        Darwin*) install_fortran_mac ;;
    esac
fi

# ── OpenVSP (optional, not pip-installable) ──────────────────────────────
check_openvsp() {
    if $PY -c "import openvsp" 2>/dev/null; then
        info "OpenVSP Python API detected."
    else
        warn "OpenVSP Python API not found."
        warn "  Download from: https://openvsp.org/download.php"
        warn "  After installing, add its Python directory to PYTHONPATH."
    fi
}

# ── Create venv & install ────────────────────────────────────────────────
cd "$SCRIPT_DIR"

if [ -n "$EXTRAS" ]; then
    info "Installing rc-aircraft-design with extras [$EXTRAS]..."
    uv sync --extra "$EXTRAS"
else
    info "Installing rc-aircraft-design (core only)..."
    uv sync
fi

# ── Post-install checks ─────────────────────────────────────────────────
info "Verifying installation..."
uv run python -c "import rc_aircraft_design; print(f'rc-aircraft-design {rc_aircraft_design.__version__} installed OK')"

if [[ "$EXTRAS" == *"aero"* ]] || [[ "$EXTRAS" == "all" ]]; then
    uv run python -c "
try:
    from xfoil import XFoil
    print('  ✓ xfoil')
except ImportError:
    print('  ✗ xfoil — install gfortran and retry')
try:
    import aerosandbox
    print('  ✓ aerosandbox')
except ImportError:
    print('  ✗ aerosandbox')
"
    check_openvsp
fi

if [[ "$EXTRAS" == *"dev"* ]] || [[ "$EXTRAS" == "all" ]]; then
    info "Running quick test suite..."
    uv run pytest --tb=short -q || warn "Some tests failed."
fi

info "Done."
