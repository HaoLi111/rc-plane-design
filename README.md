# RC Aircraft Design & Manufacturing Software

Python toolkit for fixed-wing RC aircraft design, analysis, and manufacturing template generation.

Every module works standalone — use them as a library to analyze an existing aircraft, or wire them together through the passive pipeline to generate a complete design from mission assumptions. Either way, you get the same aero, structures, stability, and CAD tools.

Ported from R/Julia originals by HaoLi111, with added NACA airfoil generation, OpenGL 3D visualization, and DXF/CAD export.

## Modules

| Module | Purpose |
|--------|---------|
| `aero` | Angle of attack, lift/drag polars, airfoil analysis |
| `wing` | Trapezoid wing geometry, planform, NACA 4/6 digit airfoils |
| `stability` | CG analysis, stability derivatives, simplified models |
| `constraints` | T/W vs W/S constraint diagrams, feasibility regions |
| `power` | Motor, propeller, battery sizing, rubber power models |
| `passive` | **Passive design pipeline** — full aircraft from ~10 assumptions |
| `expand` | 3D surface unfolding to 2D cutting templates |
| `viz` | OpenGL 3D visualization |
| `cad` | DXF file export |
| `utils` | Shared math, interpolation, optimization helpers |

## Setup

```bash
uv sync                    # install core deps
uv sync --extra dev        # install dev deps (pytest, ruff)
uv sync --extra all        # install everything
```

## Two Workflows

The package supports two complementary workflows:

| Workflow | Start with | End with |
|----------|-----------|----------|
| **Analysis** | An existing aircraft (JSON or code) | Aero polars, stability margins, structural loads, DXF templates |
| **Design** | ~10 mission assumptions | A complete sized aircraft + all of the above |

You can mix and match freely — design a plane with the passive pipeline, then run extra analysis passes on it; or define your own geometry by hand and skip the pipeline entirely.

## Quickstart — Analyze an Existing Aircraft

Load one of the included aircraft definitions (or create your own) and use individual modules:

```python
import json
from rc_aircraft_design.aero import LinearAirfoil, naca4
from rc_aircraft_design.wing import Wing, ConventionalConcept, compute_mac, planform_coords
from rc_aircraft_design.stability import analyze_stability
from rc_aircraft_design.constraints import ConstraintParams, analyze_constraints
from rc_aircraft_design.wing.loads import compute_span_loads_simple
from rc_aircraft_design.cad import DxfWriter

# Load an aircraft JSON  (or build Wing objects directly — it's the same API)
data = json.load(open("data/examples/sport_trainer_40.json"))

# Aero analysis
af_d = data["airfoil"]
af = LinearAirfoil(Cla=af_d["Cla"], alpha0_deg=af_d["alpha0_deg"],
                   Cd0=af_d["Cd0"], Cdi_factor=af_d["Cdi_factor"])
result = af.analyze()
print(f"L/D max = {result.LDmax:.1f} at α = {result.alpha_LDmax:.1f}°")

# Build geometry and compute MAC
wm = Wing(**data["wing_main"])
mac = compute_mac(wm)
print(f"MAC = {mac.mac_length:.3f} m, AR = {wm.aspect_ratio:.1f}")

# Stability
wh = Wing(**data["wing_horiz"])
wv = Wing(**data["wing_vert"])
fus = data["fuselage"]
concept = ConventionalConcept(
    wing_main=wm, wing_horiz=wh, wing_vert=wv,
    fuselage_length=fus["length"],
    fuselage_stations=fus["stations"], fuselage_radii=fus["radii"],
)
stab = analyze_stability(concept, X_cg=data["cg_x"])
print(f"Static margin = {stab.static_margin:.3f}")

# Span loads
loads = compute_span_loads_simple(wm, lift_N=wm.area * 50)  # 50 Pa example

# Export planform to DXF
dxf = DxfWriter()
for wing, layer in [(wm, "WING"), (wh, "HTAIL"), (wv, "VTAIL")]:
    px, py = planform_coords(wing)
    dxf.add_planform(px, py, layer=layer)
dxf.save("sport_trainer.dxf")
```

No pipeline needed — pick the modules you want and call them directly.

### Quickstart — Use Modules Standalone

You don't need a JSON file at all. Every module accepts plain Python objects:

```python
from rc_aircraft_design.aero import naca4
from rc_aircraft_design.wing import Wing, compute_mac

# Generate a NACA 2412 airfoil
x, yu, yl = naca4("2412")

# Define a wing and compute MAC
w = Wing(chord_root=0.3, chord_tip=0.2, span=1.5, sweep_deg=5, dihedral_deg=3)
mac = compute_mac(w)
print(f"MAC = {mac.mac_length:.3f} m, AR = {w.aspect_ratio:.1f}")
```

### Aircraft JSON Format

Full aircraft definitions live in [`data/examples/`](data/examples/). Each JSON contains geometry, airfoil params, weight, power, and constraint targets — everything needed to run any analysis module:

| File | Description |
|------|-------------|
| [`classic_2m_glider.json`](data/examples/classic_2m_glider.json) | 2 m sailplane, no motor |
| [`sport_trainer_40.json`](data/examples/sport_trainer_40.json) | Classic .40-size sport trainer |
| [`extra_330sc_3d.json`](data/examples/extra_330sc_3d.json) | 3D aerobatic pattern plane |

See [`tests/test_example_planes.py`](tests/test_example_planes.py) for the full analysis workflow exercised on every plane.

## Design — Full Aircraft from Assumptions

If you don't already have an aircraft, the **passive design pipeline** ([`passive.py`](rc_aircraft_design/passive.py)) derives a complete conventional-layout RC aircraft from a handful of mission assumptions — no manual geometry required. The output is the same `ConventionalConcept` you'd build by hand, so every analysis module works on it identically.

Ported from the rAviExp R package (`legacy/rAviExp/`), each stage feeds forward analytically with no iteration loops:

```
Airfoil assumptions → Constraint analysis (T/W vs W/S)
     → Weight & power sizing → Wing geometry → Stability check
```

### Usage

Define a mission as a JSON file with ~10 parameters (see [`data/examples/missions/`](data/examples/missions/)):

```json
{
    "assumptions": {
        "mission": "weekend sport flying, gentle aerobatics, grass field",
        "payload_kg": 0.25,
        "payload_fraction": 0.25,
        "cruise_speed_ms": 18.0,
        "endurance_s": 600,
        "altitude_m": 200,
        "climb_rate_ms": 5.0,
        "turn_bank_deg": 45,
        "takeoff_ground_roll_m": 20.0
    },
    "airfoil": {
        "code": "2412",
        "Cla": 0.1, "alpha0_deg": -5.0,
        "Cd0": 0.02, "Cdi_factor": 0.0398
    }
}
```

Then run the pipeline in Python:

```python
import json
from rc_aircraft_design.passive import run_passive_design

data = json.load(open("data/examples/missions/aerial_survey.json"))
result = run_passive_design(data["assumptions"], data["airfoil"])

# Result is a ConventionalConcept with sized wing, tail, fuselage
concept = result.concept
print(f"Wing span:  {concept.wing_main.span*100:.0f} cm")
print(f"Wing area:  {result.S_wing*1e4:.0f} cm²")
print(f"Gross mass: {result.m_gross_kg:.2f} kg")
print(f"T/W:        {result.TW_opt:.3f}")
print(f"SM:         {result.stability.static_margin:.3f}")

# Export to DXF for CAD/laser-cutting
from rc_aircraft_design.cad import DxfWriter
from rc_aircraft_design.wing.geometry import planform_coords

dxf = DxfWriter()
for wing, layer in [
    (concept.wing_main, "WING"), (concept.wing_horiz, "HTAIL"), (concept.wing_vert, "VTAIL"),
]:
    px, py = planform_coords(wing)
    dxf.add_planform(px, py, layer=layer)
dxf.save("my_aircraft.dxf")
```

### Mission Profiles

Six mission profiles are included in [`data/examples/missions/`](data/examples/missions/):

| Mission | File | Payload | Speed | Key trait |
|---------|------|---------|-------|-----------|
| Sport Flyer | [`passive_sport_flyer.json`](data/examples/passive_sport_flyer.json) | 0.25 kg | 18 m/s | Balanced weekend flyer |
| Aerial Survey | [`aerial_survey.json`](data/examples/missions/aerial_survey.json) | 0.50 kg | 14 m/s | Heavy camera, long loiter |
| 3D Aerobat | [`aerobat_3d.json`](data/examples/missions/aerobat_3d.json) | 0.15 kg | 22 m/s | 15 m/s climb, 70° bank |
| FPV Racer | [`fpv_racer.json`](data/examples/missions/fpv_racer.json) | 0.35 kg | 30 m/s | High speed, 60° bank |
| Park Flyer | [`park_flyer.json`](data/examples/missions/park_flyer.json) | 0.05 kg | 8 m/s | Micro, beginner-friendly |
| Thermal Soarer | [`thermal_soarer.json`](data/examples/missions/thermal_soarer.json) | 0.02 kg | 8 m/s | No motor, high L/D |

Generate all result images and DXF files:

```bash
python examples/passive_design_gallery.py
# outputs to results/examples/passive_*.png and *.dxf
```

### Example Results

#### Sport Flyer — Three-View with Design Parameters
> Modules: [`passive`](rc_aircraft_design/passive.py) · [`wing.geometry`](rc_aircraft_design/wing/geometry.py) · [`stability`](rc_aircraft_design/stability/analysis.py)

The pipeline produces a `ConventionalConcept` with main wing, H-tail, V-tail, and fuselage — plus CG/NP positions and stability checks.

![Sport Flyer three-view planform with parameters](results/examples/passive_sport_flyer_threeview.png)

#### Sport Flyer — Constraint Diagram (T/W vs W/S)
> Module: [`constraints`](rc_aircraft_design/constraints/analysis.py)

Five constraint curves (turn, climb, cruise, ceiling, takeoff) define the feasible envelope. The red star marks the optimal design point with minimum required T/W.

![Sport Flyer constraint diagram](results/examples/passive_sport_flyer_constraints.png)

#### 3D Aerobat — Three-View
> High T/W = 1.035 for vertical performance, compact 76 cm span, NACA 0015 symmetrical airfoil.

![3D Aerobat three-view planform](results/examples/passive_aerobat_3d_threeview.png)

#### Mission Comparison
> All six missions side-by-side. Note how different requirements (speed, payload, climb rate) produce dramatically different aircraft sizes and proportions.

![Passive design mission comparison — 6 aircraft silhouettes](results/examples/passive_comparison.png)

#### DXF / CAD Export
> Module: [`cad`](rc_aircraft_design/cad/dxf_writer.py)

Each design is also exported to DXF R12 format (e.g. `passive_sport_flyer_planform.dxf`) with layered planforms (WING_MAIN, H_TAIL, V_TAIL) and airfoil profiles — ready for any CAD program or laser cutter.

## Testing

The test suite covers all 9 modules plus integration tests that exercise each example
aircraft JSON through a full design workflow (aero → geometry → stability → constraints → loads → CAD).

```bash
# Run the full test suite
uv run pytest tests/ -v

# Run tests for a single module
uv run pytest tests/test_aero.py -v
uv run pytest tests/test_wing.py -v

# Quick summary
uv run pytest tests/ -q
```

| Test file | What it covers |
|-----------|---------------|
| `test_utils.py` | Trig helpers, ISA atmosphere, Reynolds, interpolation, geometry |
| `test_aero.py` | Thin-airfoil coefficients, compressibility, form factors, `LinearAirfoil`, NACA generation, climb & V-n analysis |
| `test_wing.py` | `Wing` dataclass, MAC computation, sizing, planform coords, span loads (shear, bending, torsion) |
| `test_stability.py` | Volume coefficients, neutral point, spiral stability, full stability analysis |
| `test_constraints.py` | All 6 constraint types, envelope, full T/W vs W/S analysis |
| `test_power.py` | Russell propeller, rubber motors, electric power system, weight estimation |
| `test_expand.py` | Quad/triangle/strip unfolding, full wing surface unfold |
| `test_viz.py` | Mesh normals, `from_vertices_and_indices`, fuselage & wing mesh generation |
| `test_cad.py` | DXF R12 entities (line, polyline, circle, arc, text), planform/airfoil/template helpers, file I/O |
| `test_example_planes.py` | End-to-end workflow for each JSON in `data/examples/` (3 aircraft) |
| `test_passive_design.py` | Passive pipeline across 6 missions — aero, constraints, weight, geometry, stability checks |

## Examples

All runnable example scripts live in [`examples/`](examples/):

| Script | Description | Key modules |
|--------|-------------|-------------|
| [`smoke_test_loads.py`](examples/smoke_test_loads.py) | NACA airfoils, alpha sweeps, span loads, taper comparison, V-n envelope | `aero.airfoil`, `aero.analysis`, `wing.loads` |
| [`test_neuralfoil.py`](examples/test_neuralfoil.py) | NeuralFoil (PINN) CL/CD/CM polars for 4 NACA foils at Re=200k | `aero.airfoil`, NeuralFoil |
| [`passive_design_from_assumptions.py`](examples/passive_design_from_assumptions.py) | Full aircraft from ~10 mission assumptions (single mission) | `passive`, `wing.geometry`, `stability`, `constraints` |
| [`passive_design_gallery.py`](examples/passive_design_gallery.py) | Three-views, constraint diagrams, and comparison for all 6 missions | `passive`, `constraints`, `cad` |

Each run creates a timestamped subfolder under `results/examples/<YYYYMMDD_HHMMSS>/`.

```bash
python examples/smoke_test_loads.py
python examples/test_neuralfoil.py
python examples/passive_design_gallery.py
python examples/passive_design_from_assumptions.py
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
