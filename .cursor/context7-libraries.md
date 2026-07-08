# Context7 library IDs — McKenna Derby

Use these IDs with the Context7 MCP (`resolve-library-id` / `query-docs`) for up-to-date docs. Prefer this table over guessing IDs.

| Stack piece | Context7 ID | Notes |
|-------------|-------------|-------|
| NumPy | `/websites/numpy_doc_2_4` | Arrays, linear algebra |
| pandas | `/websites/pandas_pydata` | DataFrames, time series |
| SciPy | `/websites/scipy_doc_scipy` | `stats`, permutation tests |
| Matplotlib | `/websites/matplotlib_stable` | CLI report plots |
| Streamlit | `/streamlit/docs` | `dashboard.py` |
| Plotly | `/plotly/plotly.py` | Dashboard charts |
| pytest | `/pytest-dev/pytest` | Golden tests, fixtures |
| CrewAI | `/websites/crewai_en` | Planner crew in `crewai/` |

## Example

Ask Context7: "How do I use `scipy.stats.spearmanr` with NaN handling?" with library ID `/websites/scipy_doc_scipy`.
