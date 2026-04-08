# Installation Guide

## Requirements

| Requirement     | Version  | Notes                            |
|-----------------|----------|----------------------------------|
| Python          | >= 3.11  | 3.12 recommended                 |
| uv              | latest   | Package manager (auto-installed) |
| gfortran / gcc  | any      | Only for `aero` extra (xfoil)    |

## Quick Install

### Windows (PowerShell)

```powershell
# Core only
.\install.ps1

# All extras (aero simulation, 3D viz, CAD, web UI, dev tools)
.\install.ps1 -Extras all

# Just aero extras (xfoil + aerosandbox)
.\install.ps1 -Extras aero

# Web UI only
.\install.ps1 -Extras webui
```

### Linux / macOS (Bash)

```bash
chmod +x install.sh

# Core only
./install.sh

# All extras
./install.sh all

# Just aero extras
./install.sh aero

# Web UI only
./install.sh webui
```

### Manual Install (uv)

```bash
# Core dependencies only
uv sync

# With specific extras
uv sync --extra aero       # xfoil + aerosandbox + neuralfoil
uv sync --extra webui      # Dash web UI (plotly, dash, pandas)
uv sync --extra viz        # OpenGL visualization
uv sync --extra cad        # DXF/CAD export
uv sync --extra dev        # pytest + ruff
uv sync --extra all        # everything
```

### Manual Install (pip)

```bash
pip install -e .             # core
pip install -e ".[aero]"     # + xfoil, aerosandbox, neuralfoil
pip install -e ".[webui]"    # + Dash web UI
pip install -e ".[all]"      # everything
```

---

## Dependency Groups

Defined in `pyproject.toml` under `[project.optional-dependencies]`:

| Extra   | Packages                                     | Purpose                          |
|---------|----------------------------------------------|----------------------------------|
| (core)  | numpy, scipy, matplotlib                     | Base numerics and plotting       |
| `aero`  | xfoil, aerosandbox, neuralfoil               | XFoil 2D polars, VLM 3D aero, PINN airfoil |
| `webui` | dash, dash-bootstrap-components, dash-iconify, plotly, pandas | Interactive web dashboard |
| `viz`   | PyOpenGL, PyOpenGL-accelerate, glfw           | 3D OpenGL visualization          |
| `cad`   | ezdxf                                        | DXF file export                  |
| `julia` | juliacall                                    | Julia interop for heavy numerics |
| `dev`   | pytest, ruff                                 | Testing and linting              |
| `all`   | all of the above                             |                                  |

---

## Web UI (Dash)

The web UI has its own project in `webui/` with a separate `pyproject.toml`.
It installs the core `rc-aircraft-design` package automatically.

### Quick start

```bash
cd webui
uv sync                # creates .venv, installs dash + core package
uv run python app.py   # http://127.0.0.1:8050
```

### Manual setup

```bash
cd webui
uv venv --python 3.11
uv pip install -e ".."                     # core package (editable)
uv pip install dash dash-bootstrap-components dash-iconify plotly pandas
python app.py
```

### What the UI provides

| Page | Description |
|------|-------------|
| **Dashboard** | Preset aircraft cards, one-click design |
| **Configuration** | Mission & airfoil parameter editor, triggers design pipeline |
| **Aerodynamics** | Standalone: Cl/Cd polars, speed–lift contour, V-n diagram, climb analysis |
| **Constraints** | Interactive T/W vs W/S diagram |
| **Geometry** | Top + side planform views, MAC tables |
| **Stability** | Gauge charts for Vh, Vv, static margin, spiral stability |
| **Power** | Sankey power-flow diagram, battery/motor sizing |
| **Loads** | Spanwise lift, shear, bending distributions |
| **Workbench** | Run any stage standalone — pick a stage, edit JSON, execute, export |
| **Manufacturing** | Rib schedule, airfoil preview |
| **Export** | Download JSON / DXF / text report |

Every analysis stage is also a standalone JSON→JSON function — import/export
at any boundary (replaces the `.RData` workflow from the R legacy tools).

---

## Platform-Specific Notes

### XFoil (Fortran Compiler)

The `xfoil` Python package compiles Fortran source on install. Pre-built wheels
may exist for some Python versions; if not, you need a Fortran compiler:

**Windows:**
- Install [MSYS2](https://www.msys2.org/), then:
  ```
  pacman -S mingw-w64-x86_64-gcc-fortran
  ```
- Or install [MinGW-w64](https://www.mingw-w64.org/) and add its `bin/` to PATH.
- If using distutils, create `PYTHONPATH\Lib\distutils\distutils.cfg`:
  ```ini
  [build]
  compiler=mingw32
  ```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install gfortran gcc
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install gcc-gfortran gcc
```

**macOS:**
```bash
brew install gcc
```

### AeroSandbox

AeroSandbox is pure Python and installs cleanly via pip/uv with no system
dependencies. It provides:
- Vortex Lattice Method (VLM) — 3D aerodynamics
- Built-in XFoil interface (alternative to the `xfoil` package)
- Euler-Bernoulli beam solver for structural loads
- Airfoil shape optimization

```python
import aerosandbox as asb
# Quick VLM example
airplane = asb.Airplane(name="my_rc", ...)
aero = asb.VortexLatticeMethod(airplane, op_point=asb.OperatingPoint(...))
aero_result = aero.run()
```

---

## Verification

After installation, run the test suite:

```bash
uv run pytest --tb=short -q
```

Or check individual modules:

```python
from rc_aircraft_design.aero.analysis import LinearAirfoil
from rc_aircraft_design.aero.airfoil import naca4

# Generate a NACA 2412 airfoil
x, yu, yl = naca4("2412")

# Quick aero analysis
af = LinearAirfoil(Cla=0.11, alpha0_deg=-2.0, Cd0=0.008)
result = af.analyze()
print(f"L/D max = {result.LDmax:.1f} at α = {result.alpha_LDmax:.1f}°")
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pip install xfoil` fails with Fortran error | Install gfortran (see above) |
| `import openvsp` fails | Set PYTHONPATH to OpenVSP's `python/` directory |
| `uv` not found after installer | Restart your terminal or add `~/.local/bin` (Linux) / `%USERPROFILE%\.local\bin` (Windows) to PATH |
| PyOpenGL errors on headless server | Install `viz` extra only on machines with a display; use `--extra aero` for headless |
| AeroSandbox import slow on first run | Normal — it JIT-compiles some internals on first use |
