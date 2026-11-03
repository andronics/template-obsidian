# 0002: Status lifecycle and partial supersession

Status: Approved
Date: 2026-11-03
Authors: Stephen Cox

## Context

A brain records two kinds of things that are replaced over time: design records (`decisions/`, decision 0001)
and actors, the identities its automations act as (`kind: actor` notes; the brain's own `actors/` section).
`check-vault.py` only knew about records, and for them only whole replacement: a successor's `supersedes` and
the old record's `superseded_by` link each other, and `superseded_by` forces `status: superseded`.

Two cases don't fit:

- **A record replaced in part.** The brain's record 0004 (the pass layout) replaces only point 3 of 0003 (the
  key-path rule); the rest of 0003 stands. Listing 0003 in 0004's `supersedes` fails the check unless 0003 gets
  `superseded_by`, which then forces `status: superseded`, which is false. So the brain leaves both properties
  empty and says it in a comment and a callout, where nothing checks it.
- **Actors have no end states.** Their lifecycle (`planned`, `created`, `installed`, `active`, `retired`) has
  nothing for an actor another one took over, or one whose App is gone, and no property for the successor.
  The brain's Metalayerlab Release App was split into Stardate and Ansible and then deleted; it can only say
  `retired`.

The idea note **🤹 Template Actors** lists both gaps. Stephen answered its question 5 on 2026-11-03: add
`deleted` and `superseded`, `superseded_by` and partial supersession together, including this check. Its
"should not include" list leaves actor notes, their legends and `Actors.base` to template-obsidian and the brain;
the actor manifest (`.github/actors/*.yml`, template-actors) comes later and becomes the source of truth.

Constraints: every brain that passes today must still pass, and the properties must stay ones Obsidian's
Properties panel and Bases can show and filter (flat values or lists of links, no nested mappings).

## Decision

- **Partial supersession is its own pair of properties**, beside the whole-note pair, with the same shape:
  - `partially_supersedes`: a list of quoted wikilinks, on the newer note, to the notes it replaces part of.
  - `partially_superseded_by`: a list of quoted wikilinks, on the older note, to the notes that replaced part
    of it. The older note keeps its status: the rest of it stands.

  Which part is prose: the newer note says it (a record in its Decision, an actor in its Role), and the older
  one may say it in a comment beside the property. Both properties are optional and default to empty.
- **One link rule for both pairs and both kinds.** For each of `supersedes`, `superseded_by`,
  `partially_supersedes` and `partially_superseded_by`, every value must be a link to another note of the
  same kind (a record to a record, an actor to an actor; never itself), and that note must link back with the
  property's partner. A note may not name the same note as both wholly and partially superseded.
- **Design records:** statuses unchanged (`proposed`, `approved`, `implemented`, `superseded`, `rejected`).
  `superseded_by` still forces `status: superseded`. `deleted` doesn't apply: a record is never removed; a
  withdrawn one is `rejected`. The record template gains the two empty properties; `Decisions.base` shows
  *Superseded by* and *Partly superseded by*.
- **Actors** (any note with `kind: actor` outside Obsidian's templates folder, read from
  `.obsidian/templates.json`, default `_templates`):
  - `status` must be one of `planned`, `created`, `installed`, `active`, `retired`, `superseded`, `deleted`.
    `retired`: it stopped doing its job and nothing took over; its App may still exist. `superseded`: another
    actor took over its job. `deleted`: its App or identity no longer exists.
  - `superseded_by` (one link) means one actor took over all of it; a split is `partially_superseded_by`
    naming each actor that took a part.
  - `status: superseded` needs a successor: `superseded_by`, or `partially_superseded_by` for a split.
  - `superseded_by` allows only `status: superseded` or `deleted` (replaced, then removed; the successor stays
    recorded).
  - No other actor property is checked here; the manifest's validation (template-actors) checks the rest.
- **The check's output** adds `, N actors` after the record count when the vault has actor notes.

## Alternatives considered

- **Mappings in `supersedes`** (`supersedes: [{note: "[[…]]", part: "point 3"}]`): keeps one property and
  records the part, but Obsidian's Properties panel can't show or edit a list of mappings, Bases can't filter
  on it, and a brain mixing strings and mappings in one list is harder to read and check. *Rejected.*
- **Only `partially_superseded_by` on the older note:** the check could resolve it but not test that it points
  both ways, which is the rule decision 0001 set for supersession. *Rejected.*
- **A `partially-superseded` status:** a record's status says where it is in its own lifecycle (approved,
  implemented), and a partial replacement doesn't change that; it also can't name the successor. *Rejected.*
- **Making `superseded_by` a list:** would make a split look like a whole replacement by each actor, and changes
  a property every existing record has as a single link. *Rejected* for `partially_superseded_by`.
- **Also requiring `superseded_by` on a record with `status: superseded`:** consistent with actors, but a brain
  with such a record would fail on update. *Rejected* to keep the change backward compatible.
- **Seeding an actor note template and `Actors.base` here:** the brain's are its own, with its legends and
  themes; the manifest generator (template-actors) will produce the notes. *Deferred* to that work.

## Consequences

- Every brain that passed still passes: the new properties are optional, record rules are unchanged, and
  actor notes were unchecked before, so only an actor with a status outside the new set (or a broken
  supersession link) now fails.
- A brain can express 0003/0004-style partial replacement in properties and drop the comment-only
  workaround. The brain's actors can move to `superseded` or `deleted` and name their successors.
- The record template and `Decisions.base` reach existing brains on `copier update`. `📐 Conventions`,
  and `README.md` are seeds: existing brains update their own conventions by hand.
- template-actors' manifest uses the same actor statuses, `superseded_by` and `partially_superseded_by`, so a
  generated note checks clean.
- Rollback: revert the release; the new properties are then ignored, and actor notes are unchecked again.

## Open questions

None. Stephen answered the idea note's question 5 on 2026-11-03.
