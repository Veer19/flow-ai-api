def get_generate_chart_sample_data_prompt(chart_info: str, sample_data: str):
    return """
    ### PURPOSE
    Produce an **ApexCharts** configuration (**options** & **series**) for a single chart concept using the sample rows provided.

    ### CHART SPEC - """ + chart_info + """
    
    ### SAMPLE DATAFRAME(S)
    <DATA_SAMPLE>""" + sample_data + """</DATA_SAMPLE>

    ### FIELD RULES PER TYPE
    * **pie / donut**
    * `options.labels` = category names  
    * `series` = [count1, count2, …]
    * **bar / column**
    * `options.xaxis.categories` = x values  
    * `series` = [{ "name": metric, "data": [y1, y2, …] }]
    * **line / area**
    * same as bar, but `chart.type = "line" | "area"`

    ### MUST‑DOS
    1. Use counts calculated **only** from `<DATA_SAMPLE>` – never invent values.
    2. Pick a built‑in palette: `theme: { palette: "palette5" }`.
    3. Title must equal `chartInfo.title`.
    4. Return **one** JSON object with keys `"options"` and `"series"`.  
    5. Keep the charts colorful with meaningful colors.
    *Do not* wrap in markdown or add comments.

    ### VALIDATION EXAMPLE
    ```json
    {
    "options": {
        "chart": { "type": "pie" },
        "labels": ["Motorcycles","Classic Cars"],
        "title": { "text": "Distribution of Product Segments" },
        "theme": { "palette": "palette5" },
        "tooltip": { "y": { "formatter": "function(val){ return val }" } }
    },
    "series": [3,1]
    }
    ```
"""

