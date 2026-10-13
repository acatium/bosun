# Rehearsal: "Finance defines IRR"

**Date:** 2026-10-13 · **Run by:** the platform owner, through the compiler · **Store:** Contoso Portfolio

## Before the change

Question to the portfolio data agent (MCP `tools/call`): "What is Fabrikam Software's IRR?"

> IRR is not a defined business term in the Contoso Capital semantic model, so I can't provide Fabrikam
> Software's IRR from this data. The closest defined terms available ... are: Revenue ... EBITDA ...

## The change

Two lines added to `model/contoso.yaml` (the text is in [`docs/demo/gross-irr-change.yaml`](../../docs/demo/gross-irr-change.yaml)):
a term `Gross IRR` (owner: Finance & Operations lead; calculation in DAX; source: fund cash flows) and a
dataset store `fund-cash-flows` (domain: Finance & Operations; sensitivity: Internal).

`python -m backplane plan` output:

```
term store: 1 change(s)
  create-term    Gross IRR
data: 4 change(s)
  load-dataset   fund_cash_flows
  add-table      fund_cash_flows
  add-measure    Gross IRR
  update-agent-vocabulary
```

`python -m backplane apply` output (two runs: the second added the step that lets the data agent see the
new table, which the first run showed was missing):

```
done: create-term Gross IRR
done: loaded data/portfolio/fund_cash_flows.csv into fund_cash_flows
done: added table fund_cash_flows to the semantic model
done: added measure 'Gross IRR' for term Gross IRR
done: regenerated the data agent's vocabulary from the model
re-plan: nothing left to do
...
done: let the data agent see table fund_cash_flows (draft)
done: let the data agent see table fund_cash_flows (published)
re-plan: nothing left to do
```

## Check against an independent calculation

`Gross IRR` by company from DAX `executeQueries`, against XIRR computed in Python from the same CSV before
the change:

| Company | DAX measure | Python XIRR |
|---|---|---|
| Fabrikam Software | 17.8% | 17.8% |
| Tailspin Health | 8.7% | 8.7% |
| Adventure Works Outdoor | 6.1% | 6.1% |
| Northwind Logistics | -0.9% | -0.9% |

## After the change

Same question to the data agent: "What is Fabrikam Software's Gross IRR?"

> Fabrikam Software's **Gross IRR** is **17.8%** as of **quarter ending 1 September 2026**.

**Known flaw:** the as-of date should read 30 September 2026 (the NAV date). The agent's instructions are
to be tightened.

**Found and fixed during the rehearsal:** the SQL endpoint must sync a new table before Direct Lake can read
it, and the data agent must be told to include the new table; both are now compiler steps.
