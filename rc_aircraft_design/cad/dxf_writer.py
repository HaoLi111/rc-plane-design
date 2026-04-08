"""DXF file writer using native DXF grammar (no heavy dependencies).

Generates DXF R12 (AC1009) files that can be opened in any CAD program.
No external libraries required for basic 2D entities.
"""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

import numpy as np
from numpy.typing import ArrayLike


class DxfWriter:
    """Minimal DXF R12 writer for 2D CAD export."""

    def __init__(self):
        self._entities: list[str] = []
        self._layer_colors: dict[str, int] = {"0": 7}  # default layer, white

    def add_layer(self, name: str, color: int = 7):
        """Register a layer with a color (1=red, 2=yellow, 3=green, 4=cyan, 5=blue, 7=white)."""
        self._layer_colors[name] = color

    # -- Entity primitives ---------------------------------------------------

    def line(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        layer: str = "0",
    ):
        """Add a LINE entity."""
        self._entities.append(
            f"0\nLINE\n8\n{layer}\n"
            f"10\n{x1:.6f}\n20\n{y1:.6f}\n30\n0.0\n"
            f"11\n{x2:.6f}\n21\n{y2:.6f}\n31\n0.0\n"
        )

    def polyline(
        self,
        points: ArrayLike,
        closed: bool = False,
        layer: str = "0",
    ):
        """Add a POLYLINE entity from an (N, 2) array of points."""
        pts = np.asarray(points, dtype=float)
        flag = 1 if closed else 0
        self._entities.append(f"0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n{flag}\n")
        for x, y in pts:
            self._entities.append(
                f"0\nVERTEX\n8\n{layer}\n10\n{x:.6f}\n20\n{y:.6f}\n30\n0.0\n"
            )
        self._entities.append(f"0\nSEQEND\n8\n{layer}\n")

    def circle(self, cx: float, cy: float, r: float, layer: str = "0"):
        """Add a CIRCLE entity."""
        self._entities.append(
            f"0\nCIRCLE\n8\n{layer}\n"
            f"10\n{cx:.6f}\n20\n{cy:.6f}\n30\n0.0\n"
            f"40\n{r:.6f}\n"
        )

    def arc(
        self,
        cx: float, cy: float, r: float,
        start_deg: float, end_deg: float,
        layer: str = "0",
    ):
        """Add an ARC entity."""
        self._entities.append(
            f"0\nARC\n8\n{layer}\n"
            f"10\n{cx:.6f}\n20\n{cy:.6f}\n30\n0.0\n"
            f"40\n{r:.6f}\n50\n{start_deg:.6f}\n51\n{end_deg:.6f}\n"
        )

    def text(
        self,
        x: float, y: float,
        content: str,
        height: float = 2.5,
        layer: str = "0",
    ):
        """Add a TEXT entity."""
        self._entities.append(
            f"0\nTEXT\n8\n{layer}\n"
            f"10\n{x:.6f}\n20\n{y:.6f}\n30\n0.0\n"
            f"40\n{height:.6f}\n1\n{content}\n"
        )

    def point(self, x: float, y: float, layer: str = "0"):
        """Add a POINT entity."""
        self._entities.append(
            f"0\nPOINT\n8\n{layer}\n"
            f"10\n{x:.6f}\n20\n{y:.6f}\n30\n0.0\n"
        )

    # -- High-level helpers --------------------------------------------------

    def add_planform(self, x: ArrayLike, y: ArrayLike, layer: str = "PLANFORM"):
        """Add a wing planform outline as a closed polyline."""
        self.add_layer(layer, color=3)
        pts = np.column_stack([np.asarray(x), np.asarray(y)])
        self.polyline(pts, closed=True, layer=layer)

    def add_airfoil(
        self,
        x: ArrayLike, y_upper: ArrayLike, y_lower: ArrayLike,
        chord: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        layer: str = "AIRFOIL",
    ):
        """Add an airfoil profile as a closed polyline."""
        self.add_layer(layer, color=5)
        ax = np.asarray(x) * chord + offset_x
        ayu = np.asarray(y_upper) * chord + offset_y
        ayl = np.asarray(y_lower) * chord + offset_y
        # Upper surface forward, lower surface backward → closed loop
        px = np.concatenate([ax, ax[::-1]])
        py = np.concatenate([ayu, ayl[::-1]])
        pts = np.column_stack([px, py])
        self.polyline(pts, closed=True, layer=layer)

    def add_cutting_template(
        self,
        left_pts: list[tuple[float, float]],
        right_pts: list[tuple[float, float]],
        layer: str = "TEMPLATE",
    ):
        """Add an unfolded surface template as polylines."""
        self.add_layer(layer, color=1)
        # Left edge
        pts_l = np.array(left_pts)
        self.polyline(pts_l, closed=False, layer=layer)
        # Right edge
        pts_r = np.array(right_pts)
        self.polyline(pts_r, closed=False, layer=layer)
        # Connect top and bottom
        self.line(pts_l[0][0], pts_l[0][1], pts_r[0][0], pts_r[0][1], layer)
        self.line(pts_l[-1][0], pts_l[-1][1], pts_r[-1][0], pts_r[-1][1], layer)

    # -- File output ---------------------------------------------------------

    def _header(self) -> str:
        return (
            "0\nSECTION\n2\nHEADER\n"
            "9\n$ACADVER\n1\nAC1009\n"
            "0\nENDSEC\n"
        )

    def _tables(self) -> str:
        lines = "0\nSECTION\n2\nTABLES\n"
        lines += f"0\nTABLE\n2\nLAYER\n70\n{len(self._layer_colors)}\n"
        for name, color in self._layer_colors.items():
            lines += (
                f"0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\nCONTINUOUS\n"
            )
        lines += "0\nENDTAB\n0\nENDSEC\n"
        return lines

    def _entities_section(self) -> str:
        return "0\nSECTION\n2\nENTITIES\n" + "".join(self._entities) + "0\nENDSEC\n"

    def to_string(self) -> str:
        """Generate complete DXF file content as a string."""
        return self._header() + self._tables() + self._entities_section() + "0\nEOF\n"

    def save(self, filepath: str | Path):
        """Write DXF file to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.to_string(), encoding="ascii")
