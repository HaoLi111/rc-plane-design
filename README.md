# RC Aircraft Design & Manufacturing Software

Python toolkit for fixed-wing RC aircraft design, analysis, and manufacturing template generation.

Ported from R/Julia originals by HaoLi111, with added NACA airfoil generation, OpenGL 3D visualization, and DXF/CAD export.

## Modules

| Module | Purpose |
|--------|---------|
| `aero` | Angle of attack, lift/drag polars, airfoil analysis |
| `wing` | Trapezoid wing geometry, planform, NACA 4/6 digit airfoils |
| `stability` | CG analysis, stability derivatives, simplified models |
| `constraints` | T/W vs W/S constraint diagrams, feasibility regions |
| `power` | Motor, propeller, battery sizing, rubber power models |
| `expand` | 3D surface unfolding to 2D cutting templates |
| `viz` | OpenGL 3D visualization |
| `cad` | DXF file export |
| `utils` | Shared math, interpolation, optimization helpers |

## Setup

```bash
uv sync                    # install core deps
uv sync --extra all        # install everything
```

## Examples

Run the smoke-test script to regenerate all plots (each run creates a timestamped subfolder):

```bash
python examples/smoke_test_loads.py
# outputs to results/examples/<YYYYMMDD_HHMMSS>/
```

### NACA 4-Digit Airfoil Profiles
> Module: [`aero.airfoil`](rc_aircraft_design/aero/airfoil.py)

![NACA airfoil profiles](results/examples/naca_airfoils.png)

### Lift / Drag / L-D Polar Sweep
> Module: [`aero.analysis`](rc_aircraft_design/aero/analysis.py)

![Alpha sweep – Cl, Cd, L/D, drag polar](results/examples/alpha_sweep.png)

### Spanwise Structural Loads (Elliptic Lift)
> Module: [`wing.loads`](rc_aircraft_design/wing/loads.py)

![Span loads – lift distribution, shear, bending moment](results/examples/span_loads_simple.png)

### Taper Ratio Comparison
> Module: [`wing.loads`](rc_aircraft_design/wing/loads.py)

![Effect of taper ratio on structural loads](results/examples/taper_comparison.png)

### V-n Manoeuvre Envelope
> Module: [`wing.loads`](rc_aircraft_design/wing/loads.py) · [`aero.analysis`](rc_aircraft_design/aero/analysis.py)

Positive and negative aerodynamic envelopes clamped to structural limit load factors, with $V_{ne}$ (max dynamic pressure) and $V_{s1}$ (1g stall) annotated.

![V-n manoeuvre envelope – positive/negative load factor vs airspeed](results/examples/load_factor_envelope.png)

## Integrations & External Tools

This project integrates several open-source aerodynamics packages as pip dependencies
or git submodules to give a richer analysis toolkit:

### Python Dependencies (pip / `uv sync --extra aero`)

| Package | Purpose | Link |
|---------|---------|------|
| **AeroSandbox** | VLM aerodynamics, optimization, propulsion models | [peterdsharpe/AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) |
| **NeuralFoil** | ML-based XFoil replacement (~1000× faster, no Fortran binary) | [peterdsharpe/NeuralFoil](https://github.com/peterdsharpe/NeuralFoil) |
| **XFoil** (Python wrapper) | Classical 2-D viscous airfoil analysis | [xfoil](https://pypi.org/project/xfoil/) |

### Git Submodules (`legacy/`)

Community and reference repos brought in for study, porting, and cross-validation:

| Submodule | Author | Description |
|-----------|--------|-------------|
| `ThomasDavid0-AircraftDesign` | Thomas David | Aircraft definition, AVL interface, XFLR5 data import, atmosphere model, airfoil database, performance & solar-wing tools ([repo](https://github.com/ThomasDavid0/AircraftDesign)) |
| `MachUpX` | USU Aero Lab | Numerical lifting-line theory, stability derivatives, JSON aircraft definitions ([repo](https://github.com/usuaero/MachUpX)) |
| `AirfoilDatabase` | USU Aero Lab | Airfoil database management, XFoil integration, polar curve fitting ([repo](https://github.com/usuaero/AirfoilDatabase)) |
| `rAviExp` | HaoLi111 | R library for model-aviation exploratory design (original source for constraint & geometry modules) |
| `ModelPlanePower` | HaoLi111 | Propeller design (Russell method), rubber motor & electric power models |
| `ModelAircraftDesignTuningHandbook` | HaoLi111 | Lift-line theory & minimum-lift-speed calculations (Julia) |
| `eXpand` | HaoLi111 | 3-D surface → 2-D cutting-template unfolding (Julia) |
| `MFVN` | HaoLi111 | Multivariable function visualisation & numerical tools (R) |
| `WebrAviExpConvConcept` | HaoLi111 | Shiny web UI for conventional-concept sizing |
| `Open-Model-Airplane-Training` | HaoLi111 | Open-source RC aircraft training curriculum |

Clone with all submodules:

```bash
git clone --recurse-submodules https://github.com/<you>/rc-aircraft-design.git
# or, after a shallow clone:
git submodule update --init --recursive
```
