from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from stacking import ROOT, commit, copy, sibling, stage  # noqa: E402

# The base version this overlay needs, and its tests render (staged copies are tagged with it).
BASE_VERSION = "v2.0.0"
BASE = {"project_name": "demo", "description": "A demo brain", "github_owner": "metalayerlab"}
BRAIN = {"vault_dir": "knowledge", "brain_pull": True}


@pytest.fixture(scope="session")
def base_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """template-base at its latest: ../template-base, or $TEMPLATE_BASE."""
    base = sibling("template-base", "TEMPLATE_BASE")
    if base is None:
        pytest.fail("template-base must be checked out next to this repository, or set TEMPLATE_BASE")
    return stage(base, tmp_path_factory.mktemp("src") / "template-base", tag=BASE_VERSION)


@pytest.fixture(scope="session")
def obsidian_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return stage(ROOT, tmp_path_factory.mktemp("src") / "template-obsidian")


def render(base_src: Path, obsidian_src: Path, dst: Path, base: dict | None = None, **answers: object) -> Path:
    copy(base_src, dst, {**BASE, **(base or {})})
    copy(obsidian_src, dst, {**BRAIN, **answers})
    return commit(dst)


@pytest.fixture(scope="session")
def project(base_src: Path, obsidian_src: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """base + obsidian, the vault in knowledge/, with Brain pull."""
    return render(base_src, obsidian_src, tmp_path_factory.mktemp("render") / "demo")
