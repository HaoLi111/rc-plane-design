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

![NACA airfoil profiles](results/examples/naca_airfoils.png)

### Lift / Drag / L-D Polar Sweep

![Alpha sweep – Cl, Cd, L/D, drag polar](results/examples/alpha_sweep.png)

### Spanwise Structural Loads (Elliptic Lift)

![Span loads – lift distribution, shear, bending moment](results/examples/span_loads_simple.png)

### Taper Ratio Comparison

![Effect of taper ratio on structural loads](results/examples/taper_comparison.png)

### Load Factor Envelope

![Root shear and bending vs manoeuvre load factor](results/examples/load_factor_envelope.png)

## Legacy Source

Original R/Julia repos are under `legacy/` as git submodules.
