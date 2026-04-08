"""Shared fixtures for rc_aircraft_design tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "examples"

PLANE_FILES = sorted(DATA_DIR.glob("*.json"))


def _load_plane(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(params=PLANE_FILES, ids=lambda p: p.stem)
def plane_data(request) -> dict:
    """Parametrised fixture: yields each example plane JSON as a dict."""
    return _load_plane(request.param)


@pytest.fixture()
def sport_trainer() -> dict:
    return _load_plane(DATA_DIR / "sport_trainer_40.json")


@pytest.fixture()
def extra_330() -> dict:
    return _load_plane(DATA_DIR / "extra_330sc_3d.json")


@pytest.fixture()
def glider() -> dict:
    return _load_plane(DATA_DIR / "classic_2m_glider.json")
