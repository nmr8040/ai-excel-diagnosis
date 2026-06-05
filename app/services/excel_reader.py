from pathlib import Path
from typing import Union

import pandas as pd


def read_excel_file(file_path: Union[str, Path]) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        for encoding in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path, encoding="utf-8", errors="replace")

    if suffix == ".xls":
        return pd.read_excel(path, engine="xlrd")

    return pd.read_excel(path, engine="openpyxl")


def get_preview_data(df: pd.DataFrame, max_rows: int = 50) -> dict:
    preview_df = df.head(max_rows)
    return {
        "columns": list(preview_df.columns.astype(str)),
        "rows": preview_df.fillna("").astype(str).values.tolist(),
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }


def get_data_summary(df: pd.DataFrame) -> dict:
    columns_info = []
    for col in df.columns:
        col_str = str(col)
        series = df[col]
        col_info = {
            "name": col_str,
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_values": [str(v) for v in series.dropna().head(3).tolist()],
        }
        if pd.api.types.is_numeric_dtype(series):
            col_info["min"] = float(series.min()) if series.notna().any() else None
            col_info["max"] = float(series.max()) if series.notna().any() else None
            col_info["mean"] = float(series.mean()) if series.notna().any() else None
        columns_info.append(col_info)

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_info,
        "column_names": [str(c) for c in df.columns],
    }
