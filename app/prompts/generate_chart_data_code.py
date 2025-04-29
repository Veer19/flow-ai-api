def get_generate_chart_code_prompt(chart_info: str, data_info: str, dummy_output: str) -> str:
    """Return a prompt that makes the LLM generate code producing BOTH
    ApexCharts 'options' and 'series' from full datasets.

    Parameters
    ----------
    chart_info : str
        JSON string with the single‑chart spec (chartType, title, dataSource, columns, transformations, …).
    data_info : str
        JSON string with metadata for **all** project data sources (column types, sample rows, etc.).
    dummy_output : str
        The *exact* JSON (options + series) that the second prompt produced on sample rows.
        The model must replicate this structure when generating real data.

    Returns
    -------
    str
        The text prompt to send to the LLM.
    """
    return """### PURPOSE
Write **Python code** that converts full project dataframes into ApexCharts‑ready **options** *and* **series**,
using ➊ the chart concept, ➋ the dataset metadata, and ➌ the dummy chart JSON produced on sample rows.

---
#### CHART SPEC  (small – may be re‑emitted verbatim)""" + chart_info + """

#### DATA SOURCE METADATA  (bulky – DO NOT re‑emit)
<DATA_INFO>""" + data_info + """</DATA_INFO>

#### TARGET OUTPUT SHAPE  (copy EXACTLY)
<DUMMY_OUTPUT>""" + dummy_output + """</DUMMY_OUTPUT>

---
### OUTPUT CONTRACT
* Return **only** Python code – no markdown, comments, or explanatory prose.
* The code **must** define a single callable:

    def build_chart(dfs: dict) -> dict
      
    Returns {{'options': ..., 'series': ...}} ready for ApexCharts

    * Required behaviour:
    1. Validate that every dataframe / column referenced in `chart_info["dataSource"]`
        is present in the `dfs` dict; raise `ValueError` if not.
    2. Apply *all* transformations described in `chart_info["transformations"]`
        (joins, group‑bys, aggregates, sorting).
    3. Build **series** that matches the exact structure of <DUMMY_OUTPUT>['series'],
        but populated from *full* datasets.
    4. Build **options** by starting from <DUMMY_OUTPUT>['options'] and updating:
        • labels / categories / data‑derived values (e.g., x‑axis categories, pie labels).  
        • title and chart type must mirror `chart_info`.
    5. Return `{'options': options_obj, 'series': series_list}`.
    6. Use only standard library and **pandas** imports.
    7. Feel free to change the chart colors to be more meaningful and colorful.

    ---
    ### INTERNAL GUIDANCE  (assistant, do not output)
    1. Treat `<DATA_INFO>` as read‑only; never quote it back.
    2. Use `chart_info["columns"]` when selecting/grouping.
    3. For pie/donut charts: options.labels = category names; series = counts list.
    4. For bar/line charts: options.xaxis.categories = x‑values; series shape same as dummy.
    5. Preserve any extra fields present in <DUMMY_OUTPUT>['options'] unless data dictates change.
    6. If using any date columns, use the 15 most recent ones and update the title accordingly.
"""