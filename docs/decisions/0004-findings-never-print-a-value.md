# 0004: Findings that never print a value

Status: Approved (2026-11-04)
Date: 2026-11-04
Authors: Stephen Cox

## Context

A brain's vault may hold properties whose value must never be a secret: a property meant to hold only a pass
path (a password-store path such as `services/bank/account`), never the thing it points to. If someone writes
the secret itself into one (an unquoted account number, say), `scripts/check-vault.py` finds the mistake and
then prints the value: on the terminal, in an assistant's context, and in the CI log of every run until it is
fixed. The repo is private but its logs are kept, and a value printed once can't be taken back.

Decision 0003 fixed the type-check finding as `error: <note>: <property> is <value>, not <type>`, and
`tests/test_obsidian.py` (`TYPE_CASES`) pins that text. The type check is not the only one that prints a
value. In `template/scripts/check-vault.py.jinja` (v1.4.0), these findings print a property's value or text
derived from the note's contents:

| Check | Finding today | What it prints |
|---|---|---|
| Property types (`check_types`) | `{name} is {json value}, not {kind}` | the whole value, as JSON |
| Record kind (`check_records`) | `kind is {kind!r}, not 'decision'` | the value of `kind` |
| Record status (`check_records`) | `status {status!r} is not one of …` | the value of `status` |
| Actor status (`check_actors`) | `status {status!r} is not one of …` | the value of `status` (`None` when missing) |
| Record number (`check_records`) | `number {number!r} is not a whole number` | the value of `number` |
| Supersession links (`check_successors`) | `{prop} {value!r}, which is not {what}` | the unresolved link, or whatever the property holds |
| Broken YAML (`main`) | `front matter is not valid YAML: {e}` | the parser's first line, which for some errors quotes the note's text (an unknown escape, an undefined alias or tag, the token it found) |

`kind`, `status` and `number` are rarely secret, but a check can't know which property a brain uses for what,
and the same mistake (a value pasted into the wrong line) can put a secret anywhere. These findings print only
names the template or the brain chose, or a number already checked to be a whole number, and are safe:

- `missing properties: …`, `missing headings: …`, `the name must be '📝 NNNN Title In Title Case'` (the
  number is already validated), `number N is also <note>`;
- `superseded_by is set, so status must be …`, `status is 'superseded', so superseded_by … must name who took
  over`, `<property> names the note itself`, `<property> <note>, whose <partner> doesn't link back`,
  `<note> is named as both wholly and partially superseded` (the link resolved, so what is printed is a note's
  name);
- `.obsidian/types.json: not JSON whose types is a mapping …`, `front matter is not a mapping of properties`;
- the pass line, `check-vault OK: N files, N design records, N actors`.

One finding prints note text that is not a property: `embeds a missing file: {target}`, the target of an
`![[…]]` embed in the body. It is a file name the author typed as a link, and the fix needs it: a note can
embed many files, and without the name the author has to find the broken one by hand.

Constraints: no check changes what it accepts or rejects; only the wording of findings changes.

## Decision

- **The rule, for every finding `check-vault.py` prints, now and in future checks:** a finding names the note,
  the property and the rule that failed, and, where it helps, the *type* of what was found (a string, a list).
  It never prints a property's value, part of one, or text a parser quoted from the front matter. This
  partly supersedes decision 0003: the finding format in its Decision (`<property> is <value>, not <type>`)
  is replaced; the rest of 0003 stands.
- **What was found is named by its YAML type**, one of: `a string`, `a number`, `a boolean`, `a date`,
  `a datetime`, `a list`, `a mapping`. For a list whose items are the problem, the finding names the first
  bad item by position and type (`item 2 is a number`). Nothing longer: the author has the note open.
- **Each finding that printed a value becomes:**

  | Check | New finding |
  |---|---|
  | Property types | `<property> is <found type>, not <type>`, e.g. `updated is a string, not date`; `aliases is a list whose item 1 is a number, not aliases`; `summary is a list, not text` |
  | Record kind | `kind must be 'decision'` |
  | Record status | `status is not one of approved, implemented, …` |
  | Actor status | `status is missing; it must be one of …` when absent, else `status is not one of …` |
  | Record number | `number is <found type>, not a whole number`, e.g. `number is a string, not a whole number` |
  | Supersession links | `<property> is not a link to <what>` for one value; `<property> item N is not a link to <what>` in a list |
  | Broken YAML | `front matter is not valid YAML (line L, column C)` from the parser's position, which is two numbers; without one, `front matter is not valid YAML`. The parser's message is dropped. |

  The `error: <note>: ` prefix, the order of findings and the exit status are unchanged.
- **Kept as they are**, because they print only note names, property names, the template's own allowed lists,
  or an integer already validated: every finding in the list of safe ones above.
- **`embeds a missing file: <target>` is kept**, and is the one stated exception: the target is body text
  written as a link, not a property value, and is needed to fix the link. The rule's wording covers it:
  properties are never printed; an embed's target is.
- **The implementing PR** changes `check-vault.py.jinja` and the expected text in `tests/test_obsidian.py`
  (`TYPE_CASES`, and in `VAULT_CASES` the bad status, partial-to-a-non-record and bad front matter cases),
  and adds a test that a secret-looking value in a typed property, in `kind`, `status`, `number`, a
  supersession property and in broken YAML never appears in the output. It also adds the rule to the module
  docstring, so a future check follows it.

## Alternatives considered

- **Hide only properties a brain marks sensitive** (a `sensitive` or `pass_only` flag beside the property's
  type, in `types.json` or a file of the brain's own): prints values everywhere else, which helps a little
  with a type error. But Obsidian owns `types.json` and rewrites it, so a flag there can be lost; a separate
  list must be kept in step with every new property, and the property that leaks is the one nobody thought to
  list, or the wrong line a value was pasted into. A value is never needed to fix a type error: the author
  opens the note and sees it. *Rejected* for the generic rule.
- **Mask the value** (`updated is "1***", not date`, or its length): still prints part of it, and a short
  secret is mostly shown. *Rejected*.
- **Print values locally, hide them in CI** (an environment switch): two outputs to test, and an assistant
  running the check locally still reads the value into its context and may repeat it. *Rejected*.
- **Keep the parser's YAML message but strip quoted text**: the parser's wording varies by error and version,
  so a filter can't be shown to catch every case; the line and column are enough to find the error.
  *Rejected*.
- **Drop the embed target too**, for one rule with no exception: the target is a link the author wrote in
  prose, not a property, and a note with several embeds would leave the author guessing. *Rejected*.

## Consequences

- A minor release (a `feat`): the output's wording changes, what passes and fails does not. A brain that
  passes still passes with the same one line; a failing brain fails on the same notes with new wording.
  Nothing parses these findings except this repo's tests, which change with it.
- A finding tells the author where to look and what is wrong, not what is there: fixing a type error means
  opening the note, which the author does anyway.
- A secret pasted into any property no longer reaches the terminal, an assistant's context or a CI log by way
  of this check. It is still in the note and in git history: removing it is the brain's job, and this record
  doesn't change that.
- Decision 0003's finding format is replaced; its type table, records' `created` and the rest stand.
  0003's Status line notes it (see Resolved questions).
- Brains get the change on `copier update`; `check-vault.py` is template-owned, so no brain edits it.
- Rollback: revert the release; findings print values again.

## Resolved questions

Approved by the brain coordinator for Stephen, 2026-11-04, with each open question answered as recommended:

1. **How should 0003 record that part of it is replaced?** A line under its `Status: Approved`:
   `Partly superseded by 0004 (the finding format).`, and its index row says so. Decision 0002's
   `partially_superseded_by` property is for vault notes, not this folder's plain Markdown records.
2. **Should a type finding also give the expected form?** No. The type name says it, decision 0003's table
   spells out each form, and a shorter rule is easier to keep in every future check.
3. **Should the rule bind brains' own checks?** It becomes a convention in the seeded `📐 Conventions` note
   that new brains start with; each brain's own scripts stay its own. This template owns only
   `check-vault.py`.
