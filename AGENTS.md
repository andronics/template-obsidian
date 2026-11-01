# AGENTS.md: working on template-obsidian

This repository is a [Copier](https://copier.readthedocs.io/) **stack overlay**: it is applied on top of
[template-base](https://github.com/andronics/template-base) and makes the project a brain, an Obsidian vault.
These instructions are for changing **the overlay**. What projects get is `template/.agents/stack.md.jinja`
plus base's `AGENTS.md`. Why: `docs/decisions/0001-obsidian-overlay.md` and template-base's decision 0001.

## Layout

| Path | What |
|---|---|
| `copier.yml` | `vault_dir`, `brain_pull`; base's answers through `_external_data`; the base version check |
| `template/` | Rendered into the project, over base: the slots, `obsidian-*` workflows, `scripts/checks.d/20-obsidian.sh`, the vault seeds |
| `tests/` | Renders base (`../template-base` or `$TEMPLATE_BASE`) then this overlay, and checks the brain |
| `docs/decisions/` | Design records; `README.md` is the index |

## The rules of the stack

- **Never ask base's questions.** Read them from `_external_data.base`.
- **Fill every slot base defines**, with every entry base requires (`scripts/checks.d/00-base.sh` checks them).
- **Own files by name:** workflows `obsidian-*`, drop-ins `NN-obsidian*.sh`, each marked `Template-owned: template-obsidian`.
- Never write a file base owns. A change base needs goes to template-base as an issue.

## Jinja

As template-base: `[[ ]]`, `[% %]`, `[#! !#]`. Vault notes are copied verbatim (no `.jinja`): their `[[links]]` are Obsidian's.

## Rules

- Keep the brain green: `uv run pytest`. Pin actions to SHAs. Never credit an AI. Never create tags or releases.
- A vault seed is `_skip_if_exists`: changing it reaches new brains only.
- Asking the user something? Give your recommendation and why. Reply tersely.

## Definition of done

```sh
uv run pytest -m ''
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
```
