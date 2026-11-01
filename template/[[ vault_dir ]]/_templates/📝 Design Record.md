---
kind: decision
number:
status: proposed        # proposed | approved | implemented | superseded | rejected
date: "{{date:YYYY-MM-DD}}"
authors: []
summary:                # the decision in one line
supersedes: []          # wikilinks, quoted: ["[[📝 0001 Title]]"]
superseded_by:
tags: [decision]
---
%% Name this note `📝 NNNN Title In Title Case` with the next free number, and fill `number`, `authors` and `summary`. A superseding record lists the old one in `supersedes`; the old one gets `superseded_by` and `status: superseded`. Template-owned: change it in project-template. %%

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
