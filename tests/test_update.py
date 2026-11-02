"""`copier update` of a brain: Copier replays the old and new overlay versions into empty
directories, without `.copier-answers.base.yml`, so the overlay reads base's answers from the
`base_answers` copy it records in its own answers file (issue #1, template-base decision 0001).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml
from conftest import BASE, BRAIN
from stacking import GIT, ROOT, checks, commit, copy, sh, stage

EDIT = "A line the brain added.\n"


def test_update_keeps_base_answers(base_src: Path, tmp_path: Path) -> None:
    """Obsidian v1.0.0 -> v1.1.0: base's values stay, the brain's edit survives, no conflicts."""
    obsidian = stage(ROOT, tmp_path / "template-obsidian")
    project = tmp_path / "demo"
    copy(base_src, project, BASE)
    copy(obsidian, project, BRAIN)
    commit(project)
    stack_md = project / ".agents/stack.md"
    stack_md.write_text(stack_md.read_text() + f"\n{EDIT}")
    commit(project)

    config = obsidian / "template/.github/ISSUE_TEMPLATE/config.yml.jinja"
    config.write_text(config.read_text().replace("never in a public issue", "never in a public issue of demo"))
    sh(*GIT, "commit", "-qam", "v1.1.0", cwd=obsidian)
    sh("git", "tag", "v1.1.0", cwd=obsidian)
    sh(sys.executable, "-m", "copier", "update", "-a", ".copier-answers.stack-obsidian.yml", "--trust",
       "--skip-tasks", "--defaults", "--conflict", "inline", cwd=project)  # fmt: skip

    text = (project / ".github/ISSUE_TEMPLATE/config.yml").read_text()
    assert "https://github.com/metalayerlab/demo/security/advisories/new" in text
    assert "never in a public issue of demo" in text
    assert (project / "README.md").read_text().startswith("# demo\n\nA demo brain\n")
    assert EDIT in stack_md.read_text()
    answers = yaml.safe_load((project / ".copier-answers.stack-obsidian.yml").read_text())
    assert answers["_commit"] == "v1.1.0"
    assert answers["base_answers"]["project_name"] == "demo"
    assert answers["base_answers"]["description"] == "A demo brain"

    tracked = sh("git", "ls-files", "--others", "--cached", "--exclude-standard", cwd=project).splitlines()
    marker = re.compile(r"^(<{7}|>{7}) ", re.MULTILINE)
    marked = [n for n in tracked if (project / n).is_file() and marker.search((project / n).read_text(errors="ignore"))]
    assert marked == [], f"conflict markers in {marked}"
    assert not list(project.rglob("*.rej"))
    result = checks(commit(project))
    assert result.returncode == 0, result.stdout + result.stderr


def test_recopy_message(base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    """A recopy prints the copy message (issue #9): it must not tell an existing brain to make its first commit."""
    project = tmp_path / "demo"
    copy(base_src, project, BASE)
    copy(obsidian_src, project, BRAIN)
    commit(project)
    recopy = subprocess.run([sys.executable, "-m", "copier", "recopy", "-a", ".copier-answers.stack-obsidian.yml",
                             "--trust", "--skip-tasks", "--defaults", "--overwrite"],
                            cwd=project, capture_output=True, text=True, check=True)  # fmt: skip
    lines = recopy.stderr.splitlines()
    assert any(line.strip().startswith("A recopy: run sh scripts/post-update.sh") for line in lines), recopy.stderr
    assert all(line.strip().startswith("A new brain:") for line in lines if "initial commit" in line), recopy.stderr
