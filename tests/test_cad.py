"""Tests for rc_aircraft_design.cad (DxfWriter)."""

import pytest

from rc_aircraft_design.cad import DxfWriter


class TestDxfWriter:
    def test_empty_dxf_valid(self):
        dxf = DxfWriter()
        content = dxf.to_string()
        assert "AC1009" in content
        assert content.endswith("0\nEOF\n")

    def test_line_entity(self):
        dxf = DxfWriter()
        dxf.line(0, 0, 1, 1)
        content = dxf.to_string()
        assert "LINE" in content

    def test_polyline_entity(self):
        dxf = DxfWriter()
        dxf.polyline([[0, 0], [1, 0], [1, 1], [0, 1]], closed=True)
        content = dxf.to_string()
        assert "POLYLINE" in content
        assert "VERTEX" in content
        assert "SEQEND" in content

    def test_circle_entity(self):
        dxf = DxfWriter()
        dxf.circle(0, 0, 5.0)
        content = dxf.to_string()
        assert "CIRCLE" in content

    def test_arc_entity(self):
        dxf = DxfWriter()
        dxf.arc(0, 0, 5.0, 0, 90)
        content = dxf.to_string()
        assert "ARC" in content

    def test_text_entity(self):
        dxf = DxfWriter()
        dxf.text(0, 0, "Hello", height=3.0)
        content = dxf.to_string()
        assert "TEXT" in content
        assert "Hello" in content

    def test_point_entity(self):
        dxf = DxfWriter()
        dxf.point(1, 2)
        content = dxf.to_string()
        assert "POINT" in content

    def test_add_layer(self):
        dxf = DxfWriter()
        dxf.add_layer("WING", color=3)
        dxf.line(0, 0, 1, 1, layer="WING")
        content = dxf.to_string()
        assert "WING" in content

    def test_add_planform(self):
        import numpy as np
        dxf = DxfWriter()
        x = np.array([0, 0.3, 0.5, 0.2, 0])
        y = np.array([0, 0, 0.75, 0.75, 0])
        dxf.add_planform(x, y)
        content = dxf.to_string()
        assert "PLANFORM" in content

    def test_add_airfoil(self):
        from rc_aircraft_design.aero import naca4
        x, yu, yl = naca4("2412", n_points=30)
        dxf = DxfWriter()
        dxf.add_airfoil(x, yu, yl, chord=0.3)
        content = dxf.to_string()
        assert "AIRFOIL" in content

    def test_add_cutting_template(self):
        dxf = DxfWriter()
        left = [(0, 0), (0, 1), (0, 2)]
        right = [(1, 0), (1.1, 1), (1, 2)]
        dxf.add_cutting_template(left, right)
        content = dxf.to_string()
        assert "TEMPLATE" in content

    def test_save_and_read(self, tmp_path):
        dxf = DxfWriter()
        dxf.line(0, 0, 1, 1)
        dxf.circle(0, 0, 5)
        out = tmp_path / "test.dxf"
        dxf.save(out)
        assert out.exists()
        text = out.read_text(encoding="ascii")
        assert "AC1009" in text
        assert "LINE" in text
