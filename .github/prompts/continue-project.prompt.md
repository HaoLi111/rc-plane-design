---
description: "Resume unfinished rc-aircraft-design work — review the backlog, pick a task, test, and iterate. Use when: continuing development, scrutinizing quality, checking what's left to do."
agent: "agent"
argument-hint: "Optionally specify an area to focus on: webui, manufacturing, tests, docs, deepnest, README..."
---

# Continue RC Aircraft Design Project

You are resuming work on the **rc-aircraft-design** project — a full design → simulate → manufacture pipeline for fixed-wing RC aircraft.

Read [PROJECT_PLAN.md](../../PROJECT_PLAN.md) and [README.md](../../README.md) for context, then check the backlog below. Pick the highest-priority unfinished item (or the area the user specifies), work on it, run the tests, and report what you did.

## Current Architecture

```
rc_aircraft_design/          # Python library (10 modules)
├── aero/                    # ✅ Airfoil geometry, polars, NACA generation
├── wing/                    # ✅ Geometry, MAC, planform, span loads
├── stability/               # ✅ CG, neutral point, static margin
├── constraints/             # ✅ T/W vs W/S constraint diagrams
├── power/                   # ✅ Motor, prop, battery, rubber power
├── passive/                 # ✅ Full aircraft from ~10 assumptions
├── manufacturing/           # ✅ Ribs, formers, spar webs, DXF export
├── expand/                  # ✅ 3D surface → 2D cutting templates
├── viz/                     # ✅ 3D matplotlib views, mesh generation
├── cad/                     # ✅ DXF R12 writer
└── utils/                   # ✅ ISA atmosphere, Reynolds, math helpers

webui/                       # Dash web GUI (11 pages)
├── pages/                   # home, config, aero, constraints, geometry,
│                            # stability, power, loads, manufacturing,
│                            # export, workbench
├── callbacks/               # stages.py (9 analysis stages), design.py
└── components/              # sidebar, cards

examples/                    # Runnable scripts
├── full_pipeline_demo.py    # ✅ Design → 3D viz → parts → DXF
├── passive_design_gallery.py
├── smoke_test_loads.py
└── test_neuralfoil.py

tests/                       # pytest suite (~342 tests)
data/examples/               # 3 full aircraft JSONs + 6 mission profiles
```

## Backlog — Unfinished & Next Steps

### HIGH PRIORITY — Manufacturing completeness
- [ ] **More part types**: fuselage sides, doublers, motor mount, landing gear plates, wing joiner — see the reference laser-cut plan (user showed a full plan with ~40 part types; we currently generate ribs + formers + spar webs)
- [ ] **DeepNest integration**: automate DXF → DeepNest nesting → nested sheet DXF output. DeepNest repo: https://github.com/nicholasnelson/deepnest — investigate its CLI/API and write a wrapper
- [ ] **Manufacturing config completeness**: aileron hinge position, number of tail ribs, former stringer hole patterns, tab/slot interlocking joints between ribs and spars
- [ ] **Laser-cut plan validation**: compare generated DXF output against known good plans — ensure parts fit together, tabs align, grain direction markers present

### HIGH PRIORITY — WebUI polish
- [ ] **WebUI launch reliability**: the webui has had startup issues (Exit Code: 1 in recent sessions). Diagnose and fix — ensure `cd webui && python app.py` works cleanly
- [ ] **Manufacturing page**: currently only shows NACA airfoil preview and rib schedule. Should show the full rib gallery plot, former plot, and part count summary
- [ ] **3D geometry page**: add interactive 3D (Plotly mesh3d) alongside the current planform 2D views
- [ ] **Export page**: add manufacturing DXF download (laser-cut parts), not just planform DXF

### MEDIUM PRIORITY — Analysis depth  
- [ ] **NeuralFoil integration**: use PINN-based polars as default when available (currently `LinearAirfoil` only in passive pipeline). Allow user to select analysis backend
- [ ] **AeroSandbox VLM**: wire in 3D aerodynamic analysis for the full aircraft (not just 2D airfoil polars)
- [ ] **CFD mesh export**: generate surface mesh suitable for OpenFOAM or SU2 from the 3D model
- [ ] **Structural FEA**: spar bending + torsion analysis beyond the current beam model

### MEDIUM PRIORITY — Testing & quality
- [ ] **Manufacturing tests**: add test_manufacturing.py — generate parts for each example aircraft, verify rib counts, slot positions, DXF validity
- [ ] **WebUI integration tests**: Selenium or Dash testing framework to verify all pages render without error
- [ ] **Cross-platform CI**: GitHub Actions workflow for pytest + ruff on Linux/macOS/Windows
- [ ] **README image link audit**: the reference laser-cut plan image is commented out (`docs/reference_laser_cut_plan.png`) — add the file or remove the comment

### LOW PRIORITY — Documentation & packaging
- [ ] **API docs**: Sphinx or mkdocs in `docs/` — auto-generated from docstrings
- [ ] **PROJECT_PLAN.md**: outdated, doesn't reflect manufacturing, webui, or integration work. Update or replace with this backlog
- [ ] **PyPI publish**: clean up pyproject.toml for public release
- [ ] **Contribution guide**: CONTRIBUTING.md for the open-source vision

## How to Work

1. **Before coding**: run `uv run pytest tests/ -q` to get baseline test status
2. **After each change**: run tests again, check for regressions
3. **For webui work**: `cd webui && uv sync && python app.py` — verify pages load
4. **For manufacturing work**: run `uv run python examples/full_pipeline_demo.py` to see full output
5. **When done**: update this backlog (check off completed items or add new issues discovered)

## Key Commands

```bash
uv sync --extra all                          # install everything
uv run pytest tests/ -v                      # full test suite
uv run python examples/full_pipeline_demo.py # end-to-end pipeline
cd webui && uv sync && python app.py         # launch web GUI
uv run ruff check rc_aircraft_design/        # lint
```
