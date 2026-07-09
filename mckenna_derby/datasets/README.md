# Bundled race datasets

## `hk_runners.csv`

Processed Hong Kong Jockey Club races derived from the Kaggle dataset
[`gdaley/hkracing`](https://www.kaggle.com/datasets/gdaley/hkracing).

| Field | Value |
|-------|--------|
| Races | ~6,157 (after validation) |
| Date range | 1997-06-02 → 2005-08-28 |
| Columns | `date`, `race_id`, `horse`, `decimal_odds`, `finish_position` |

This file is the **default** data source for the dashboard and CLI so users do
not need a Kaggle token or CSV upload. Redistribution is subject to
[Kaggle Terms](https://www.kaggle.com/terms) and the dataset page.

### Rebuild from raw Kaggle download

```bash
kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
python scripts/build_bundled_data.py
```

Raw `rawdata/` stays gitignored; only this processed CSV is committed.
