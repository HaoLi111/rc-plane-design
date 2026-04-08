# RC Aircraft Design & Manufacturing Software

HERE for a lite demo without installation: https://rc-plane-design.onrender.com/geometry 

**One pipeline: mission requirements in → laser-cut parts out.**

This is not just an aero textbook translated to Python. It is a full **design → simulate → manufacture** workflow that takes a handful of mission assumptions (payload, speed, endurance…) and produces a complete, physically buildable RC aircraft — 3D visualization, structural analysis, and every laser-cutter-ready rib, former, fuselage side, and spar template — with no manual CAD in between.

```
Mission assumptions ─→ Aerodynamics ─→ Constraint sizing ─→ 3D aircraft model
    ─→ Stability & loads ─→ Manufacturing parts (ribs, formers, skins)
        ─→ DXF export ─→ DeepNest sheet nesting ─→ Laser cut ─→ Build
```

Available as a **Python library** (use any module standalone) and as a **web GUI** (interactive dashboard for the full workflow). Integrates PINN-based airfoil analysis (NeuralFoil), vortex-lattice methods (AeroSandbox), and classical panel codes (XFoil).

## Web UI — no code required

> **Live demo:** [rc-aircraft-design-studio.onrender.com](https://rc-aircraft-design-studio.onrender.com) *(free tier — first load may take ~30 s to wake)*

The fastest way to use this project: a full interactive dashboard that runs in your browser. No Python knowledge needed — load a preset, tweak parameters, click **Run**, explore interactive charts, and export results as JSON, DXF, or HTML.

**Quick launch (copy-paste):**

```powershell
# Windows (PowerShell)
cd webui; uv sync; uv run python app.py        # → http://127.0.0.1:8050
```

```bash
# macOS / Linux
cd webui && uv sync && uv run python app.py    # → http://127.0.0.1:8050
```

```bash
# Without uv (pip)
cd webui
python -m venv .venv && .venv/bin/pip install -e .. && .venv/bin/pip install dash dash-bootstrap-components dash-iconify plotly pandas
.venv/bin/python app.py                        # → http://127.0.0.1:8050
```

**Deploy your own** (free): click the button below to deploy to Render, or use the included `render.yaml` blueprint.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

<!-- Screenshots: replace these comments with actual screenshots once available -->
<!-- ![Dashboard](docs/screenshots/webui_dashboard.png) -->
<!-- ![Aerodynamics — speed–lift contour](docs/screenshots/webui_aero_speed_lift.png) -->

| Page | What you get |
|------|-------------|
| **Dashboard** | Pick a preset aircraft, one-click design pipeline |
| **Configuration** | Edit mission & airfoil params, run full pipeline |
| **Aerodynamics** | Cl/Cd polars, speed–lift contour, V-n diagram, climb curves — all standalone |
| **Constraints** | Interactive T/W vs W/S envelope with optimum point |
| **Geometry** | 3D Plotly aircraft view + 2D planforms, CG/NP markers, MAC tables — export to HTML |
| **Stability** | Gauge charts for Vh, Vv, static margin, spiral stability |
| **Power** | Sankey power-flow diagram, battery/motor/propeller sizing |
| **Loads** | Spanwise lift, shear, bending distributions |
| **Workbench** | Run any stage standalone — paste JSON in, get JSON + chart out (replaces `.RData`) |
| **Manufacturing** | Rib schedule, airfoil profiles |
| **Export** | Download JSON config, DXF planforms, text report, or interactive 3D HTML |

> Every analysis stage is a pure **JSON → JSON function**. Import and export at any boundary — no proprietary formats, no lock-in.

## Python library — for developers

Use any module standalone in your own scripts or Jupyter notebooks:

```python
from rc_aircraft_design.passive import run_passive_design
from rc_aircraft_design.aero import LinearAirfoil, naca4
from rc_aircraft_design.wing import Wing, compute_mac
from rc_aircraft_design.stability import analyze_stability
```

```bash
pip install -e .     # or: uv sync
```

See the [Quickstart](#quickstart) section below for full examples.

## Gallery

#### 3D aircraft visualization
| Perspective | Top | Side | Front |
|:-----------:|:---:|:----:|:-----:|
| ![3D perspective](results/examples/sport_flyer_3d_perspective.png) | ![Top view](results/examples/sport_flyer_3d_top.png) | ![Side view](results/examples/sport_flyer_3d_side.png) | ![Front view](results/examples/sport_flyer_3d_front.png) |

#### Manufacturing parts — wing ribs with spar slots, longerons, and aileron hinge cuts
![Wing rib gallery](results/examples/sport_flyer_rib_gallery.png)

#### Manufacturing parts — fuselage formers at each station
![Fuselage formers](results/examples/sport_flyer_formers.png)

#### What we're building toward — complete laser-cut part sheets from a single design
> Real RC aircraft plans contain dozens of interlocking ribs, formers, fuselage sides, doublers, and spar webs — all generated from the same geometry and exported to DXF for nesting and cutting. This is the end goal of the manufacturing pipeline.

<!-- Add a reference plan image here: ![Reference laser-cut plan](docs/reference_laser_cut_plan.png) -->

#### Six missions → six different aircraft, sized automatically
![Passive design mission comparison](results/examples/passive_comparison.png)

#### Three-view planforms with design parameters
| Sport Flyer | 3D Aerobat | Aerial Survey |
|:-----------:|:----------:|:-------------:|
| ![Sport Flyer](results/examples/passive_sport_flyer_threeview.png) | ![3D Aerobat](results/examples/passive_aerobat_3d_threeview.png) | ![Aerial Survey](results/examples/passive_aerial_survey_threeview.png) |

| FPV Racer | Park Flyer | Thermal Soarer |
|:---------:|:----------:|:--------------:|
| ![FPV Racer](results/examples/passive_fpv_racer_threeview.png) | ![Park Flyer](results/examples/passive_park_flyer_threeview.png) | ![Thermal Soarer](results/examples/passive_thermal_soarer_threeview.png) |

#### Constraint diagrams (T/W vs W/S)
| Sport Flyer | 3D Aerobat | Aerial Survey |
|:-----------:|:----------:|:-------------:|
| ![Sport Flyer constraints](results/examples/passive_sport_flyer_constraints.png) | ![Aerobat constraints](results/examples/passive_aerobat_3d_constraints.png) | ![Survey constraints](results/examples/passive_aerial_survey_constraints.png) |

| FPV Racer | Park Flyer | Thermal Soarer |
|:---------:|:----------:|:--------------:|
| ![FPV constraints](results/examples/passive_fpv_racer_constraints.png) | ![Park constraints](results/examples/passive_park_flyer_constraints.png) | ![Soarer constraints](results/examples/passive_thermal_soarer_constraints.png) |

#### Aero & structural analysis
| NACA Airfoil Profiles | Lift / Drag / L-D Polars | V-n Manoeuvre Envelope |
|:---------------------:|:------------------------:|:---------------------:|
| ![NACA airfoils](results/examples/naca_airfoils.png) | ![Alpha sweep](results/examples/alpha_sweep.png) | ![V-n envelope](results/examples/load_factor_envelope.png) |

| Spanwise Loads (Elliptic Lift) | Taper Ratio Comparison |
|:------------------------------:|:----------------------:|
| ![Span loads](results/examples/span_loads_simple.png) | ![Taper comparison](results/examples/taper_comparison.png) |

---

## Quickstart

```bash
pip install -e .           # or: uv sync
```

### Design an aircraft from mission assumptions

```python
import json
from rc_aircraft_design.passive import run_passive_design

data = json.load(open("data/examples/missions/aerial_survey.json"))
result = run_passive_design(data["assumptions"], data["airfoil"])

print(f"Wing span:  {result.concept.wing_main.span*100:.0f} cm")
print(f"Gross mass: {result.m_gross_kg:.2f} kg")
print(f"T/W:        {result.TW_opt:.3f}")
```

### Analyze an existing aircraft

```python
import json
from rc_aircraft_design.aero import LinearAirfoil
from rc_aircraft_design.wing import Wing, ConventionalConcept, compute_mac
from rc_aircraft_design.stability import analyze_stability

data = json.load(open("data/examples/sport_trainer_40.json"))

af = data["airfoil"]
result = LinearAirfoil(Cla=af["Cla"], alpha0_deg=af["alpha0_deg"],
                       Cd0=af["Cd0"], Cdi_factor=af["Cdi_factor"]).analyze()
print(f"L/D max = {result.LDmax:.1f}")

wm = Wing(**data["wing_main"])
concept = ConventionalConcept(
    wing_main=wm,
    wing_horiz=Wing(**data["wing_horiz"]),
    wing_vert=Wing(**data["wing_vert"]),
    fuselage_length=data["fuselage"]["length"],
    fuselage_stations=data["fuselage"]["stations"],
    fuselage_radii=data["fuselage"]["radii"],
)
stab = analyze_stability(concept, X_cg=data["cg_x"])
print(f"Static margin = {stab.static_margin:.3f}")
```

### Use individual modules directly

```python
from rc_aircraft_design.aero import naca4
from rc_aircraft_design.wing import Wing, compute_mac

x, yu, yl = naca4("2412")
w = Wing(chord_root=0.3, chord_tip=0.2, span=1.5, sweep_deg=5, dihedral_deg=3)
print(f"MAC = {compute_mac(w).mac_length:.3f} m, AR = {w.aspect_ratio:.1f}")
```

---

## Modules

| Module | Purpose |
|--------|---------|
| `aero` | Airfoil geometry (NACA 4/6), lift/drag polars, compressibility corrections |
| `wing` | Trapezoid wing geometry, MAC, planform coords, span loads (shear/bending/torsion) |
| `stability` | CG analysis, neutral point, stability derivatives, static margin |
| `constraints` | T/W vs W/S constraint diagrams, feasibility envelope |
| `power` | Motor, propeller, battery sizing, rubber power models |
| `passive` | Full aircraft from ~10 assumptions — no manual geometry |
| `manufacturing` | Wing ribs, fuselage formers, spar webs — laser-cutter-ready parts |
| `expand` | 3D surface unfolding → 2D cutting templates |
| `viz` | 3D visualization, mesh generation |
| `cad` | DXF R12 export (planforms, airfoils, layered part sheets) |
| `utils` | ISA atmosphere, Reynolds, trig helpers, interpolation |
| `webui/` | Dash web GUI — interactive dashboard, workbench (JSON stage runner) |

## Passive Design Pipeline

The passive pipeline ([`passive.py`](rc_aircraft_design/passive.py)) sizes a complete conventional-layout aircraft from a handful of mission assumptions. The output is a standard `ConventionalConcept` — identical to what you'd build by hand — so every analysis module works on it.

```
Airfoil assumptions → Constraint analysis (T/W vs W/S)
     → Weight & power sizing → Wing geometry → Stability check
```

Define a mission as JSON with ~10 parameters (see [`data/examples/missions/`](data/examples/missions/)):

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

Six mission profiles are included:

| Mission | File | Payload | Speed | Key trait |
|---------|------|---------|-------|-----------|
| Sport Flyer | [`passive_sport_flyer.json`](data/examples/passive_sport_flyer.json) | 0.25 kg | 18 m/s | Balanced weekend flyer |
| Aerial Survey | [`aerial_survey.json`](data/examples/missions/aerial_survey.json) | 0.50 kg | 14 m/s | Heavy camera, long loiter |
| 3D Aerobat | [`aerobat_3d.json`](data/examples/missions/aerobat_3d.json) | 0.15 kg | 22 m/s | 15 m/s climb, 70° bank |
| FPV Racer | [`fpv_racer.json`](data/examples/missions/fpv_racer.json) | 0.35 kg | 30 m/s | High speed, 60° bank |
| Park Flyer | [`park_flyer.json`](data/examples/missions/park_flyer.json) | 0.05 kg | 8 m/s | Micro, beginner-friendly |
| Thermal Soarer | [`thermal_soarer.json`](data/examples/missions/thermal_soarer.json) | 0.02 kg | 8 m/s | No motor, high L/D |

## Manufacturing Pipeline

The manufacturing module generates every structural part needed to physically build the aircraft from flat sheet stock (balsa, plywood, foam board). From a single `ConventionalConcept` + manufacturing config, it produces:

- **Wing ribs** — airfoil-profile cutouts with spar slots, longeron notches, leading/trailing-edge rabbets, and aileron hinge cuts (configurable: which rib the aileron starts, spar count/position, lightening holes)
- **Fuselage formers** — cross-section profiles at each station with stringer notches and equipment mounting holes
- **Fuselage sides / doublers** — flat panels with cutouts for servos, battery trays, landing gear mounting
- **Spar webs** — shear webs sized from the loads analysis
- **Tail ribs & formers** — horizontal/vertical stabilizer internal structure

All parts export to **DXF R12** with part labels, then feed into [**DeepNest**](https://github.com/nicholasnelson/deepnest) (open-source nesting optimizer) for optimal sheet layout before laser cutting / CNC routing:

```
ConventionalConcept + ManufacturingConfig
    → generate_parts()  → RibProfile[], FormerProfile[], ...
    → export_dxf()      → layered DXF per part family
    → DeepNest          → nested sheet layouts → laser cutter
```

```python
from rc_aircraft_design.manufacturing import ManufacturingConfig, generate_all_parts, SparConfig
from rc_aircraft_design.manufacturing.export_dxf import export_parts_dxf

config = ManufacturingConfig()  # sensible defaults: 12 wing ribs, 6 spars per rib

# Default spars per rib: LE rod, front spar, upper longeron,
# lower longeron, rear spar, TE stock — all configurable:
config.wing.spars[1] = SparConfig("front_spar", x_frac=0.30, width_mm=6.0, height_mm=3.0)

parts = generate_all_parts(concept, config)
export_parts_dxf(parts, "sport_flyer_laser_parts.dxf")
# → open in DeepNest for sheet nesting, then cut
```

### DXF / CAD Export

Every design (not just manufacturing parts) can be exported to DXF R12 with layered planforms (WING, H_TAIL, V_TAIL) and airfoil profiles:

```python
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

## Aircraft JSON Definitions

Full aircraft definitions (geometry, airfoil, weight, power, constraints) live in [`data/examples/`](data/examples/):

| File | Description |
|------|-------------|
| [`classic_2m_glider.json`](data/examples/classic_2m_glider.json) | 2 m sailplane, no motor |
| [`sport_trainer_40.json`](data/examples/sport_trainer_40.json) | Classic .40-size sport trainer |
| [`extra_330sc_3d.json`](data/examples/extra_330sc_3d.json) | 3D aerobatic pattern plane |

These work with every analysis module and are integration-tested in [`tests/test_example_planes.py`](tests/test_example_planes.py).

## Example Scripts

| Script | Description |
|--------|-------------|
| [`smoke_test_loads.py`](examples/smoke_test_loads.py) | NACA airfoils, alpha sweeps, span loads, taper comparison, V-n envelope |
| [`test_neuralfoil.py`](examples/test_neuralfoil.py) | NeuralFoil (PINN) CL/CD/CM polars for 4 NACA foils at Re=200k |
| [`passive_design_from_assumptions.py`](examples/passive_design_from_assumptions.py) | Full aircraft from mission assumptions (single mission) |
| [`passive_design_gallery.py`](examples/passive_design_gallery.py) | Three-views, constraint diagrams, and comparison for all 6 missions |
| [`full_pipeline_demo.py`](examples/full_pipeline_demo.py) | Design → 3D viz → manufacturing parts → DXF laser-cut export |

```bash
python examples/passive_design_gallery.py   # generates all plots + DXF in results/examples/
python examples/full_pipeline_demo.py        # full pipeline: 3D views, ribs, formers, DXF
python examples/smoke_test_loads.py
```

## Testing

```bash
uv run pytest tests/ -v       # full suite
uv run pytest tests/ -q       # quick summary
uv run pytest tests/test_aero.py -v   # single module
```

| Test file | Covers |
|-----------|--------|
| `test_utils.py` | Trig helpers, ISA atmosphere, Reynolds, interpolation, geometry |
| `test_aero.py` | Thin-airfoil coefficients, compressibility, form factors, NACA generation, V-n |
| `test_wing.py` | Wing dataclass, MAC, sizing, planform coords, span loads |
| `test_stability.py` | Volume coefficients, neutral point, spiral stability |
| `test_constraints.py` | All 6 constraint types, envelope, T/W vs W/S analysis |
| `test_power.py` | Russell propeller, rubber motors, electric power, weight estimation |
| `test_expand.py` | Quad/triangle/strip unfolding, full wing surface unfold |
| `test_viz.py` | Mesh normals, fuselage & wing mesh generation |
| `test_cad.py` | DXF R12 entities, planform/airfoil/template helpers, file I/O |
| `test_example_planes.py` | End-to-end workflow for each aircraft JSON (3 planes) |
| `test_passive_design.py` | Passive pipeline across 6 missions |

342 tests pass, 1 skipped (OpenGL renderer on headless CI).

## Setup

```bash
uv sync                    # install core deps
uv sync --extra dev        # install dev deps (pytest, ruff)
uv sync --extra all        # install everything
```

## Integrations

This project connects the full design-to-manufacturing chain by integrating specialized open-source tools at each stage:

### Aerodynamics & Optimization (`uv sync --extra aero`)

| Package | Role in pipeline | Link |
|---------|-----------------|------|
| **NeuralFoil** | PINN-based airfoil analysis — ~1000× faster than XFoil, no Fortran binary, differentiable for optimization | [peterdsharpe/NeuralFoil](https://github.com/peterdsharpe/NeuralFoil) |
| **AeroSandbox** | VLM aerodynamics, ML-based surrogate models, gradient-based design optimization | [peterdsharpe/AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) |
| **XFoil** (Python wrapper) | Classical 2-D viscous panel code for validation and high-fidelity polars | [xfoil](https://pypi.org/project/xfoil/) |

### Manufacturing & Nesting

| Tool | Role in pipeline | Link |
|------|-----------------|------|
| **DeepNest** | Sheet nesting optimization for laser-cut parts — takes DXF from this tool, minimizes material waste | [deepnest](https://github.com/nicholasnelson/deepnest) |

### Git Submodules (`legacy/`)

| Submodule | Author | Description |
|-----------|--------|-------------|
| `ThomasDavid0-AircraftDesign` | Thomas David | AVL interface, XFLR5 import, atmosphere, airfoil DB, performance tools |
| `MachUpX` | USU Aero Lab | Numerical lifting-line theory, stability derivatives |
| `AirfoilDatabase` | USU Aero Lab | Airfoil database, XFoil integration, polar fitting |
| `rAviExp` | HaoLi111 | R library for model-aviation exploratory design (original source) |
| `ModelPlanePower` | HaoLi111 | Propeller design (Russell method), rubber & electric power |
| `ModelAircraftDesignTuningHandbook` | HaoLi111 | Lift-line theory & min-lift-speed calcs (Julia) |
| `eXpand` | HaoLi111 | 3D surface → 2D cutting-template unfolding (Julia) |
| `MFVN` | HaoLi111 | Multivariable function visualisation (R) |
| `WebrAviExpConvConcept` | HaoLi111 | Shiny web UI for conventional-concept sizing |
| `Open-Model-Airplane-Training` | HaoLi111 | Open-source RC aircraft training curriculum |

```bash
git clone --recurse-submodules https://github.com/<you>/rc-aircraft-design.git
# or after a shallow clone:
git submodule update --init --recursive
```
