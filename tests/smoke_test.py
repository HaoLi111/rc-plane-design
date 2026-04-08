"""Smoke test for all rc_aircraft_design modules."""
from rc_aircraft_design import aero, wing, stability, constraints, power, expand, viz, cad, utils
print("All modules imported successfully!")

from rc_aircraft_design.aero import LinearAirfoil, naca4
af = LinearAirfoil()
result = af.analyze()
print(f"Alpha analysis: Clmax={result.Clmax:.3f} at alpha={result.alpha_Clmax:.1f} deg")
print(f"  L/D max={result.LDmax:.2f} at alpha={result.alpha_LDmax:.1f} deg")

x, yu, yl = naca4("2412")
print(f"NACA 2412: {len(x)} points, max thickness={max(yu-yl):.4f}c")

from rc_aircraft_design.wing import Wing, compute_mac
w = Wing(chord_root=0.5, chord_tip=0.3, span=1.6, sweep_deg=10)
mac = compute_mac(w)
print(f"Wing: AR={w.aspect_ratio:.2f}, MAC={mac.mac_length:.4f}m")

from rc_aircraft_design.constraints import analyze_constraints
cr = analyze_constraints()
print(f"Constraints: {len(cr.W_S)} W/S points, min envelope T/W={cr.envelope.min():.3f}")

from rc_aircraft_design.cad import DxfWriter
dxf = DxfWriter()
dxf.line(0, 0, 1, 1)
content = dxf.to_string()
has_version = "AC1009" in content
print(f"DXF output: {len(content)} chars, has AC1009: {has_version}")

from rc_aircraft_design.power import design_propeller_russell, thrust_russell
prop = design_propeller_russell(RPM=8000, speed_ms=15)
T = thrust_russell(prop.radius, prop.pitch, 8000)
print(f"Propeller: D={prop.diameter*100:.1f}cm, pitch={prop.pitch*100:.1f}cm, thrust={T:.1f}N")

from rc_aircraft_design.utils import density_isa, dynamic_pressure
rho = density_isa(0)
q = dynamic_pressure(20, rho)
print(f"ISA sea level: rho={rho:.3f} kg/m3, q(20m/s)={q:.1f} Pa")

print("\nAll smoke tests passed!")
