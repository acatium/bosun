# Re-run, 2026-10-13 morning

Run by the platform owner from Claude Code, after resuming the F2 capacity. Addresses redacted.

## Offline checks

| Check | Command | Result |
|---|---|---|
| Model validation and reference check | `python -m backplane validate` | passed |
| Offline tests | `python -m unittest discover -s tests` | 12 tests, OK |
| Generated classes match the schema | the CI step (`gen-pydantic` diff) | no difference |
| Portability, with the real tenant and subscription identifiers supplied | `python tools/check_portability.py` | passed, 57 files |
| Deny-list over files and full history, with the private terms supplied locally | `python tools/check_denylist.py` | passed |

## Compiler

`python -m backplane plan`: groups 0, fabric 0, term store 0, data 0 changes.

`python -m backplane report`: model-level objects match the model; 4 compiled groups; 10 terms in the term
store; 0 deal rooms; overall CONFORMANT.

Two compiler changes were made and applied during this run:

- The data agent's refusal instruction now says to name the closest defined terms "without figures". Before
  this, the IRR refusal listed figures for those terms, two of them wrong ("EBITDA variance to plan: 0" for
  Fabrikam, whose value is +14.4%).
- The data agent's per-source instructions (`dataSourceInstructions`) are now generated from the model. They
  had been written by hand at setup and did not list new measures.

After applying, `plan` showed zero changes.

## Golden questions

`python evals/run_golden.py` ([runner](../../evals/run_golden.py), [questions](../../evals/golden-questions.yaml)),
through the data agent's MCP endpoint, after the two changes above.

As the partner (access through the compiled partner role group):

| Question | Result | Detail |
|---|---|---|
| q1-variance-ranking | Pass | - |
| q2-leverage | Pass | - |
| q3-undefined-term | Pass | - |

**Answers:**

### As of September 2026, what is each portfolio company's EBITDA variance to plan for that month? Rank them.

Here are the portfolio companies’ EBITDA variance to plan (measure: **EBITDA vs Plan %**) for **September 2026**, ranked from highest to lowest:

1. **Fabrikam Software (FBS)** – **+14.4%** EBITDA variance to plan  
2. **Tailspin Health (TSH)** – **-2.9%** EBITDA variance to plan  
3. **Adventure Works Outdoor (AWO)** – **-8.0%** EBITDA variance to plan  
4. **Northwind Logistics (NWL)** – **-25.0%** EBITDA variance to plan  

All figures are **EBITDA variance to plan for September 2026**. Positive values mean EBITDA is ahead of plan; negative values mean it is behind plan.

### What is Northwind Logistics' leverage as of September 2026?

Northwind Logistics’ **leverage** (Net debt / LTM EBITDA, measure: **Leverage x**) is **2.5x**, **as of September 1, 2026**.

### What is the IRR on Fabrikam Software?

IRR is not a defined term in the Contoso Capital semantic model, so I can’t provide an IRR figure for Fabrikam Software from this data.

The closest defined terms available for Fabrikam Software (as of 2026‑09) are:
- Revenue  
- Plan revenue  
- EBITDA  
- Plan EBITDA  
- EBITDA variance to plan (EBITDA vs Plan %)  
- EBITDA margin (EBITDA Margin %)  
- LTM EBITDA  
- Net debt  
- Leverage  
- Value creation initiative target uplift (Initiative Target Uplift)

If you have separate cash-flow data for the Fabrikam Software investment (e.g., draws and distributions by date), I can walk you through how to calculate IRR conceptually, but I can’t derive it from the portfolio model measures alone.


As the outsider (an analyst in the Private Equity domain, not covered by any read rule),
`python evals/run_golden.py --expect-denied`: all three questions refused by Fabric with
`"User is not authorized"`.

## Deal room

`create_deal_room` called over stdio exactly as Claude desktop launches the server, as the partner, for
"Project Dryrun" (Confidential, two members, CIM from the inbox):

```
{"result": "refused", "reason": "The Confidential label is not yet available to you, so no room was created.
Newly published labels can take a few hours to reach people."}
```

No group was created. Cause, found 2026-10-14: no label policy existed in the tenant (`Get-LabelPolicy` returned
nothing), so the labels were not published to anyone. The policy `contoso-labels` (the three Contoso labels,
published to the five personas) was created on 2026-10-14 at 17:44 UTC.

## Gross IRR after the model change

`docs/demo/gross-irr-change.yaml` was added to the model and applied (`plan` then `apply`, about two
minutes; re-plan zero changes). The measure, queried directly with DAX `executeQueries`, returned
Fabrikam 17.8%, Tailspin 8.7%, Adventure Works 6.1%, Northwind -0.9%, matching the independent XIRR in
[`irr-rehearsal.md`](irr-rehearsal.md).

The data agent was then asked ten times, as the partner:

| Runs | Data source instructions | Result |
|---|---|---|
| 3 (MCP) | hand-written, without Gross IRR | no query generated |
| 1 (MCP) "What's Fabrikam's IRR?" | generated | access error: "Either the database 'Contoso Portfolio' does not exist, or you do not have permissions to access it" |
| 1 (MCP) "What is the gross IRR for each portfolio company?" | generated | **wrong figure: 7.38% for all four companies** |
| 1 (Assistants API) same question | generated | no query generated |
| 4 (Assistants API, concurrent) same question | generated | 2 runs failed, 1 returned no message, 1 access error as above |

None returned a correct figure. The query behind the 7.38% answer was not captured. One concurrent run
exposed the query generated for the same question. It groups and filters on `monthly_financials`, which has
no relationship path to `fund_cash_flows`, where Gross IRR is defined:

```dax
// Latest available Gross IRR per portfolio company,
// showing company name, the exact as-of month, and the Gross IRR value.
DEFINE
  VAR _LastMonthPerCompany =
    ADDCOLUMNS(
      // Companies that have at least one monthly_financials row
      SUMMARIZE(
        'monthly_financials',
        'monthly_financials'[company_id]
      ),
      "LastMonth",
        CALCULATE(
          MAX('monthly_financials'[month])
        ),
      "Company Name",
        RELATED('companies'[company_name])
    )

EVALUATE
  SELECTCOLUMNS(
    ADDCOLUMNS(
      _LastMonthPerCompany,
      "Gross IRR Value",
        VAR _AsOfDate = [LastMonth]
        RETURN
          CALCULATE(
            [Gross IRR], // Existing measure in the model
            'monthly_financials'[month] == _AsOfDate
          )
    ),
    "company_name", [Company Name],
    "as_of_date", [LastMonth],
    "Gross IRR", [Gross IRR Value]
  )
ORDER BY
  [company_name] ASC,
  [as_of_date] ASC

```

The change was then reverted (`git checkout model/contoso.yaml`, `local/admin/reset_irr.py`); `plan` showed
zero changes.
