# template-obsidian

The stack overlay for a **brain**: a repository of notes that is an Obsidian vault. It goes on top of
[template-base](https://github.com/andronics/template-base):

```sh
uvx copier copy --trust gh:andronics/template-base my-brain
uvx copier copy --trust gh:andronics/template-obsidian my-brain
```

It asks two questions, `vault_dir` (the vault's folder, `.` for the root) and `brain_pull`, and reads the
rest from base's answers. It needs template-base `v2.0.0` or later.

## What it adds

| Path | What |
|---|---|
| `[vault_dir]/` | The vault's seeds: `🏠 Home`, `📐 Conventions`, `decisions/` (indexed by `Decisions.base`), `_templates/📝 Design Record`, `.obsidian/{app,templates}.json`, and `🛰️ Subscriptions` with Brain pull. Seeds are the brain's once written |
| `scripts/checks.d/20-obsidian.sh` | Runs `scripts/check-vault.py` (front matter, embeds, design records, actor statuses and supersession, property types), then the brain's own `scripts/check.sh` |
| Slots | `.agents/stack.md`, `stack-ci.yml`, `.gitignore`, `.pre-commit-config.yaml`, `.claude/settings.json`, `README.md`, `.github/dependabot.yml`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/config.yml` |
| `obsidian-brain-pull.yml` | With `brain_pull`: daily, Claude Code updates the notes whose sources changed, in one PR |

## Brain pull setup

Add the `CLAUDE_CODE_OAUTH_TOKEN` secret (`claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN`;
until then the workflow does nothing), and allow Actions to open PRs (Settings → Actions → General → **Allow
GitHub Actions to create and approve pull requests**). `scripts/repo-metadata.py` doesn't set it: it also lets
workflows approve PRs, so turn it on knowingly.

Optionally, let the PR come from Scout, the brain's GitHub App (contents, pull-requests, issues and actions
write): set the `SCOUT_APP_CLIENT_ID` variable and the `SCOUT_APP_PRIVATE_KEY` secret. Its push runs CI on the
PR by itself; without it the workflow pushes with `GITHUB_TOKEN` and dispatches `base-ci.yml` by hand.

## Where this came from

Built from [metalayerlab/project-template](https://github.com/metalayerlab/project-template) `v0.1.23`'s
`layers/obsidian/` and its obsidian-gated files, as a new repository with no history. Its design records 0016,
0018 and 0019 are not imported: [`docs/decisions/0001`](docs/decisions/0001-obsidian-overlay.md) rebuilds them
for the stacked shape. The originals stay in project-template's `docs/design/`.

## License

[Unlicense](LICENSE).
