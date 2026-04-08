"""Power & propulsion: motor, propeller, battery sizing, rubber power models."""

from .propulsion import (
    Propeller, design_propeller_russell, thrust_russell,
    rubber_breaking_turns_millman, rubber_torque,
    rubber_breaking_turns_sherman, rubber_torque_sherman,
    ElectricPowerSystem, WeightEstimate,
)
