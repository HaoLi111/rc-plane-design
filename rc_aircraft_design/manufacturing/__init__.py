"""Manufacturing parts generation — ribs, spars, formers, laser-cut sheets."""

from .config import ManufacturingConfig, WingBuildConfig, FuselageBuildConfig, ControlSurfaceConfig, SparConfig
from .parts import (
    generate_wing_ribs, generate_fuselage_formers, generate_all_parts,
    ManufacturingParts, RibProfile, FormerProfile, SlotRect,
    LighteningHole, FuselageSidePanel, Firewall, Doubler,
)
