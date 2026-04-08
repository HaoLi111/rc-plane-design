# RC Aircraft Design & Manufacturing Software — Project Plan

## Project: `rc-aircraft-design`
**Location**: `C:\Users\lhrcp\projects\rc-aircraft-design`
**Stack**: Python (main), Julia (compute-heavy), OpenGL (viz), DXF (CAD export)
**Focus**: Fixed-wing RC aerobatics, trapezoid wings default

## Source Repos (GitHub: HaoLi111)
| Repo | Language | Purpose |
|------|----------|---------|
| `rAviExp` | R | Core aviation exploratory design (alpha analysis, constraints, optimization) |
| `ModelPlanePower` | R | Power/propulsion: motor, prop, battery, rubber models |
| `ModelAircraftDesignTuningHandbook` | Julia | Lift-line theory, min lift speed, symbolic derivations |
| `WebrAviExpConvConcept` | R (Shiny) | Web UI for conventional RC fixed-wing parameter exploration |
| `eXpand` | Julia | 3D surface to 2D projection unfolding (foamboard/cardboard templates) |
| `MFVN` | R | Multivariable functions visual & numerical library (dependency of rAviExp) |
| `Open-Model-Airplane-Training` | HTML | Training materials |

## Python Package Modules
```
rc_aircraft_design/
├── aero/           # Angle of attack, lift/drag, airfoil polars
├── wing/           # Trapezoid wing geometry, planform, NACA 4/6 digit airfoils
├── stability/      # CG, stability analysis, simplified models
├── constraints/    # T/W vs W/S constraint analysis, feasibility regions
├── power/          # Motor, propeller, battery sizing, rubber power models
├── expand/         # 3D surface unfolding to 2D (foamboard cutting templates)
├── viz/            # OpenGL 3D visualization (fuselage sections, wing extrusion)
├── cad/            # DXF/DWG file writer (native grammar, no heavy deps)
└── utils/          # Shared math, interpolation, optimization helpers
```

## Key Enhancements (beyond R originals)
1. **NACA Airfoil Generation** — 4-digit and 6-series, with coordinate output
2. **OpenGL 3D Visualization** — Circle/square fuselage sections extruded from center; wing from NACA profile root-to-tip
3. **DXF/CAD Export** — Write DXF files using native DXF grammar (no AutoCAD needed)
4. **Julia acceleration** — Heavy numerical routines (lifting line, optimization) via `juliacall`

## Build Steps
1. Create project dir, git init, add repos as submodules under `legacy/`
2. Set up `uv` env with `pyproject.toml`
3. Read and understand all R/Julia source code
4. Implement core aero module (alpha analysis, Cl/Cd, polars)
5. Implement wing geometry (trapezoid planform, NACA profiles)
6. Implement stability and constraint modules
7. Implement power/propulsion module
8. Implement surface expansion (3D to 2D unfolding)
9. Implement NACA airfoil + OpenGL 3D viz
10. Implement DXF/CAD writer
11. Install and verify in uv env
