# Design records

Why template-obsidian is the way it is. Copy [0000-template.md](0000-template.md) to `NNNN-short-title.md` and
add a line below. **Read this index first.** The split itself is template-base's decision 0001.

| # | Title | Status | Decision in one line |
|---|---|---|---|
| [0001](0001-obsidian-overlay.md) | The obsidian stack overlay | Approved | A brain is base + this overlay: the vault is the wiki, records are notes, checks run in `checks.d/20-obsidian.sh`, Brain pull is opt-in; rebuilds project-template's 0015, 0016, 0018 and 0019 |
| [0002](0002-status-lifecycle-and-partial-supersession.md) | Status lifecycle and partial supersession | Approved | Records and actor notes link part-successors with `partially_supersedes` / `partially_superseded_by`; actors gain `superseded` and `deleted` and name their successors; check-vault checks both |
| [0003](0003-property-types-and-created-on-records.md) | Property types from types.json, and created on design records | Approved | When `.obsidian/types.json` exists, check-vault checks every property value against its registered type; records take `created` (or `date`) and optional `approved` / `approved_by`; `Decisions.base` shows *Created* falling back to `date`; `stack.md` allows `types.json` |
| [0004](0004-findings-never-print-a-value.md) | Findings that never print a value | Proposed | Every check-vault finding names the note, the property, the rule and the type found, never a value; the embed target stays; partly supersedes 0003's finding format |
