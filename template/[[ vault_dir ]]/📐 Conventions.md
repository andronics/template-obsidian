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
