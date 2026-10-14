# Gross IRR after hiding relationship columns, 2026-10-14

The compiler now hides every column used in a relationship (`hide-key-column`). With that applied, the Gross IRR change
(`docs/demo/gross-irr-change.yaml`) was applied again and the data agent was asked five times over MCP as the partner.
Format: question | percentages in the answer | first 300 characters.

```
### What's Fabrikam's IRR? | ['17.8%'] | Fabrikam Software’s **Gross IRR** is **17.8%**, **as of 2026-09-30** (quarter end).
### What is the gross IRR for each portfolio company? | [] | I wasn’t able to retrieve any Gross IRR data from the Contoso Portfolio semantic model for any portfolio company—the query returned no rows.  That means I can’t state the Gross IRR for each company, or even confirm which companies have Gross IRR calculated, without fabricating information, which I m
### What is Fabrikam Software's Gross IRR? | ['17.8%'] | Fabrikam Software’s Gross IRR is **17.8%**, measured **as of 30 September 2026**.
### What is the gross IRR for each portfolio company? | [] | The semantic model does not contain any non-blank Gross IRR values for the portfolio companies as of the latest available date.  For the latest Gross IRR data (as of 9/30/2026), the result is:  - Adventure Works Outdoor — Gross IRR: not available (as of 2026-09-30)   - Fabrikam Software — Gross IRR:
### What's Fabrikam's IRR? | [] | I can’t access the Contoso Portfolio data model right now due to a connection/permissions issue, so I’m not able to retrieve actual Gross IRR values.  Using only the defined terms in your environment: - The relevant metric for your question is **Gross IRR** (“Gross internal rate of return from the f
```

Result: 2 of 5 correct (17.8%, as of 30 September 2026), 0 wrong figures, 3 without an answer. Apply output:

```
data: 6 change(s)
  load-dataset   fund_cash_flows
  add-table      fund_cash_flows
  add-measure    Gross IRR
  agent-add-table fund_cash_flows (draft config)
  agent-add-table fund_cash_flows (published config)
  update-agent-vocabulary 
  done: loaded data/portfolio/fund_cash_flows.csv into fund_cash_flows
  done: added table fund_cash_flows to the semantic model
  done: hid relationship column fund_cash_flows.company_id
  done: added measure 'Gross IRR' for term Gross IRR
  done: refreshed the semantic model so the new table and measure are queryable
  done: let the data agent see table fund_cash_flows (draft)
  done: let the data agent see table fund_cash_flows (published)
  done: regenerated the data agent's vocabulary from the model
  re-plan: nothing left to do
```

The change was then reverted (`local/admin/reset_irr.py`) and the capacity paused.
