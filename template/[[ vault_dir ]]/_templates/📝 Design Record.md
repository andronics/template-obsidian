---
kind: decision
number:
status: proposed        # proposed | approved | implemented | superseded | rejected
approved:               # the date it was approved
approved_by:            # who approved it
created: "{{date:YYYY-MM-DD}}"
authors: []
summary:                # the decision in one line
supersedes: []          # wikilinks, quoted: ["[[📝 0001 Title]]"]
superseded_by:
partially_supersedes: []      # records this one replaces only part of
partially_superseded_by: []   # records that replaced part of this one; it stands otherwise
tags: [decision]
---
%% Name this note `📝 NNNN Title In Title Case` with the next free number, and fill `number`, `authors` and `summary`. When the record is approved, fill `approved` and `approved_by`. A superseding record lists the old one in `supersedes`; the old one gets `superseded_by` and `status: superseded`. A record that replaces only part of an old one lists it in `partially_supersedes` and says which part in its Decision; the old one gets `partially_superseded_by` and keeps its status. Template-owned: change it in template-obsidian. %%

## 🧭 Context

%% The problem, what forces a decision now, and the constraints. %%

## ✅ Decision

%% What is decided, concretely enough to act on. %%

## ⚖️ Alternatives considered

%% Each option and why not. A rejected idea stays here, so nobody re-proposes it. %%

## 🌊 Consequences

%% What changes, what it costs, what follows. %%

## ❓ Open questions

%% None, or each question with who answers it. Approval needs none left. %%
