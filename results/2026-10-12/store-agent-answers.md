# Store agent answers: Contoso Portfolio (owner run)

**Date:** 2026-10-12 · **Caller:** platform owner, through the data agent's MCP endpoint
(`tools/call` on `DataAgent_Contoso_Portfolio_Agent`) · **Source:** Contoso Portfolio semantic model,
reading OneLake through the workspace identity (the store key)

Expected values are in [`evals/golden-questions.yaml`](../../evals/golden-questions.yaml), computed with
DAX `executeQueries` against the same model.

| Question | Agent answer | Expected | Result |
|---|---|---|---|
| q1: EBITDA variance to plan, Sep 2026, ranked | Fabrikam +14.4%, Tailspin −2.9%, Adventure Works −8.0%, Northwind −25.0% | Same | Pass |
| q2: Northwind leverage, Sep 2026 | 2.5x | 2.5x | Pass |
| q3: IRR on Fabrikam (undefined term) | "IRR is not a defined term in the Contoso Portfolio semantic model, so I can't give you an IRR figure", then listed the closest defined terms | Refusal, no estimate | Pass |

Every figure in the answers named its glossary measure and as-of month, as the agent instructions
require. Full answer text follows.

### Q: As of September 2026, what is each portfolio company's EBITDA variance to plan for that month? Rank them.
Here are the portfolio companies ranked by **EBITDA variance to plan** for **September 2026** (using the **EBITDA variance to plan** measure for that month):

1. **Fabrikam Software** (Contoso Capital Fund III)  
   - EBITDA variance to plan (September 2026): **14.4%**

2. **Tailspin Health** (Contoso Capital Fund III)  
   - EBITDA variance to plan (September 2026): **-2.9%**

3. **Adventure Works Outdoor** (Contoso Capital Fund II)  
   - EBITDA variance to plan (September 2026): **-8.0%**

4. **Northwind Logistics** (Contoso Capital Fund III)  
   - EBITDA variance to plan (September 2026): **-25.0%**

### Q: What is Northwind Logistics' leverage as of September 2026?
Northwind Logistics’ **Leverage** (measure: **Leverage**) as of **September 2026** is **2.5x**.

### Q: What is the IRR on Fabrikam Software?
IRR is not a defined term in the Contoso Portfolio semantic model, so I can’t give you an IRR figure for Fabrikam Software from this data.

The closest defined terms we have for Fabrikam Software (as of the latest month, 9/1/2026) are:

- Revenue (9/1/2026): 5,106 (measure: Revenue, month: 9/1/2026)  
- Plan revenue (9/1/2026): 4,800 (measure: Plan revenue, month: 9/1/2026)  
- EBITDA (9/1/2026): 1,373 (measure: EBITDA, month: 9/1/2026)  
- Plan EBITDA (9/1/2026): 1,200 (measure: Plan EBITDA, month: 9/1/2026)  
- EBITDA margin (9/1/2026): 26.9% (measure: EBITDA margin, month: 9/1/2026)  
- LTM EBITDA (9/1/2026): 13,605 (measure: LTM EBITDA, month: 9/1/2026)  
- Net debt (9/1/2026): 14.2 (measure: Net debt, month: 9/1/2026; in USD millions)  
- Leverage (9/1/2026): 1.0x (measure: Leverage, month: 9/1/2026)

If you’d like to approximate or discuss an IRR based on these measures, you’d need separate information on entry valuation, cash in, and cash out, which is not available in this semantic model.

