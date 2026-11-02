"""Render template-base at its latest, then template-obsidian, and check the brain that results.

    uv run pytest                 # every test (../template-base, or $TEMPLATE_BASE)
    uv run pytest -m docker       # also the secret scan through Docker

The render must pass its own Definition of done (`sh scripts/checks.sh`) unchanged.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import BASE, BRAIN, render
from stacking import ROOT, checks, commit, copy, sh, stage

PULL = ".github/workflows/obsidian-brain-pull.yml"
GATE = "scripts/brain-pull-gate.py"
PULL_FILES = [PULL, GATE, "knowledge/🛰️ Subscriptions.md"]


def test_checks_pass(project: Path) -> None:
    result = checks(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["00-base OK", "check-vault OK: 5 files, 0 design records",
                                          "scripts/check.sh: no checks defined yet"]  # fmt: skip


def test_never_asks_base_questions() -> None:
    """One answer, one place: base's identity is recorded from _external_data as base_answers (decision 0001)."""
    config = yaml.safe_load((ROOT / "copier.yml").read_text())
    asked = {k for k, v in config.items()
             if not k.startswith("_") and v.get("when") is not False and v.get("ask") is not False}
    assert asked == {"vault_dir", "brain_pull"}
    assert config["_external_data"] == {"base": ".copier-answers.base.yml"}
    assert config["_answers_file"] == ".copier-answers.stack-obsidian.yml"


def test_answers_files(project: Path) -> None:
    stack = yaml.safe_load((project / ".copier-answers.stack-obsidian.yml").read_text())
    base_answers = {k: v for k, v in yaml.safe_load((project / ".copier-answers.base.yml").read_text()).items()
                    if k not in ("_commit", "_src_path")}
    assert {k: v for k, v in stack.items() if not k.startswith("_")} == {**BRAIN, "base_answers": base_answers}
    assert (project / ".copier-answers.base.yml").is_file() and not (project / ".copier-answers.yml").exists()


def test_reads_base_answers(project: Path) -> None:
    assert (project / "README.md").read_text().startswith("# demo\n\nA demo brain\n")
    assert "Released into the public domain" in (project / "README.md").read_text()


@pytest.mark.parametrize(("base", "error"), [
    (None, "needs template-base first: .copier-answers.base.yml is missing"),
    ("v1.0.0", "needs template-base v2.0.0 or later; this project has v1.0.0"),
])  # fmt: skip
def test_needs_base_first(base: str | None, error: str, obsidian_src: Path, base_src: Path, tmp_path: Path) -> None:
    """Base goes first, at the version the overlay needs; otherwise the copy fails and says why."""
    dst = tmp_path / "p"
    if base:
        copy(stage(base_src, tmp_path / "old-base", tag=base), dst, BASE)
    with pytest.raises(Exception, match=re.escape(error)):
        copy(obsidian_src, dst, BRAIN)


def test_fills_every_slot_and_prefixes_its_files(project: Path) -> None:
    for slot in [".github/workflows/stack-ci.yml", ".agents/stack.md", ".gitignore", ".pre-commit-config.yaml",
                 ".claude/settings.json", "README.md", ".github/dependabot.yml"]:  # fmt: skip
        assert (project / slot).is_file(), slot
    workflows = {p.name for p in (project / ".github/workflows").glob("*.yml")}
    assert workflows == {"base-ci.yml", "template-update.yml", "pr-title.yml", "stack-ci.yml", "obsidian-brain-pull.yml"}
    assert sorted(p.name for p in (project / "scripts/checks.d").glob("*")) == ["00-base.sh", "20-obsidian.sh"]


def test_agent_permissions(project: Path) -> None:
    """Agents may run every gh command except releases, repo delete and repo archive (decision 0001)."""
    permissions = json.loads((project / ".claude/settings.json").read_text())["permissions"]
    assert "Bash(gh:*)" in permissions["allow"]
    for deny in ["Bash(gh release:*)", "Bash(gh api *releases*)", "Bash(gh repo delete:*)",
                 "Bash(gh repo archive:*)", "Bash(git tag:*)", "Edit(.copier-answers.*.yml)"]:  # fmt: skip
        assert deny in permissions["deny"], deny
    assert not [e for e in permissions["deny"] if "pr merge" in e or "repo edit" in e]


def test_no_unrendered_jinja(project: Path) -> None:
    leftovers = []
    for path in project.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        # Obsidian's own [[wikilinks]] are notes' syntax, not Jinja's.
        if re.search(r"\[%|\.jinja$", path.name) or re.search(r"\[\[ |\[% ", path.read_text(errors="ignore")):
            leftovers.append(str(path))
    assert not leftovers


BRAIN_DROPS = ["CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "TODO.md", "version.txt", "contrib", "docs",
               "release-please-config.json", ".release-please-manifest.json", ".markdownlint-cli2.yaml",
               "scripts/check-wiki.py", ".github/workflows/release-please.yml", ".github/workflows/wiki.yml",
               ".github/ISSUE_TEMPLATE/bug_report.yml", "Dockerfile"]  # fmt: skip


def test_brain_keeps_guard_rails_only(project: Path) -> None:
    """No releases, wiki, image or markdownlint: they are simply absent, never excluded."""
    assert [p for p in BRAIN_DROPS if (project / p).exists()] == []
    files = [p for p in project.rglob("*") if p.is_file() and ".git" not in p.parts]
    files = [p for p in files if str(p.relative_to(project)) not in PULL_FILES]
    text = "\n".join(p.read_text(errors="ignore") for p in files)
    assert not re.search(r"check-wiki|release-please|docs/wiki|docs/design|markdownlint", text)
    assert "**/.obsidian/workspace*.json" in (project / ".gitignore").read_text()


def test_stack_md(project: Path) -> None:
    stack = (project / ".agents/stack.md").read_text()
    assert "`knowledge/🏠 Home.md`" in stack and "`knowledge/.obsidian/`, `knowledge/.trash/`" in stack
    assert "uv run scripts/check-vault.py" in stack


VAULT_OWNERS = {
    "README.md": True,
    "scripts/check.sh": True,
    "knowledge/🏠 Home.md": True,
    "knowledge/📐 Conventions.md": True,
    "knowledge/.obsidian/app.json": True,
    "knowledge/.obsidian/templates.json": True,
    "knowledge/🛰️ Subscriptions.md": True,
    "knowledge/decisions/Decisions.base": False,
    "knowledge/_templates/📝 Design Record.md": False,
    ".agents/stack.md": False,
}


def test_ownership(base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    """copier update leaves a brain's README.md, own checks and seeded notes alone, and still
    updates the design index, the record template and the slots."""
    dst = render(base_src, obsidian_src, tmp_path / "p")
    for name in VAULT_OWNERS:
        (dst / name).write_text("mine\n")
    copy(obsidian_src, dst, BRAIN, overwrite=True)
    assert {n: (dst / n).read_text() == "mine\n" for n in VAULT_OWNERS} == VAULT_OWNERS


def test_vault_at_the_root(base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    dst = render(base_src, obsidian_src, tmp_path / "demo", vault_dir=".")
    for name in ["🏠 Home.md", "decisions/Decisions.base", ".obsidian/app.json", "_attachments/.gitkeep"]:
        assert (dst / name).is_file(), name
    assert not (dst / "knowledge").exists()
    stack = (dst / ".agents/stack.md").read_text()
    assert "`.obsidian/`, `.trash/`, `_attachments/`" in stack and "`🏠 Home.md`" in stack
    (dst / ".obsidian/workspace.json").write_text("{}")
    (dst / ".trash").mkdir()
    (dst / ".trash/old.md").write_text("old")
    ignored = sh("git", "check-ignore", ".obsidian/workspace.json", ".trash/old.md", cwd=dst)
    assert ignored.split() == [".obsidian/workspace.json", ".trash/old.md"]
    result = checks(dst)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("bad", ["notes/vault", "..", "../notes", "", ".obsidian", "a/"])
def test_vault_dir_rejected(bad: str, base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    dst = tmp_path / "p"
    copy(base_src, dst, BASE)
    with pytest.raises(ValueError, match="vault_dir"):
        copy(obsidian_src, dst, {**BRAIN, "vault_dir": bad})


RECORD = """---
kind: decision
number: {number}
status: {status}
date: 2026-11-01
authors: [A. Maintainer]
summary: A decision
supersedes: {supersedes}
superseded_by: {superseded_by}
tags: [decision]
---

## 🧭 Context

## ✅ Decision

## ⚖️ Alternatives considered

## 🌊 Consequences

## ❓ Open questions
"""
OLD = RECORD.format(number=1, status="superseded", supersedes="[]",
                    superseded_by='"[[📝 0002 Follow Upstream]]"')  # fmt: skip
NEW = RECORD.format(number=2, status="approved", supersedes='["[[📝 0001 Keep Notes Here]]"]',
                    superseded_by="")  # fmt: skip
VAULT_CASES = {
    "valid": ({}, ""),
    "broken embed": ({"🧭 Topic.md": "See [[🧭 Not Yet]].\n\n![[missing.png]]\n"}, "embeds a missing file"),
    "bad front matter": ({"🧭 Topic.md": "---\ntags: [a\n---\n"}, "not valid YAML"),
    "bad status": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("approved", "done")}, "status 'done'"),
    "duplicate number": ({"decisions/📝 0002 Also Two.md": NEW}, "number 2 is also"),
    "missing heading": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("## ⚖️ Alternatives considered", "")},
                        "missing headings: Alternatives considered"),
    "one-sided supersedes": ({"decisions/📝 0001 Keep Notes Here.md": OLD.replace("superseded_by: \"[[📝 0002 Follow Upstream]]\"", "superseded_by:")},
                             "doesn't link back"),
}  # fmt: skip


@pytest.mark.parametrize("case", VAULT_CASES)
def test_vault_check(case: str, project: Path, tmp_path: Path) -> None:
    """The vault check (through scripts/checks.sh) fails on what is always broken."""
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    vault = copy_ / "knowledge"
    notes = {"decisions/📝 0001 Keep Notes Here.md": OLD, "decisions/📝 0002 Follow Upstream.md": NEW,
             "🧭 Topic.md": "---\ntags: [topic]\n---\nSee [[🧭 Not Yet]] and ![[🏠 Home]].\n"}  # fmt: skip
    files, error = VAULT_CASES[case]
    for name, text in {**notes, **files}.items():
        (vault / name).write_text(text, encoding="utf-8")
    result = subprocess.run(["uv", "run", "-q", "scripts/check-vault.py"], cwd=copy_, capture_output=True, text=True)
    if not error:
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout == "check-vault OK: 8 files, 2 design records\n"
        assert checks(copy_).returncode == 0
    else:
        assert result.returncode == 1 and error in result.stdout, result.stdout + result.stderr
        assert checks(copy_).returncode != 0


def test_brain_pull_is_opt_in(base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    dst = render(base_src, obsidian_src, tmp_path / "p", brain_pull=False)
    assert [f for f in PULL_FILES if (dst / f).exists()] == []
    assert checks(dst).returncode == 0


def test_brain_pull_workflow(project: Path) -> None:
    """Claude runs read-only; only propose writes, after checking the patch's scope."""
    flow = yaml.safe_load((project / PULL).read_text())
    jobs = flow["jobs"]
    assert flow["permissions"] == {} and set(jobs) == {"update", "propose"}
    assert jobs["update"]["permissions"] == {"contents": "read", "pull-requests": "read", "actions": "read"}
    steps = {s.get("name") or s["uses"].split("@")[0]: s for s in jobs["update"]["steps"]}
    gate = steps["Which followed sources changed?"]
    assert "--workflow obsidian-brain-pull.yml --branch main --status success" in gate["run"]
    assert 'scripts/brain-pull-gate.py "$since" brain-pull-out/changes.md' in gate["run"]
    claude = steps["Claude Code updates the notes"]
    assert "`knowledge/🛰️ Subscriptions.md`" in claude["with"]["prompt"]
    assert "Edit(./knowledge/**/*.md)" in claude["with"]["claude_args"]
    run = "\n".join(s.get("run", "") for s in jobs["propose"]["steps"])
    for needed in ["uv run scripts/check-vault.py", "gh workflow run base-ci.yml", "--label brain-pull"]:
        assert needed in run, needed


def propose_steps(project: Path) -> dict[str, dict]:
    flow = yaml.safe_load((project / PULL).read_text())
    return {s.get("id") or s.get("name") or s["uses"].split("@")[0]: s for s in flow["jobs"]["propose"]["steps"]}


def test_brain_pull_token(project: Path) -> None:
    """Scout's token when SCOUT_APP_CLIENT_ID is set, else GITHUB_TOKEN, for the push, PR, issues and dispatch."""
    steps = propose_steps(project)
    scout = steps["scout"]
    assert scout["if"] == "vars.SCOUT_APP_CLIENT_ID != ''"
    assert scout["uses"].startswith("actions/create-github-app-token@")
    assert scout["with"]["client-id"] == "${{ vars.SCOUT_APP_CLIENT_ID }}"
    assert scout["with"]["private-key"] == "${{ secrets.SCOUT_APP_PRIVATE_KEY }}"
    for perm in ["contents", "pull-requests", "issues", "actions"]:
        assert scout["with"][f"permission-{perm}"] == "write", perm
    token = "${{ steps.scout.outputs.token || github.token }}"
    assert steps["actions/checkout"]["with"]["token"] == token  # the push uses checkout's credentials
    names = list(steps)
    assert names.index("scout") < names.index("actions/checkout")
    env = steps["Commit, push and open the PR"]["env"]
    assert env["GH_TOKEN"] == token  # the PR, the issues and the dispatch
    assert env["DISPATCH_CI"] == "${{ steps.scout.outputs.token == '' }}"


@pytest.mark.parametrize(("dispatch", "dispatched"), [("true", True), ("false", False)], ids=["github-token", "scout"])
def test_brain_pull_dispatches_ci_only_without_scout(dispatch: str, dispatched: bool, project: Path, tmp_path: Path) -> None:
    step = propose_steps(project)["Commit, push and open the PR"]
    bin_, out = tmp_path / "bin", tmp_path / "out"
    bin_.mkdir()
    out.mkdir()
    log = tmp_path / "calls"
    for tool in ["gh", "git", "uv"]:
        (bin_ / tool).write_text(f'#!/bin/sh\necho "{tool} $*" >> "{log}"\n')
        (bin_ / tool).chmod(0o755)
    (out / "vault.patch").write_text("x\n")
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "OUT": str(out), "BRANCH": "brain-pull/2026-11-02",
           "REUSE": "false", "REPO": "o/r", "GH_TOKEN": "t", "DISPATCH_CI": dispatch}  # fmt: skip
    result = subprocess.run(["bash", "-c", step["run"]], cwd=tmp_path, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text()
    assert "git push -q -u origin brain-pull/2026-11-02" in calls and "gh pr create" in calls
    assert ("gh workflow run base-ci.yml" in calls) is dispatched


def scope_check(project: Path, out: Path, prefix: str) -> subprocess.CompletedProcess[str]:
    flow = yaml.safe_load((project / PULL).read_text())
    step = next(s for s in flow["jobs"]["propose"]["steps"] if s.get("name") == "The patch only edits notes")
    assert step["env"]["PREFIX"] == prefix
    return subprocess.run(["bash", "-c", step["run"]], cwd=project, capture_output=True, text=True,
                          env={**os.environ, "OUT": str(out), "PREFIX": prefix})  # fmt: skip


def patch_for(project: Path, out: Path, edits: dict[str, str]) -> None:
    for name, text in edits.items():
        path = project / name
        new = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if new:
            sh("git", "add", "-N", name, cwd=project)
    out.mkdir(exist_ok=True)
    (out / "vault.patch").write_text(sh("git", "diff", "--binary", cwd=project))


OUTSIDE = "outside the vault's notes"
SCOPE_CASES = {
    "a note": ({"knowledge/🏠 Home.md": "edited\n"}, ""),
    "two notes": ({"knowledge/🏠 Home.md": "x\n", "knowledge/📐 Conventions.md": "y\n"}, ""),
    "obsidian settings": ({"knowledge/.obsidian/app.json": "{}\n"}, OUTSIDE),
    "the design index": ({"knowledge/decisions/Decisions.base": "x\n"}, OUTSIDE),
    "the record template": ({"knowledge/_templates/📝 Design Record.md": "x\n"}, OUTSIDE),
    "outside the vault": ({"README.md": "x\n"}, OUTSIDE),
    "the stack file": ({".agents/stack.md": "x\n"}, OUTSIDE),
    "a workflow": ({".github/workflows/base-ci.yml": "x\n"}, OUTSIDE),
    "a new note": ({"knowledge/🧭 New.md": "x\n"}, "adds, removes or renames"),
    "the subscriptions": ({"knowledge/🛰️ Subscriptions.md": "x\n"}, OUTSIDE),
}  # fmt: skip


@pytest.mark.parametrize("case", SCOPE_CASES)
def test_brain_pull_scope(case: str, project: Path, tmp_path: Path) -> None:
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    edits, error = SCOPE_CASES[case]
    patch_for(copy_, tmp_path / "out", edits)
    result = scope_check(copy_, tmp_path / "out", "knowledge/")
    if error:
        assert result.returncode == 1 and error in result.stdout, result.stdout + result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr


FOLLOWED = {
    "🧭 Inline.md": '---\nrepos: [a/one, "b/two"]\n---\n',
    "sub/🧭 Block.md": "---\nrepos:\n  - c/three\n  - not a repo\n---\n",
    "🧭 One.md": "---\nrepos: a/one\n---\n",
    "_templates/🧭 Skipped.md": "---\nrepos: [z/skipped]\n---\n",
    "🧭 None.md": "No front matter.\n",
}
SUBSCRIBED = """---
kind: subscriptions
subscriptions:
  - source: a/one
    follow: [releases]
  - source: d/four
    follow: ["wiki:Security", design-records]
---
"""


def gate(project: Path, tmp_path: Path, notes: dict[str, str], *args: str,
         env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:  # fmt: skip
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    for name, text in notes.items():
        (copy_ / "knowledge" / name).parent.mkdir(parents=True, exist_ok=True)
        (copy_ / "knowledge" / name).write_text(text, encoding="utf-8")
    return subprocess.run(["uv", "run", "-q", GATE, *args], cwd=copy_, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})  # fmt: skip


def test_gate_follows(project: Path, tmp_path: Path) -> None:
    assert gate(project, tmp_path / "empty", {}, "--list").stdout == ""
    result = gate(project, tmp_path / "both", {**FOLLOWED, "🛰️ Subscriptions.md": SUBSCRIBED}, "--list")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "a/one: releases\nb/two: everything\nc/three: everything\n" \
                            "d/four: wiki:Security, design-records\n"  # fmt: skip
    assert "repos entry 'not a repo' is not owner/name" in result.stderr


BAD_SUBSCRIPTIONS = {
    "not a list": ("subscriptions: {a/one: everything}", "must be a list"),
    "bad source": ("subscriptions:\n  - source: one\n    follow: [everything]", "must be owner/name"),
    "unknown part": ("subscriptions:\n  - {source: a/one, follow: [wiki]}", "unknown part 'wiki'"),
}  # fmt: skip


@pytest.mark.parametrize("case", BAD_SUBSCRIPTIONS)
def test_gate_rejects_bad_subscriptions(case: str, project: Path, tmp_path: Path) -> None:
    props, error = BAD_SUBSCRIPTIONS[case]
    result = gate(project, tmp_path, {"🛰️ Subscriptions.md": f"---\n{props}\n---\n"}, "--list")
    assert result.returncode == 2 and error in result.stderr, result.stdout + result.stderr


def test_actions_are_pinned(project: Path) -> None:
    uses = [line.strip() for f in (project / ".github/workflows").glob("*.yml")
            for line in f.read_text().splitlines() if re.match(r"\s*(- )?uses: ", line)]  # fmt: skip
    pin = re.compile(r"^(- )?uses: (\./\S+|[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d\S*)$")
    assert uses and [u for u in uses if not pin.match(u)] == []


def test_workflows_lint(project: Path) -> None:
    if shutil.which("actionlint"):
        sh("actionlint", cwd=project)
    elif shutil.which("docker"):
        sh("docker", "run", "--rm", "-v", f"{project}:/repo", "-w", "/repo", "rhysd/actionlint:1.7.12", cwd=project)
    else:
        pytest.skip("neither actionlint nor docker available")


@pytest.mark.docker
def test_docs_secrets(project: Path) -> None:
    assert sh("scripts/check-docs-secrets.sh", cwd=project).splitlines() == ["check-docs-secrets OK: gitleaks"]


def test_checks_are_quiet_when_they_pass(project: Path) -> None:
    sh("uv", "run", "scripts/check-vault.py", cwd=project)  # uv's first run reports installing PyYAML
    env = {**os.environ, "GITHUB_ACTIONS": ""}
    out = subprocess.run(["uv", "run", "-q", "scripts/check-vault.py"], cwd=project, capture_output=True, text=True, env=env)
    assert (out.stdout + out.stderr).splitlines() == ["check-vault OK: 5 files, 0 design records"]


def test_drop_in_runs_vault_then_project_checks(project: Path, tmp_path: Path) -> None:
    dst = tmp_path / "p"
    shutil.copytree(project, dst)
    (dst / "scripts/check.sh").write_text("#!/bin/sh\necho own check failed\nexit 1\n")
    result = checks(commit(dst))
    assert result.returncode != 0 and "own check failed" in result.stdout
