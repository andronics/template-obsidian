# 0001: The obsidian stack overlay

Status: Approved
Date: 2026-11-01
Authors: Stephen Cox; drafted by Claude (Claude Code)

## Context

project-template made a brain with `language: obsidian` (kind `brain`), through `layers/obsidian/` and core
files gated on it (its design records 0015, 0016, 0018 and 0019). template-base's decision 0001 (from the idea
note **🥞 Stacked Copier Templates**) splits that template into a base and one stack overlay per project.
This repository is the overlay for brains. It is new, built from project-template `v0.1.23`'s files, with no
history. The old records are not imported; this record rebuilds what still applies.

## Decision

- **A brain is base + this overlay.** It asks only `vault_dir` (default `knowledge`, `.` for the root; one
  folder name) and `brain_pull` (default off). It reads `project_name`, `description`, `github_owner`,
  `license` and `copyright_holder` from `.copier-answers.base.yml`, writes
  `.copier-answers.stack-obsidian.yml`, and fails unless base is `v1.0.0` or later.
- **The vault is the wiki; design records are notes.** Records are `📝 NNNN Title.md` in
  `[vault_dir]/decisions/`, from `_templates/📝 Design Record.md`, indexed by `Decisions.base`. They have the
  properties `kind, number, status, date, authors, summary, supersedes, superseded_by, tags`, the five headings,
  and supersedes links that point both ways (was 0016).
- **Checks:** `scripts/checks.d/20-obsidian.sh` runs `scripts/check-vault.py` (front matter, embeds, design
  records) and then the brain's own `scripts/check.sh`. Base's `scripts/checks.sh` runs it, so CI's `checks`
  job and pre-commit run it too. The AI files' context budget left `check-vault.py` for base's contract check,
  which also counts `.agents/stack.md`.
- **Slots it fills:** `.agents/stack.md` (the intro, Don't read, the map rows and the conventions that used to
  be in AGENTS.md); `stack-ci.yml` (one empty job: everything runs in `checks.d`); `.gitignore` (Obsidian's
  per-client state, base's required entries, `private/`); `.pre-commit-config.yaml` (`scripts/checks.sh`,
  gitleaks); `.claude/settings.json` (base's permissions, plus the vault check and a `.trash/` read deny);
  `README.md`; `.github/dependabot.yml` (GitHub Actions only); `.github/pull_request_template.md` and
  `.github/ISSUE_TEMPLATE/config.yml` (base's former generic versions: a brain has no code checklist or
  Documentation link).
- **Owned by the brain once written** (`_skip_if_exists`): `README.md`, `scripts/check.sh`, `🏠 Home`,
  `📐 Conventions`, `_attachments/`, `.obsidian/app.json` and `templates.json`, and `🛰️ Subscriptions`.
  The design index and the record template keep receiving updates.
- **Brain pull** (was 0018, 0019), with `brain_pull`. `obsidian-brain-pull.yml` runs daily. It finds what
  changed since the last successful run on `main` in the sources the vault follows: the `🛰️ Subscriptions`
  note, plus notes' `repos:` as an implicit `everything`. Claude Code then updates those notes with a
  read-only token. A separate job checks that the patch only edits existing notes in the vault, and opens
  one PR labelled `brain-pull`, then dispatches `base-ci.yml` on it. It does nothing without the
  `CLAUDE_CODE_OAUTH_TOKEN` secret.

## Alternatives considered

- **Keep `kind: brain` as a value:** with a stack overlay, a brain is the overlay itself; `kind` stays in the
  code overlays (template-base decision 0001). *Rejected.*
- **A separate `obsidian-ci.yml` with the vault job:** a required check would then depend on the stack.
  *Rejected* for the drop-in that runs inside base's `ci`.

## Consequences

- Migrating a brain renames `brain-pull.yml` to `obsidian-brain-pull.yml`. The first run after the rename
  looks back one day, so dispatch it with `since` if more time has passed.
- `20-obsidian.sh` needs `uv`. Base's CI job installs it, and pre-commit needs it locally, as before.

## Open questions

None.
