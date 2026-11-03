# 0003: Property types from types.json, and created on design records

Status: Proposed
Date: 2026-11-03
Authors: Stephen Cox

## Context

The brain's approved record 0012 (*Knowledge Centres Replace Note-Kind Folders*) gives every vault property
one type, registered in `vault/.obsidian/types.json`, Obsidian's own property-type registry, and renames
records' `date` to `created`, with `approved` and `approved_by` for approval by property. Its §9 asks this
template for the three parts that any brain can use; the brain-specific rules stay in the brain.

What the overlay does today (v1.3.1):

- **`template/.agents/stack.md.jinja`** says "`.obsidian/`: never edit beyond `app.json` and
  `templates.json`", so an agent may not write `types.json`.
- **`template/scripts/check-vault.py.jinja`** reads each note's front matter with `yaml.safe_load` (between a
  leading `---` line and the next `\n---`), checks that it is a mapping, and then checks properties only on
  design records (`decisions/` notes: the required names in `PROPERTIES`, which include `date`, plus `kind`,
  `status`, `number`, headings and supersession links) and actor notes (`kind: actor`, outside the templates
  folder read from `.obsidian/templates.json`). It never reads `types.json`, so a value of the wrong type
  (a quoted `updated` in one note and a date in the next, an unquoted wikilink that YAML reads as a nested
  list) passes.
- **`📝 Design Record`** (`template/[[ vault_dir ]]/_templates/`) has `date: "{{date:YYYY-MM-DD}}"` and no
  approval properties. **`Decisions.base`** (`template/[[ vault_dir ]]/decisions/`) shows `note.date` as
  *Date* in both views. Both are template-owned and reach brains on `copier update`; 0001 lists `date` among
  a record's properties.

Obsidian writes `types.json` itself when a property's type is set in the Properties panel, as
`{"types": {"<property>": "<type>"}}`. The type names it writes are `text`, `multitext` (shown as *List*),
`number`, `checkbox`, `date`, `datetime`, and the built-in `aliases` and `tags`.

Constraints: every brain that passes today must still pass, with or without the new file; the change is a
minor release.

## Decision

- **`.agents/stack.md`** allows `.obsidian/types.json` beside `app.json` and `templates.json`:
  "`.obsidian/`: never edit beyond `app.json`, `templates.json` and `types.json`". Its Checks line adds
  "property types". The overlay doesn't seed a `types.json`: a brain's property set is its own.
- **`check-vault.py` checks values against `types.json`**, only when `[[ vault ]].obsidian/types.json`
  exists. It reads the file directly, as it reads `templates.json` (`vault_files` skips dot-folders).
  - A file that is not JSON, or whose `types` is not a mapping of names to strings, is one error.
  - Every note outside the templates folder is checked (template placeholders such as
    `"{{date:YYYY-MM-DD}}"` are not values yet). Each property whose name is registered, matched without
    regard to case as Obsidian matches names, must hold a value of its type, on the value YAML parsed:

    | Type | Valid value |
    |---|---|
    | `text` | one scalar: a string, number, boolean or date, never a list or mapping (catches an unquoted `[[link]]`) |
    | `multitext`, `aliases`, `tags` | a list; each item a scalar, and for `aliases` and `tags` a string |
    | `number` | an integer or decimal, not a boolean |
    | `checkbox` | `true` or `false` |
    | `date` | a YAML date, or a string `YYYY-MM-DD` |
    | `datetime` | a YAML timestamp, or a string `YYYY-MM-DDTHH:MM` with optional seconds; a date alone is accepted too |

  - An empty value (nothing after the colon) and an empty list pass for every type: Obsidian writes both.
  - A property not in `types.json` is not checked, and a type name the check doesn't know is skipped, so a
    newer Obsidian's type can't fail a brain.
  - Quoted and unquoted dates both pass because Obsidian reads both as dates. Requiring one form is a
    brain's own rule.
  - Each finding is `error: <note>: <property> is <value>, not <type>` (the registered type), in the
    existing output; a pass prints the same one line as now.
- **Design records accept `created` in place of `date`.** `PROPERTIES` drops `date`, and the check requires
  at least one of `date` and `created`; both are allowed and not compared. `approved` and `approved_by` are
  optional: the record check doesn't require them, and `types.json`, when present, types them. Nothing
  else about records changes.
- **The `📝 Design Record` template** writes `created: "{{date:YYYY-MM-DD}}"` in place of `date`, and gains
  empty `approved:` (a date) and `approved_by:` (text) after `status`. The placeholder stays quoted: an
  unquoted `{{…}}` is a YAML mapping, and `check-vault.py` parses the template's front matter. The guidance
  comment says to fill `approved` and `approved_by` when the record is approved.
- **`Decisions.base`** shows *Created* from a formula that falls back to `date`, so records written either
  way fill one column:

  ```yaml
  formulas:
    created: 'if(note.created, note.created, note.date)'
  ```

  Both views list `formula.created` where they listed `note.date`, with `displayName: Created`. Filters and
  the sort on `number` are unchanged.
- **Out of scope, kept in the brain:** which properties each kind requires, the allowed `kind` and `status`
  lists beyond records' and actors', the allowed `approved_by` values and the approval rule, the `centre` and
  `owner` rules, and whether dates must be unquoted. The brain's own `scripts/check.sh` runs those (record
  0012's `tools/check-properties.py`).

## Alternatives considered

- **Seed a `types.json`** with the record properties: Obsidian rewrites the file as types are set, so a
  `copier update` would fight the brain, and a `_skip_if_exists` seed reaches new brains only. *Rejected*;
  the check reads whatever the brain registers.
- **Require unquoted dates:** matches how Obsidian's editor writes them, but the record template must quote
  its placeholder, so every record made from it would fail. *Rejected* here; a brain can require it.
- **Replace `date` with `created` outright:** every existing record would fail on update. *Rejected*;
  either is accepted, and a brain renames when it chooses.
- **Two columns in `Decisions.base`, *Date* and *Created*:** half empty in any brain mid-rename.
  *Rejected* for the formula.
- **Fail on a property missing from `types.json`:** that is a brain's policy, and most brains won't
  register every property. *Rejected*.

## Consequences

- Minor and non-breaking (a `feat`, released as 1.4.0). On `copier update`, an existing brain is unaffected:
  - it has no `types.json`, so no type is checked;
  - its records keep `date`, which stays valid, and `Decisions.base` shows it under *Created*;
  - only new records get `created`, `approved` and `approved_by`.

  A brain opts into type checks by letting Obsidian write `types.json`; findings then show values its
  editor would already show as mistyped.
- 0001's list of record properties now reads `date` or `created`, plus the optional `approved` and
  `approved_by`. 0001 stays Approved; this record amends that list.
- The implementing PR changes `check-vault.py.jinja`, the record template, `Decisions.base` and
  `stack.md.jinja`, and adds tests in `tests/test_obsidian.py`: a record with `created`, with both, with
  neither; each type valid and invalid; no `types.json`; a malformed one; an unknown type; the templates
  folder skipped. The brain's 0012 migration can then drop the duplicate `date`, and its
  `check-properties.py` keeps only the brain-specific rules.
- Rollback: revert the release. Records with only `created` then fail the required-properties check, so a
  brain that has renamed adds `date` back.

## Open questions

None for the template. Approval of this record is the brain coordinator's.
