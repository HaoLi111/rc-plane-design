"""Tests for rc_aircraft_design.viz (renderer)."""

import numpy as np
import pytest

from rc_aircraft_design.viz import Mesh, fuselage_mesh, wing_mesh


# -- Mesh -------------------------------------------------------------------

class TestMesh:
    def test_compute_normal(self):
        n = Mesh.compute_normal(
            np.array([0, 0, 0]),
            np.array([1, 0, 0]),
            np.array([0, 1, 0]),
        )
        np.testing.assert_allclose(n, [0, 0, 1], atol=1e-12)

    def test_degenerate_triangle_normal(self):
        # Collinear points → fallback normal
        n = Mesh.compute_normal(
            np.array([0, 0, 0]),
            np.array([1, 0, 0]),
            np.array([2, 0, 0]),
        )
        assert np.linalg.norm(n) == pytest.approx(1.0)

    def test_from_vertices_and_indices(self):
        verts = np.array([
            [0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0],
        ], dtype=np.float32)
        indices = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
        mesh = Mesh.from_vertices_and_indices(verts, indices)
        assert mesh.vertices.shape == (4, 3)
        assert mesh.normals.shape == (4, 3)
        # All normals should point in z direction for flat quad
        for i in range(4):
            assert abs(mesh.normals[i, 2]) > 0.9


# -- Fuselage mesh ----------------------------------------------------------

class TestFuselageMesh:
    def test_circle_fuselage(self):
        mesh = fuselage_mesh(
            stations=[0, 0.2, 0.5, 1.0],
            radii=[0.05, 0.1, 0.1, 0.0],
        )
        assert isinstance(mesh, Mesh)
        assert mesh.vertices.shape[1] == 3
        assert mesh.indices.shape[1] == 3
        assert mesh.normals.shape == mesh.vertices.shape

    def test_square_fuselage(self):
        mesh = fuselage_mesh(
            stations=[0, 0.5, 1.0],
            radii=[0.05, 0.1, 0.0],
            shape="square",
        )
        assert mesh.vertices.shape[0] > 0

    def test_from_plane_json(self, sport_trainer):
        fus = sport_trainer["fuselage"]
        mesh = fuselage_mesh(
            stations=fus["stations"],
            radii=fus["radii"],
        )
        assert mesh.vertices.shape[0] > 0


# -- Wing mesh --------------------------------------------------------------

class TestWingMesh:
    def test_basic_wing_mesh(self):
        from rc_aircraft_design.aero import naca4
        x, yu, yl = naca4("2412", n_points=20)
        mesh = wing_mesh(x, yu, yl, chord_root=0.3, chord_tip=0.2, span=0.75, n_span=5)
        assert isinstance(mesh, Mesh)
        assert mesh.vertices.shape[1] == 3
        assert mesh.indices.shape[1] == 3

    def test_swept_wing_mesh(self):
        from rc_aircraft_design.aero import naca4
        x, yu, yl = naca4("0012", n_points=15)
        mesh = wing_mesh(x, yu, yl, chord_root=0.3, chord_tip=0.2, span=0.75, n_span=5, sweep_offset=0.05)
        assert mesh.vertices.shape[0] > 0
