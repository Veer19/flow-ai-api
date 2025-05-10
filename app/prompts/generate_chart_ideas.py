def get_generate_chart_ideas_prompt(project_context: str):
    return """
    ### PURPOSE
    Generate exactly **four** distinct chart recommendations that deliver the highest‑value insights for a given project.

    ### INPUT BLOCK – DO NOT RE‑EMIT
    Wrap the bulky project metadata inside `<DATA>` tags as shown below.  
    **The assistant must never quote or copy anything inside `<DATA>` in the response.**

    <DATA>""" + project_context + """</DATA>

    ### OUTPUT CONTRACT

    Return a JSON array of objects with the following schema and only the following keys:
        "chartType": "bar",
        "title": "Sales by Product Segment",
        "description": "Shows revenue distribution across segments and highlights the top performers.",
        "dataSource": ["sales.csv","products.csv"],
        "columns": ["PRODUCT_SEGMENT","QUANTITY"],
        "transformations": [
        "JOIN sales.csv ON products.csv USING PRODUCT_CODE",
        "GROUP BY PRODUCT_SEGMENT",
        "SUM QUANTITY"

    ### RULES
    1. **No duplicate insights** – each chart must answer a different business question.
    2. Sort charts by **expected impact** (highest first).
    3. Provide enough columns & transformations so downstream code can run.
    4. Think in two phases:
    - *Reason silently* (identify insights, rank, dedupe).
    - *THEN* output the final JSON only – nothing else.
    5. If two data sources relate, prefer a JOIN over standalone analysis.
    6. Every object must include all schema keys; no extra keys allowed.
    7. If there are any charts with dates involved, aggregate the data by week, month, or year.

    ### INTERNAL STEPS (assistant, do not output)
    1. Parse `<DATA>`; inspect relationships & stats.
    2. Brainstorm 6–8 insights; rank by impact.
    3. Keep top 4; ensure uniqueness.
    4. Generate IDs (slugify title).
"""

