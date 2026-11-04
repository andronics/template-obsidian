---
kind: conventions
tags: [conventions]
---
%% Yours: copier update never touches this note. AGENTS.md tells assistants to follow it, so keep it short and exact. Changing a convention is a decision: record it. Then delete this comment. %%

## 📛 Names

- A note's name is its title, with a leading emoji: `🧭 Some Topic.md`.

## 🏷️ Properties

- Every note starts with YAML properties: at least `kind` and `tags`.

## 🔗 Links

- Link notes by name, never by path: [[🏠 Home]]. A link to a note that doesn't exist yet marks the next note to write.
- Files that notes embed live in `_attachments/`.

## 📝 Decisions

- A decision about this repository (its layout, its conventions, what it follows) is a design record in `decisions/`: *Insert template* → `📝 Design Record`, the next free number, `status: proposed`.
- Records are named `📝 NNNN Title In Title Case.md` and indexed by [[Decisions.base]]. A rejected idea is a record with `status: rejected`.
- A record that replaces another links it in `supersedes`, and the old one links back in `superseded_by` with `status: superseded`. One that replaces only part of it uses `partially_supersedes` and `partially_superseded_by` instead, and says which part; the old record keeps its status.

## 🎭 Actors

- A note with `kind: actor` is an identity an automation acts as. Its `status` is `planned`, `created`, `installed`, `active`, `retired`, `superseded` or `deleted`, and its successors are linked like a record's: `superseded_by` (and `status: superseded`, or `deleted` once it is gone too), or `partially_superseded_by` for a split, with `supersedes` and `partially_supersedes` on the successors.

## 🔍 Checks

- A check or script that reports on notes names the note, the property and the rule that failed, never a property's value: a secret pasted into the wrong property must not reach a terminal, an assistant or a CI log.
