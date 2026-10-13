---
name: backplane
description: Change Contoso Capital's governance model (domains, roles, business terms, stores, rules) and compile it into Microsoft 365 and Fabric. Use when the platform owner asks to add or change a term, domain, role, store or rule, to onboard a data source, or to check conformance.
---

# Operating the backplane

You change the **model**; deterministic code changes the **tenant**. Never call Graph, Fabric or SharePoint
directly to make a governance change; always go through the model and the compiler.

## Steps

1. **Understand the request in model terms.** Which domains, roles, terms, stores or rules change? Read
   `model/contoso.yaml` and `model/bosun.yaml` first. If the request needs something the schema cannot
   express, stop and say so rather than working around it.
2. **Ask for anything the model requires that the person did not give**: a term's definition, owner and
   domain; a store's domain and sensitivity. Never invent a definition or an owner.
3. **Edit `model/contoso.yaml`** with the smallest change that does the job. Show the diff.
4. **Validate**: `model/.venv/bin/python -m backplane validate`. Fix and repeat until it passes.
5. **Plan**: `set -a; source local/bosun.env; set +a; model/.venv/bin/python -m backplane plan`. Explain
   each planned change in plain language: what will exist, who can see it, what it is tagged with.
6. **Apply only after the person approves the plan**: `... -m backplane apply`. It re-plans afterwards
   and must report nothing left to do.
7. **Report**: `... -m backplane report`. Show the conformance result.
8. **Commit** the model change on a branch with a message that says what changed and why, so the git
   history is the audit trail.

## Rules

- Agents propose, code applies, a person approves. Do not run `apply` without approval in this session.
- If the compiler cannot express a change (a gap in an emitter), report the gap; do not patch the tenant
  by hand.
- Environment identifiers stay in `local/bosun.env`; never write them into tracked files.
