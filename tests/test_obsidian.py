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


# Outside the Basic Multilingual Plane (💡), CJK, a quote and a backslash: `tojson` wrote the emoji
# as a surrogate pair, which YAML reads back as two characters.
UNICODE = 'Ideas 💡 in 漢字, with a "quote" and a back\\slash'


def test_unicode_description(base_src: Path, obsidian_src: Path, tmp_path: Path) -> None:
    """Any Unicode in base's description renders: the recorded base answers match base's file (no
    "stale" error), and the brain passes its checks."""
    project = render(base_src, obsidian_src, tmp_path / "demo", base={"description": UNICODE})
    recorded = yaml.safe_load((project / ".copier-answers.stack-obsidian.yml").read_text())["base_answers"]
    assert recorded["description"] == UNICODE
    assert (project / "README.md").read_text().startswith(f"# demo\n\n{UNICODE}\n")
    result = checks(project)
    assert result.returncode == 0, result.stdout + result.stderr


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
    ignored = (project / ".gitignore").read_text().splitlines()
    assert {"**/.obsidian/workspace*.json", "__pycache__/", "*.pyc"} <= set(ignored)


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


def test_pr_template_names_no_ai(project: Path) -> None:
    """Commits, PRs and docs never credit an AI (AGENTS.md): the PR template asks if it was generated, not by what."""
    text = (project / ".github/pull_request_template.md").read_text()
    assert "- [ ] Generated: most of this was written by an AI assistant\n" in text
    assert "tool and model" not in text


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
# Partial supersession (decision 0002): 0004 replaces a part of 0003, which stands otherwise.
PART_OLD = RECORD.format(number=3, status="implemented", supersedes="[]", superseded_by="").replace(
    "superseded_by: \n", 'superseded_by: \npartially_superseded_by: ["[[📝 0004 Change One Point]]"]\n')
PART_NEW = RECORD.format(number=4, status="approved", supersedes="[]", superseded_by="").replace(
    "supersedes: []\n", 'supersedes: []\npartially_supersedes: ["[[📝 0003 Many Points]]"]\n')
ACTOR = "---\nkind: actor\nstatus: {status}\n{links}tags: [actors]\n---\n\n*An actor.*\n"
SPLIT = ACTOR.format(status="deleted", links='partially_superseded_by: ["[[🔔 Herald]]", "[[📯 Crier]]"]\n')
HERALD = ACTOR.format(status="active", links='partially_supersedes: ["[[🎺 Old Bot]]"]\n')
CRIER = ACTOR.format(status="installed", links='partially_supersedes: ["[[🎺 Old Bot]]"]\n')
P3, P4 = "decisions/📝 0003 Many Points.md", "decisions/📝 0004 Change One Point.md"
VAULT_CASES = {
    "valid": ({}, ""),
    "broken embed": ({"🧭 Topic.md": "See [[🧭 Not Yet]].\n\n![[missing.png]]\n"}, "embeds a missing file"),
    "bad front matter": ({"🧭 Topic.md": "---\ntags: [a\n---\n"}, "error: 🧭 Topic.md: front matter is not valid YAML (line 2, column 9)\n"),
    "bad status": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("approved", "done")},
                   "status is not one of approved, implemented, proposed, rejected, superseded"),
    "bad kind": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("kind: decision", "kind: note")}, "kind must be 'decision'"),
    "number not a whole number": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("number: 2", "number: two")},
                                  "number is a string, not a whole number"),
    "superseded_by not a link": ({"decisions/📝 0001 Keep Notes Here.md": OLD.replace('"[[📝 0002 Follow Upstream]]"', "later")},
                                 "superseded_by is not a link to a design record"),
    "duplicate number": ({"decisions/📝 0002 Also Two.md": NEW}, "number 2 is also"),
    "missing heading": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("## ⚖️ Alternatives considered", "")},
                        "missing headings: Alternatives considered"),
    "one-sided supersedes": ({"decisions/📝 0001 Keep Notes Here.md": OLD.replace("superseded_by: \"[[📝 0002 Follow Upstream]]\"", "superseded_by:")},
                             "doesn't link back"),
    "superseded_by needs superseded": ({"decisions/📝 0001 Keep Notes Here.md": OLD.replace("status: superseded", "status: approved")},
                                       "superseded_by is set, so status must be 'superseded'"),
    "one-sided partial": ({P3: PART_OLD.replace('partially_superseded_by: ["[[📝 0004 Change One Point]]"]\n', "")},
                          "partially_supersedes 📝 0003 Many Points, whose partially_superseded_by doesn't link back"),
    "partial to a non-record": ({P4: PART_NEW.replace("📝 0003 Many Points", "🧭 Topic")},
                                "partially_supersedes item 1 is not a link to a design record"),
    "partial to itself": ({P4: PART_NEW.replace("📝 0003 Many Points", "📝 0004 Change One Point")},
                          "partially_supersedes names the note itself"),
    "wholly and partially": ({P4: PART_NEW.replace("supersedes: []", 'supersedes: ["[[📝 0003 Many Points]]"]'),
                              P3: PART_OLD.replace("status: implemented", "status: superseded").replace(
                                  "superseded_by: \n", 'superseded_by: "[[📝 0004 Change One Point]]"\n')},
                             "📝 0003 Many Points is named as both wholly and partially superseded"),
    "actor whole successor": ({"actors/🎺 Old Bot.md": ACTOR.format(status="superseded", links='superseded_by: "[[🔔 Herald]]"\n'),
                               "actors/🔔 Herald.md": ACTOR.format(status="active", links='supersedes: ["[[🎺 Old Bot]]"]\n'),
                               "actors/📯 Crier.md": ACTOR.format(status="retired", links="")}, ""),
    "actor bad status": ({"actors/📯 Crier.md": ACTOR.format(status="gone", links='partially_supersedes: ["[[🎺 Old Bot]]"]\n')},
                         "status is not one of active, created, deleted, installed, planned, retired, superseded"),
    "actor without status": ({"actors/📯 Crier.md": CRIER.replace("status: installed\n", "")},
                             "status is missing; it must be one of active, created, deleted, installed, planned, retired, superseded"),
    "actor superseded alone": ({"actors/🎺 Old Bot.md": ACTOR.format(status="superseded", links="")},
                               "status is 'superseded', so superseded_by (or, for a split, partially_superseded_by)"),
    "actor still active": ({"actors/🎺 Old Bot.md": ACTOR.format(status="active", links='superseded_by: "[[🔔 Herald]]"\n'),
                            "actors/🔔 Herald.md": ACTOR.format(status="active", links='supersedes: ["[[🎺 Old Bot]]"]\n')},
                           "superseded_by is set, so status must be 'superseded' or 'deleted'"),
    "actor one-sided": ({"actors/📯 Crier.md": CRIER.replace("partially_supersedes", "supersedes")},
                        "partially_superseded_by 📯 Crier, whose partially_supersedes doesn't link back"),
    "actor to a record": ({"actors/🔔 Herald.md": ACTOR.format(status="active", links='supersedes: ["[[📝 0001 Keep Notes Here]]"]\n')},
                          "supersedes item 1 is not a link to an actor note"),
    "actor template skipped": ({"_templates/🎭 Actor.md": ACTOR.format(status="", links="superseded_by: x\n")}, ""),
    # Records take `created` in place of `date`, or both (decision 0003).
    "record with created": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("date:", "created:")}, ""),
    "record with both": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("date: 2026-11-01\n", "date: 2026-11-01\ncreated: 2026-11-02\napproved: 2026-11-03\napproved_by: A. Maintainer\n")}, ""),
    "record with neither": ({"decisions/📝 0002 Follow Upstream.md": NEW.replace("date: 2026-11-01\n", "")},
                            "missing properties: date or created"),
}  # fmt: skip
NOTES = {"decisions/📝 0001 Keep Notes Here.md": OLD, "decisions/📝 0002 Follow Upstream.md": NEW,
         P3: PART_OLD, P4: PART_NEW, "actors/🎺 Old Bot.md": SPLIT, "actors/🔔 Herald.md": HERALD,
         "actors/📯 Crier.md": CRIER, "🧭 Topic.md": "---\ntags: [topic]\n---\nSee [[🧭 Not Yet]] and ![[🏠 Home]].\n"}  # fmt: skip


def run_vault_check(project: Path, tmp_path: Path, files: dict[str, str]) -> tuple[Path, subprocess.CompletedProcess[str]]:
    """check-vault.py on a copy of the render, with the test notes and `files` (vault paths) added."""
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    vault = copy_ / "knowledge"
    for name, text in {**NOTES, **files}.items():
        (vault / name).parent.mkdir(parents=True, exist_ok=True)
        (vault / name).write_text(text, encoding="utf-8")
    result = subprocess.run(["uv", "run", "-q", "scripts/check-vault.py"], cwd=copy_, capture_output=True, text=True)
    return copy_, result


@pytest.mark.parametrize("case", VAULT_CASES)
def test_vault_check(case: str, project: Path, tmp_path: Path) -> None:
    """The vault check (through scripts/checks.sh) fails on what is always broken."""
    files, error = VAULT_CASES[case]
    copy_, result = run_vault_check(project, tmp_path, files)
    if not error:
        assert result.returncode == 0, result.stdout + result.stderr
        files_ = 13 + sum(1 for name in files if name not in NOTES)
        assert result.stdout == f"check-vault OK: {files_} files, 4 design records, 3 actors\n"
        assert checks(copy_).returncode == 0
    else:
        assert result.returncode == 1 and error in result.stdout, result.stdout + result.stderr
        assert checks(copy_).returncode != 0


# Obsidian's property-type registry (decision 0003): one property per type, a name in another case,
# a type this check doesn't know, and the record properties the template writes.
TYPES = {"types": {"Updated": "date", "seen": "datetime", "count": "number", "done": "checkbox", "related": "multitext",
                   "aliases": "aliases", "tags": "tags", "summary": "text", "odd": "someNewType",
                   "created": "date", "approved": "date", "approved_by": "text", "number": "number"}}
TYPED = ("---\ntags: [topic]\nupdated: 2026-11-01\nseen: 2026-11-01T10:30:00\ncount: 3.5\ndone: false\n"
         "related: ['[[🏠 Home]]', 2]\naliases: [Alt]\nsummary: 12\nodd: [[x]]\nunregistered: [[y]]\n---\nTyped.\n")


def typed(**props: str) -> dict[str, str]:
    """The typed note, with each of `props` replaced or added (`name: value` as written)."""
    text = TYPED
    for name, value in props.items():
        line = re.search(rf"^{name}:.*$", text, re.M)
        text = text.replace(line.group(0), f"{name}: {value}") if line else text.replace("---\nTyped", f"{name}: {value}\n---\nTyped")
    return {"🧭 Typed.md": text}


TYPE_CASES = {
    "valid": (TYPES, typed(), ""),
    "quoted date and datetime": (TYPES, typed(updated='"2026-11-01"', seen='"2026-11-01T10:30"'), ""),
    "datetime as a date or with seconds": (TYPES, {**typed(seen="2026-11-01"), "🧭 Two.md": TYPED.replace("2026-11-01T10:30:00", '"2026-11-01T10:30:15"')}, ""),
    "empty values": (TYPES, typed(updated="", seen="", count="", done="", related="[]", aliases="[]", tags="[]", summary=""), ""),
    "record properties": (TYPES, {"decisions/📝 0002 Follow Upstream.md": NEW.replace("date:", "created:").replace(
        "status: approved\n", "status: approved\napproved: 2026-11-03\napproved_by: A. Maintainer\n")}, ""),
    "no types.json": (None, typed(updated='"1 Nov"', done="yes", tags="topic"), ""),
    "templates folder skipped": (TYPES, {"_templates/🧭 Typed.md": TYPED.replace("done: false", 'done: "{{x}}"')}, ""),
    "bad date": (TYPES, typed(updated='"1 Nov"'), 'error: 🧭 Typed.md: updated is a string, not date'),
    "timestamp for a date": (TYPES, typed(updated="2026-11-01T10:30:00"), "updated is a datetime, not date"),
    "bad datetime": (TYPES, typed(seen='"2026-11-01 10:30"'), "seen is a string, not datetime"),
    "boolean for a number": (TYPES, typed(count="true"), "count is a boolean, not number"),
    "string for a checkbox": (TYPES, typed(done='"yes"'), "done is a string, not checkbox"),
    "one value for a list": (TYPES, typed(related='"[[🏠 Home]]"'), "related is a string, not multitext"),
    "nested list in a list": (TYPES, typed(related="[[[🏠 Home]]]"), "related is a list whose item 1 is a list, not multitext"),
    "number in aliases": (TYPES, typed(aliases="[1]"), "aliases is a list whose item 1 is a number, not aliases"),
    "one tag": (TYPES, typed(tags="topic"), "tags is a string, not tags"),
    "second item bad": (TYPES, typed(related="['[[🏠 Home]]', 2, {a: 1}]"), "related is a list whose item 3 is a mapping, not multitext"),
    "unquoted link for text": (TYPES, typed(summary="[[🏠 Home]]"), "summary is a list, not text"),
    "quoted impossible date": (TYPES, typed(updated="'2026-13-45'"), "error: 🧭 Typed.md: updated is a string, not date"),
    "quoted impossible datetime": (TYPES, typed(seen="'2026-11-04T25:99'"), "error: 🧭 Typed.md: seen is a string, not datetime"),
    "quoted impossible day in a datetime": (TYPES, typed(seen='"2026-02-30T10:30"'), "seen is a string, not datetime"),
    "not JSON": ("{types:", typed(), "error: .obsidian/types.json: not JSON whose types is a mapping"),
    "types not a mapping": ({"types": ["date"]}, typed(), "error: .obsidian/types.json: not JSON whose types is a mapping"),
}  # fmt: skip


@pytest.mark.parametrize("case", TYPE_CASES)
def test_property_types(case: str, project: Path, tmp_path: Path) -> None:
    """With .obsidian/types.json, every note's registered properties hold a value of their type (decision 0003)."""
    types, files, error = TYPE_CASES[case]
    if types is not None:
        files = {**files, ".obsidian/types.json": types if isinstance(types, str) else json.dumps(types)}
    _, result = run_vault_check(project, tmp_path, files)
    if not error:
        assert result.returncode == 0 and result.stdout.startswith("check-vault OK:"), result.stdout + result.stderr
    else:
        assert result.returncode == 1 and error in result.stdout, result.stdout + result.stderr
        assert len(result.stdout.splitlines()) == 1, result.stdout


SECRET = "SECRET-4111111111111111"
# A secret pasted into each property a check reads, and into front matter the parser quotes (decision 0004).
LEAKS = {
    "🧭 Typed.md": typed(updated=SECRET, count=SECRET, done=SECRET, related=f"[ok, [{SECRET}]]", aliases=f"[{SECRET}, 1]",
                         tags=SECRET, summary=f"[{SECRET}]")["🧭 Typed.md"],
    "decisions/📝 0002 Follow Upstream.md": NEW.replace("kind: decision", f"kind: {SECRET}").replace(
        "status: approved", f"status: {SECRET}").replace("number: 2", f"number: {SECRET}").replace(
        'supersedes: ["[[📝 0001 Keep Notes Here]]"]', f"supersedes: [{SECRET}]"),
    "decisions/📝 0001 Keep Notes Here.md": OLD.replace('"[[📝 0002 Follow Upstream]]"', SECRET),
    "actors/📯 Crier.md": CRIER.replace("status: installed", f"status: {SECRET}").replace('"[[🎺 Old Bot]]"', SECRET),
    "actors/🔔 Herald.md": HERALD.replace('partially_supersedes: ["[[🎺 Old Bot]]"]', f"superseded_by: {SECRET}"),
    "🧭 Escape.md": f'---\nnote: "\\q{SECRET}"\n---\n',
    "🧭 Alias.md": f"---\nnote: *{SECRET}\n---\n",
    "🧭 Tag.md": f"---\nnote: !{SECRET} x\n---\n",
    "🧭 Token.md": f"---\nnote: [{SECRET}}}\n---\n",
    "🧭 Indent.md": f"---\nnote: a\n  {SECRET}: b\n---\n",
}


def test_findings_never_print_a_value(project: Path, tmp_path: Path) -> None:
    """A secret in any property, or in broken YAML, is never printed; the note and property are (decision 0004)."""
    files = {**LEAKS, ".obsidian/types.json": json.dumps(TYPES)}
    _, result = run_vault_check(project, tmp_path, files)
    out = result.stdout + result.stderr
    assert result.returncode == 1 and not result.stderr, out
    assert SECRET not in out and "4111" not in out, out
    for name in ["🧭 Typed.md", "📝 0002 Follow Upstream.md", "📝 0001 Keep Notes Here.md", "📯 Crier.md", "🔔 Herald.md",
                 "🧭 Escape.md", "🧭 Alias.md", "🧭 Tag.md", "🧭 Token.md", "🧭 Indent.md"]:
        assert name in out, (name, out)
    for finding in ["updated is a string, not date", "count is a string, not number", "done is a string, not checkbox",
                    "related is a list whose item 2 is a list, not multitext", "aliases is a list whose item 2 is a number, not aliases",
                    "tags is a string, not tags", "summary is a list, not text", "kind must be 'decision'",
                    "status is not one of approved", "number is a string, not a whole number",
                    "supersedes item 1 is not a link to a design record", "superseded_by is not a link to a design record",
                    "partially_supersedes item 1 is not a link to an actor note", "superseded_by is not a link to an actor note",
                    "status is not one of active"]:
        assert finding in out, (finding, out)
    for note in ["Escape", "Alias", "Tag", "Token", "Indent"]:
        assert re.search(rf"error: 🧭 {note}\.md: front matter is not valid YAML \(line [23], column \d+\)$", out, re.M), (note, out)


# Dates YAML or Python can't build, unquoted (YAML raises while loading) and quoted (the type check's regex
# matches the shape only); each value's text must never be printed (decision 0004).
IMPOSSIBLE = {
    "🧭 Leap.md": ("---\ncreated: 2026-02-30\n---\n", "created is not a real date", "2026-02-30"),
    "🧭 Month.md": ("---\ntags: [topic]\nupdated: 2026-13-45\n---\n", "updated is not a real date", "13-45"),
    "🧭 Hour.md": ("---\nseen: 2026-11-04T25:99:00\n---\n", "seen is not a real date", "25:99"),
    "🧭 Listed.md": ("---\nrelated: [ok, 2026-04-31]\n---\n", "related is not a real date", "04-31"),
    "🧭 Quoted.md": ("---\nupdated: '2026-13-46'\n---\n", "updated is a string, not date", "13-46"),
    "🧭 Clock.md": ("---\nseen: '2026-11-04T25:98'\n---\n", "seen is a string, not datetime", "25:98"),
    "🧭 Keyed.md": ("---\n2026-02-31: x\n---\n", "front matter has a date that doesn't exist", "02-31"),
}


def test_impossible_dates_are_findings(project: Path, tmp_path: Path) -> None:
    """An impossible date, quoted or not, is one finding naming the note and property, never the value, and
    the check goes on to the other notes (the typed note's valid dates still pass)."""
    files = {name: text for name, (text, _, _) in IMPOSSIBLE.items()}
    _, result = run_vault_check(project, tmp_path, {**typed(), **files, ".obsidian/types.json": json.dumps(TYPES)})
    out = result.stdout + result.stderr
    assert result.returncode == 1 and not result.stderr and "Traceback" not in out, out
    assert len(result.stdout.splitlines()) == len(IMPOSSIBLE), out
    for name, (_, finding, value) in IMPOSSIBLE.items():
        assert f"error: {name}: {finding}" in result.stdout.splitlines(), (name, out)
        assert value not in out, (value, out)
    assert "Typed" not in out, out


def test_vault_check_without_actors_reads_as_before(project: Path) -> None:
    """A brain with no actor notes gets the same output as before decision 0002."""
    result = subprocess.run(["uv", "run", "-q", "scripts/check-vault.py"], cwd=project, capture_output=True, text=True)
    assert result.stdout == "check-vault OK: 5 files, 0 design records\n", result.stdout + result.stderr


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
    steps = {s.get("id") or s.get("name") or s["uses"].split("@")[0]: s for s in jobs["update"]["steps"]}
    gate = steps["gate"]
    assert "--workflow obsidian-brain-pull.yml --branch main --status success" in gate["run"]
    assert 'scripts/brain-pull-gate.py "$since" brain-pull-out/changes.md' in gate["run"]
    assert '--read "$RUNNER_TEMP/brain-pull-read.md"' in gate["run"]  # out of Claude's reach
    assert steps["package"]["env"]["READ"] == "${{ runner.temp }}/brain-pull-read.md"
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
    (out / "report.md").write_text("**Read**\n\n- `a/one@1111111 → 2222222`\n")
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "OUT": str(out), "BRANCH": "brain-pull/2026-11-02",
           "REUSE": "false", "REPO": "o/r", "GH_TOKEN": "t", "DISPATCH_CI": dispatch}  # fmt: skip
    result = subprocess.run(["bash", "-c", step["run"]], cwd=tmp_path, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text()
    assert "git push -q -u origin brain-pull/2026-11-02" in calls and "gh pr create" in calls
    assert ("gh workflow run base-ci.yml" in calls) is dispatched
    # The PR body: the run's before → after report first, then Claude's lines (here the fallback).
    assert f"--body-file {out}/body.md" in calls
    assert (out / "body.md").read_text() == "**Read**\n\n- `a/one@1111111 → 2222222`\n\n" \
                                            "Notes updated by the Brain pull workflow.\n"  # fmt: skip


def package(project: Path, tmp_path: Path, read: str) -> tuple[subprocess.CompletedProcess[str], str, str]:
    """Run the update job's Package step; return its result, report.md and the job summary."""
    flow = yaml.safe_load((project / PULL).read_text())
    step = next(s for s in flow["jobs"]["update"]["steps"] if s.get("id") == "package")
    (tmp_path / "read.md").write_text(read)
    summary, output = tmp_path / "summary", tmp_path / "output"
    env = {**os.environ, "VAULT_DIR": step["env"]["VAULT_DIR"], "READ": str(tmp_path / "read.md"),
           "GITHUB_STEP_SUMMARY": str(summary), "GITHUB_OUTPUT": str(output)}  # fmt: skip
    result = subprocess.run(["bash", "-c", step["run"]], cwd=project, capture_output=True, text=True, env=env)
    report = project / "brain-pull-out/report.md"
    return result, report.read_text() if report.exists() else "", summary.read_text() if summary.exists() else ""


READ = "- `a/one@0000000 → 1111111`\n- `c/new@none → 3333333`\n"


def test_brain_pull_report_lists_notes_changed(project: Path, tmp_path: Path) -> None:
    """Computed, not written by Claude: what it read, before → after, and each note changed."""
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    for name in ["🏠 Home.md", "📐 Conventions.md"]:
        with (copy_ / "knowledge" / name).open("a", encoding="utf-8") as f:
            f.write("\nedited\n")
    result, report, summary = package(copy_, tmp_path, READ)
    assert result.returncode == 0, result.stdout + result.stderr
    assert report == "**Read**\n\n" + READ + "\n**Vault:** none → 2 notes\n\n" \
                     "- `knowledge/🏠 Home.md`\n- `knowledge/📐 Conventions.md`\n"  # fmt: skip
    assert summary == "\n" + report


def test_brain_pull_report_vault_unchanged(project: Path, tmp_path: Path) -> None:
    copy_ = tmp_path / project.name
    shutil.copytree(project, copy_)
    result, report, _ = package(copy_, tmp_path, "")
    assert result.returncode == 0, result.stdout + result.stderr
    assert report == "**Read**\n\n- nothing listed\n\n**Vault unchanged**\n"


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


FAKE_GH = """#!/usr/bin/env python3
import json, sys
path = sys.argv[-1]
repo = "/".join(path.split("/")[1:3])
if "/releases" in path:
    out = []
elif "per_page=1&until=" in path:
    out = [] if repo == "c/new" else [{"sha": "0" * 40, "commit": {"message": "old"}}]
elif path.endswith("per_page=1"):
    out = [{"sha": {"a/one": "1", "b/two": "2", "c/new": "3"}[repo] * 40, "commit": {"message": "head"}}]
else:  # the window's commits, paginated: b/two changed nothing
    out = [[] if repo == "b/two" else [{"sha": "1" * 40, "commit": {"message": "feat: x"}}]]
print(json.dumps(out))
"""


def test_gate_reads_heads_before_and_after(project: Path, tmp_path: Path) -> None:
    """--read: each changed source's head at SINCE and now; an unchanged one isn't listed."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "gh").write_text(FAKE_GH)
    (bin_ / "gh").chmod(0o755)
    notes = {"🧭 Followed.md": "---\nrepos: [a/one, b/two, c/new]\n---\n"}
    read, out = tmp_path / "read.md", tmp_path / "changes.md"
    result = gate(project, tmp_path / "p", notes, "2026-11-01T05:00:00Z", str(out), "--read", str(read),
                  env={"PATH": f"{bin_}:{os.environ['PATH']}"})  # fmt: skip
    assert result.returncode == 0, result.stderr
    assert result.stdout == "a/one c/new\n"
    assert read.read_text() == "- `a/one@0000000 → 1111111`\n- `c/new@none → 3333333`\n"
    assert "## a/one" in out.read_text() and "## b/two" not in out.read_text()


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
