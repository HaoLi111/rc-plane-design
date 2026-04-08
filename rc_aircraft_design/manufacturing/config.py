"""Manufacturing configuration — everything needed to cut and build an RC aircraft.

Captures the structural details visible in laser-cut plan sheets:
rib count & spacing, spar positions, control surface hinge lines,
material thickness, tab/slot dimensions, and fuselage former profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ControlSurfaceConfig:
    """Control surface definition (aileron, elevator, rudder, flap)."""

    name: str                        # e.g. "aileron_right"
    type: str = "aileron"            # aileron | elevator | rudder | flap
    start_rib: int = 0               # first rib index (from root) where it begins
    end_rib: int = -1                # last rib index (-1 = tip)
    hinge_x_frac: float = 0.72       # hinge line as fraction of local chord from LE
    max_deflection_deg: float = 25.0  # max deflection


@dataclass
class SparConfig:
    """A single spar / longeron / rod member running spanwise through ribs."""

    name: str                          # e.g. "main_spar", "le_rod", "upper_longeron"
    x_frac: float                      # chordwise position as fraction of chord from LE
    width_mm: float = 6.0             # cross-section width (chordwise)
    height_mm: float = 3.0            # cross-section height (thickness direction)
    surface: str = "center"            # "upper" | "lower" | "center" — where the slot sits
    # "upper"  = slot notched down from upper skin
    # "lower"  = slot notched up from lower skin
    # "center" = full-depth slot through rib (traditional spar)


@dataclass
class WingBuildConfig:
    """Wing panel manufacturing configuration."""

    n_ribs: int = 12                  # total rib count (one half)

    # ── Spanwise structural members ─────────────────────────────────
    # Each entry creates a slot in every rib.  Typical RC wing has:
    #   LE rod, front spar, rear spar, upper/lower longerons, TE stock
    spars: list[SparConfig] = field(default_factory=lambda: [
        SparConfig("le_rod",         x_frac=0.03, width_mm=5.0, height_mm=5.0, surface="center"),
        SparConfig("front_spar",     x_frac=0.25, width_mm=6.0, height_mm=3.0, surface="center"),
        SparConfig("upper_longeron", x_frac=0.40, width_mm=3.0, height_mm=3.0, surface="upper"),
        SparConfig("lower_longeron", x_frac=0.40, width_mm=3.0, height_mm=3.0, surface="lower"),
        SparConfig("rear_spar",      x_frac=0.65, width_mm=6.0, height_mm=3.0, surface="center"),
        SparConfig("te_stock",       x_frac=0.97, width_mm=6.0, height_mm=3.0, surface="center"),
    ])

    material_thickness_mm: float = 3.0  # sheet material (plywood/balsa/foam)
    tab_width_mm: float = 5.0        # interlocking tab width
    tab_depth_mm: float = 3.0        # tab depth (= material thickness usually)
    le_sheeting: bool = True          # leading edge D-box sheeting
    le_sheeting_frac: float = 0.15    # D-box extent as fraction of chord
    dihedral_break_rib: int | None = None  # rib index where dihedral changes (polyhedral)
    washout_deg: float = 0.0         # tip washout [deg]
    control_surfaces: list[ControlSurfaceConfig] = field(default_factory=list)

    # ── Lightening holes ────────────────────────────────────────────
    lightening_holes: bool = True     # cut weight-saving holes between spars
    lightening_hole_margin_mm: float = 4.0  # min clearance from spar edges
    lightening_hole_min_width_mm: float = 12.0  # skip holes in gaps smaller than this
    lightening_hole_height_frac: float = 0.55   # hole height as fraction of local airfoil thickness

    # ── Doublers ────────────────────────────────────────────────────
    root_doubler: bool = True         # include root rib doubler (thicker, cross-braced)
    tip_doubler: bool = False         # include tip rib doubler


@dataclass
class FuselageBuildConfig:
    """Fuselage manufacturing configuration (former-and-longeron construction)."""

    n_formers: int = 8                # number of cross-section formers
    longeron_count: int = 4           # number of longerons (stringers)
    material_thickness_mm: float = 3.0
    tab_width_mm: float = 5.0
    firewall_thickness_mm: float = 6.0  # motor mount firewall
    battery_hatch_former: int = 2     # former index where battery hatch starts
    battery_hatch_length_mm: float = 80.0
    wing_saddle_former: int = 2       # former index for wing saddle
    wing_saddle_width_mm: float = 0.0  # auto-computed from wing root chord

    # ── Stringer notches in formers ────────────────────────────────
    stringer_notch_width_mm: float = 3.0   # notch width for longerons
    stringer_notch_depth_mm: float = 3.0   # notch depth into former edge

    # ── Firewall ───────────────────────────────────────────────────
    firewall: bool = True             # generate motor-mount firewall
    motor_mount_holes: int = 4        # number of motor mounting bolt holes
    motor_mount_spacing_mm: float = 25.0  # bolt pattern diameter

    # ── Side panels ────────────────────────────────────────────────
    side_panels: bool = True          # generate fuselage side panels
    side_panel_battery_cutout: bool = True   # battery access window
    side_panel_servo_cutout: bool = True     # servo access window
    side_panel_tab_count: int = 0     # auto-computed from n_formers

    # Fuselage profile: list of (x_frac, width_mm, height_mm) stations
    # If empty, auto-generated from ConventionalConcept fuselage geometry
    profile_stations: list[tuple[float, float, float]] = field(default_factory=list)


@dataclass
class ManufacturingConfig:
    """Complete manufacturing configuration for one aircraft."""

    name: str = "unnamed"
    wing: WingBuildConfig = field(default_factory=WingBuildConfig)
    fuselage: FuselageBuildConfig = field(default_factory=FuselageBuildConfig)
    htail: WingBuildConfig = field(default_factory=lambda: WingBuildConfig(
        n_ribs=6,
        spars=[
            SparConfig("le_rod",     x_frac=0.03, width_mm=3.0, height_mm=3.0, surface="center"),
            SparConfig("main_spar",  x_frac=0.30, width_mm=4.0, height_mm=2.0, surface="center"),
            SparConfig("te_stock",   x_frac=0.97, width_mm=4.0, height_mm=2.0, surface="center"),
        ],
        material_thickness_mm=2.0,
        le_sheeting=False,
        control_surfaces=[ControlSurfaceConfig(name="elevator", type="elevator",
                                                start_rib=0, end_rib=-1,
                                                hinge_x_frac=0.65)],
    ))
    vtail: WingBuildConfig = field(default_factory=lambda: WingBuildConfig(
        n_ribs=4,
        spars=[
            SparConfig("le_rod",     x_frac=0.03, width_mm=3.0, height_mm=3.0, surface="center"),
            SparConfig("main_spar",  x_frac=0.30, width_mm=4.0, height_mm=2.0, surface="center"),
            SparConfig("te_stock",   x_frac=0.97, width_mm=4.0, height_mm=2.0, surface="center"),
        ],
        material_thickness_mm=2.0,
        le_sheeting=False,
        control_surfaces=[ControlSurfaceConfig(name="rudder", type="rudder",
                                                start_rib=0, end_rib=-1,
                                                hinge_x_frac=0.60)],
    ))
    sheet_width_mm: float = 600.0     # laser cutter bed width
    sheet_height_mm: float = 400.0    # laser cutter bed height
    kerf_mm: float = 0.15            # laser kerf compensation


def make_sport_flyer_config() -> ManufacturingConfig:
    """Example configuration for a ~1 kg sport flyer."""
    return ManufacturingConfig(
        name="sport_flyer",
        wing=WingBuildConfig(
            n_ribs=12,
            spars=[
                SparConfig("le_rod",         x_frac=0.03, width_mm=5.0, height_mm=5.0, surface="center"),
                SparConfig("front_spar",     x_frac=0.25, width_mm=6.0, height_mm=3.0, surface="center"),
                SparConfig("upper_longeron", x_frac=0.42, width_mm=3.0, height_mm=3.0, surface="upper"),
                SparConfig("lower_longeron", x_frac=0.42, width_mm=3.0, height_mm=3.0, surface="lower"),
                SparConfig("rear_spar",      x_frac=0.65, width_mm=6.0, height_mm=3.0, surface="center"),
                SparConfig("te_stock",       x_frac=0.97, width_mm=6.0, height_mm=3.0, surface="center"),
            ],
            material_thickness_mm=3.0,
            le_sheeting=True,
            le_sheeting_frac=0.15,
            washout_deg=1.5,
            control_surfaces=[
                ControlSurfaceConfig(
                    name="aileron_right", type="aileron",
                    start_rib=7, end_rib=-1,
                    hinge_x_frac=0.72, max_deflection_deg=25.0,
                ),
            ],
        ),
        fuselage=FuselageBuildConfig(
            n_formers=8,
            longeron_count=4,
            material_thickness_mm=3.0,
            firewall_thickness_mm=6.0,
            battery_hatch_former=2,
            battery_hatch_length_mm=80.0,
        ),
    )
