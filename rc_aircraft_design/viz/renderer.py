"""OpenGL 3D visualization: fuselage sections, wing extrusion.

Uses PyOpenGL + GLFW for rendering circle/square fuselage cross-sections
extruded along the centerline, and wing surfaces extruded from NACA profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike


@dataclass
class Mesh:
    """Simple triangle mesh for rendering."""

    vertices: np.ndarray   # (N, 3) float32
    normals: np.ndarray    # (N, 3) float32
    indices: np.ndarray    # (M, 3) uint32 — triangle indices

    @staticmethod
    def compute_normal(v0, v1, v2):
        """Compute face normal from three vertices."""
        e1 = v1 - v0
        e2 = v2 - v0
        n = np.cross(e1, e2)
        norm = np.linalg.norm(n)
        return n / norm if norm > 1e-12 else np.array([0.0, 0.0, 1.0])

    @classmethod
    def from_vertices_and_indices(cls, vertices: np.ndarray, indices: np.ndarray) -> Mesh:
        """Build a Mesh with auto-computed per-vertex normals."""
        normals = np.zeros_like(vertices)
        for tri in indices:
            v0, v1, v2 = vertices[tri[0]], vertices[tri[1]], vertices[tri[2]]
            n = cls.compute_normal(v0, v1, v2)
            for idx in tri:
                normals[idx] += n
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms < 1e-12] = 1.0
        normals /= norms
        return cls(vertices=vertices, normals=normals, indices=indices)


def fuselage_mesh(
    stations: ArrayLike,
    radii: ArrayLike,
    n_circumference: int = 24,
    shape: str = "circle",
    width: float | None = None,
    height: float | None = None,
) -> Mesh:
    """Generate a fuselage mesh from station-radius profile.

    Parameters
    ----------
    stations : x-positions along the fuselage [m]
    radii : radius at each station [m]
    n_circumference : number of points around the cross-section
    shape : "circle", "square", or "box"
    width, height : explicit cross-section dimensions for box fuselage [m]
    """
    stations = np.asarray(stations, dtype=np.float32)
    radii = np.asarray(radii, dtype=np.float32)
    ns = len(stations)
    nc = n_circumference

    if shape in ("square", "box"):
        # Box/square cross-section: 4 sides with subdivisions
        t = np.linspace(0, 2 * np.pi, nc, endpoint=False)
        cos_t = np.cos(t)
        sin_t = np.sin(t)
        max_cs = np.maximum(np.abs(cos_t), np.abs(sin_t))
        cy = cos_t / max_cs
        cz = sin_t / max_cs
    else:
        # Circle
        t = np.linspace(0, 2 * np.pi, nc, endpoint=False)
        cy = np.cos(t)
        cz = np.sin(t)

    # Build vertices
    verts = []
    max_r = float(np.max(radii)) if np.max(radii) > 0 else 1.0
    for i in range(ns):
        if shape == "box" and width is not None and height is not None:
            # Box fuselage: scale the constant width/height by radius ratio
            scale = radii[i] / max_r if max_r > 0 else 1.0
            ry = width / 2 * scale
            rz = height / 2 * scale
        else:
            ry = radii[i]
            rz = radii[i]
        for j in range(nc):
            verts.append([stations[i], ry * cy[j], rz * cz[j]])
    vertices = np.array(verts, dtype=np.float32)

    # Build triangle indices (quad strips between stations)
    indices = []
    for i in range(ns - 1):
        for j in range(nc):
            j_next = (j + 1) % nc
            v00 = i * nc + j
            v01 = i * nc + j_next
            v10 = (i + 1) * nc + j
            v11 = (i + 1) * nc + j_next
            indices.append([v00, v10, v01])
            indices.append([v01, v10, v11])
    indices = np.array(indices, dtype=np.uint32)

    return Mesh.from_vertices_and_indices(vertices, indices)


def wing_mesh(
    airfoil_x: ArrayLike,
    airfoil_yu: ArrayLike,
    airfoil_yl: ArrayLike,
    chord_root: float,
    chord_tip: float,
    span: float,
    n_span: int = 20,
    sweep_offset: float = 0.0,
) -> Mesh:
    """Generate wing mesh by extruding NACA profile from root to tip.

    Parameters
    ----------
    airfoil_x : normalized x coordinates (0–1)
    airfoil_yu, airfoil_yl : upper and lower surface y coordinates
    chord_root, chord_tip : root/tip chord [m]
    span : half-span [m]
    n_span : number of spanwise sections
    sweep_offset : total LE sweep offset at tip [m]
    """
    ax = np.asarray(airfoil_x, dtype=np.float32)
    ayu = np.asarray(airfoil_yu, dtype=np.float32)
    ayl = np.asarray(airfoil_yl, dtype=np.float32)
    nc = len(ax)

    # Combine upper + lower into closed loop (upper forward, lower backward)
    profile_x = np.concatenate([ax, ax[::-1]])
    profile_y = np.concatenate([ayu, ayl[::-1]])
    np_circ = len(profile_x)

    spanwise = np.linspace(0, span, n_span + 1)

    verts = []
    for i, y_pos in enumerate(spanwise):
        frac = y_pos / span
        chord = chord_root + (chord_tip - chord_root) * frac
        x_offset = sweep_offset * frac
        for j in range(np_circ):
            verts.append([
                x_offset + profile_x[j] * chord,
                y_pos,
                profile_y[j] * chord,
            ])
    vertices = np.array(verts, dtype=np.float32)
    ns = n_span + 1

    indices = []
    for i in range(ns - 1):
        for j in range(np_circ):
            j_next = (j + 1) % np_circ
            v00 = i * np_circ + j
            v01 = i * np_circ + j_next
            v10 = (i + 1) * np_circ + j
            v11 = (i + 1) * np_circ + j_next
            indices.append([v00, v10, v01])
            indices.append([v01, v10, v11])
    indices = np.array(indices, dtype=np.uint32)

    return Mesh.from_vertices_and_indices(vertices, indices)


# ---------------------------------------------------------------------------
# OpenGL rendering (optional, requires PyOpenGL + glfw)
# ---------------------------------------------------------------------------

def render_meshes(meshes: list[Mesh], title: str = "RC Aircraft Viewer"):
    """Open an OpenGL window and render a list of meshes.

    Requires: pip install PyOpenGL glfw
    """
    try:
        import glfw
        from OpenGL.GL import (
            GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
            GL_FLOAT, GL_LIGHTING, GL_LIGHT0, GL_TRIANGLES, GL_UNSIGNED_INT,
            glClear, glClearColor, glEnable, glEnableClientState,
            glVertexPointer, glNormalPointer, glDrawElements,
            GL_VERTEX_ARRAY, GL_NORMAL_ARRAY,
            glLoadIdentity, glRotatef, glTranslatef, glScalef,
        )
        from OpenGL.GLU import gluPerspective
    except ImportError:
        raise ImportError(
            "OpenGL visualization requires PyOpenGL and glfw. "
            "Install with: uv pip install PyOpenGL glfw"
        )

    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")

    window = glfw.create_window(800, 600, title, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create GLFW window")

    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glClearColor(0.15, 0.15, 0.2, 1.0)

    rotation = [30.0, -45.0]

    while not glfw.window_should_close(window):
        glfw.poll_events()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluPerspective(45, 800 / 600, 0.1, 100.0)
        glTranslatef(0, 0, -3)
        glRotatef(rotation[0], 1, 0, 0)
        glRotatef(rotation[1], 0, 1, 0)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        for mesh in meshes:
            glVertexPointer(3, GL_FLOAT, 0, mesh.vertices)
            glNormalPointer(GL_FLOAT, 0, mesh.normals)
            glDrawElements(GL_TRIANGLES, mesh.indices.size, GL_UNSIGNED_INT, mesh.indices)

        glfw.swap_buffers(window)
        rotation[1] += 0.3  # slow rotation

    glfw.terminate()
