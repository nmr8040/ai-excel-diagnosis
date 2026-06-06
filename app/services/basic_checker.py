from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd


def analyze_excel_basic(df: pd.DataFrame) -> list[dict]:
    results: list[dict] = []
    results.extend(_check_blank_cells(df))
    results.extend(_check_duplicate_rows(df))
    results.extend(_check_numeric_anomalies(df))
    results.extend(_check_date_missing(df))
    results.extend(_check_negative_values(df))
    results.extend(_check_extreme_values(df))
    results.extend(_check_period_changes(df))
    results.extend(_check_category_bias(df))
    return results


OPTIONAL_COLUMN_KEYWORDS = (
    "備考", "メモ", "コメント", "注記", "remarks", "remark", "note", "memo", "comment",
)
REQUIRED_COLUMN_KEYWORDS = (
    "担当", "日付", "date", "金額", "数量", "ステータス", "状態", "期限", "納期",
    "顧客", "案件", "名称", "名前", "件名", "カテゴリ", "分類", "種別",
)


def _is_optional_column(col_name: str) -> bool:
    col_lower = str(col_name).lower()
    return any(kw in str(col_name) or kw in col_lower for kw in OPTIONAL_COLUMN_KEYWORDS)


def _is_important_column(col_name: str) -> bool:
    col_lower = str(col_name).lower()
    return any(kw in str(col_name) or kw in col_lower for kw in REQUIRED_COLUMN_KEYWORDS)


def _check_blank_cells(df: pd.DataFrame) -> list[dict]:
    results = []
    for col in df.columns:
        col_str = str(col)
        if _is_optional_column(col_str):
            continue

        null_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        null_count = int(null_mask.sum())
        if null_count == 0:
            continue

        ratio = null_count / len(df) * 100
        is_important = _is_important_column(col_str)

        # 重要列は10%超で指摘、それ以外は50%超のみ
        if is_important:
            if ratio <= 10:
                continue
            severity = "high" if ratio > 30 else "medium"
        else:
            if ratio <= 50:
                continue
            severity = "medium" if ratio <= 80 else "high"

        first_rows = [int(i) + 2 for i in df.index[null_mask].tolist()[:5]]
        hint = "入力漏れの可能性があります" if is_important else "多くの行が未入力です"
        results.append({
            "check_type": "空白セル",
            "target_column": col_str,
            "target_row": first_rows[0] if first_rows else None,
            "message": f"列「{col}」に空白が{null_count}件（{ratio:.1f}%）あります。{hint}。行: {first_rows}",
            "severity": severity,
        })
    return results


def _check_duplicate_rows(df: pd.DataFrame) -> list[dict]:
    results = []
    dup_mask = df.duplicated(keep=False)
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        unique_dup = int(df.duplicated().sum())
        results.append({
            "check_type": "重複行",
            "target_column": None,
            "target_row": None,
            "message": f"重複行が{dup_count}件検出されました（うち完全重複{unique_dup}件）。データ入力ミスや二重登録の可能性があります。",
            "severity": "high" if unique_dup > 5 else "medium",
        })
    return results


def _check_numeric_anomalies(df: pd.DataFrame) -> list[dict]:
    results = []
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if len(series) < 5:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        if len(outliers) > 0:
            outlier_rows = [int(i) + 2 for i in outliers.index.tolist()[:5]]
            results.append({
                "check_type": "数値異常値",
                "target_column": str(col),
                "target_row": outlier_rows[0] if outlier_rows else None,
                "message": f"列「{col}」に統計的異常値が{len(outliers)}件あります（IQR法）。行: {outlier_rows}",
                "severity": "high" if len(outliers) > len(series) * 0.1 else "medium",
            })
    return results


def _check_date_missing(df: pd.DataFrame) -> list[dict]:
    results = []
    date_keywords = ("日", "date", "期限", "納期", "期日", "作成", "更新", "受付")
    for col in df.columns:
        col_lower = str(col).lower()
        if not any(kw in col_lower or kw in str(col) for kw in date_keywords):
            continue
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            results.append({
                "check_type": "日付欠損",
                "target_column": str(col),
                "target_row": None,
                "message": f"日付関連列「{col}」に欠損が{null_count}件あります。期限管理や進捗追跡に影響する可能性があります。",
                "severity": "high" if null_count > len(df) * 0.2 else "medium",
            })
    return results


def _check_negative_values(df: pd.DataFrame) -> list[dict]:
    results = []
    positive_keywords = ("金額", "数量", "在庫", "売上", "単価", "時間", "件数", "price", "amount", "qty")
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        col_str = str(col).lower()
        if not any(kw in col_str or kw in str(col) for kw in positive_keywords):
            continue
        negatives = df[df[col] < 0]
        if len(negatives) > 0:
            neg_rows = [int(i) + 2 for i in negatives.index.tolist()[:5]]
            results.append({
                "check_type": "マイナス値",
                "target_column": str(col),
                "target_row": neg_rows[0] if neg_rows else None,
                "message": f"列「{col}」にマイナス値が{len(negatives)}件あります。入力ミスの可能性があります。行: {neg_rows}",
                "severity": "high",
            })
    return results


def _check_extreme_values(df: pd.DataFrame) -> list[dict]:
    results = []
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if len(series) < 3:
            continue
        mean_val = series.mean()
        std_val = series.std()
        if std_val == 0 or np.isnan(std_val):
            continue
        extreme = series[series > mean_val + 5 * std_val]
        if len(extreme) > 0:
            extreme_rows = [int(i) + 2 for i in extreme.index.tolist()[:5]]
            results.append({
                "check_type": "極端に大きい値",
                "target_column": str(col),
                "target_row": extreme_rows[0] if extreme_rows else None,
                "message": f"列「{col}」に極端に大きい値が{len(extreme)}件あります（平均の5σ超）。行: {extreme_rows}",
                "severity": "high",
            })
    return results


def _check_period_changes(df: pd.DataFrame) -> list[dict]:
    results = []
    date_col = None
    for col in df.columns:
        col_str = str(col)
        if any(kw in col_str for kw in ("日", "date", "月", "期間")):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() > len(df) * 0.5:
                date_col = col
                df = df.copy()
                df["_parsed_date"] = parsed
                break

    if date_col is None:
        return results

    df_sorted = df.dropna(subset=["_parsed_date"]).sort_values("_parsed_date")
    if len(df_sorted) < 10:
        return results

    mid = len(df_sorted) // 2
    first_half = df_sorted.iloc[:mid]
    second_half = df_sorted.iloc[mid:]

    for col in df.columns:
        if col in ("_parsed_date", date_col):
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        mean1 = first_half[col].mean()
        mean2 = second_half[col].mean()
        if pd.isna(mean1) or pd.isna(mean2) or mean1 == 0:
            continue
        change_pct = abs((mean2 - mean1) / mean1) * 100
        if change_pct > 50:
            direction = "増加" if mean2 > mean1 else "減少"
            results.append({
                "check_type": "期間変動",
                "target_column": str(col),
                "target_row": None,
                "message": f"列「{col}」が前半期間と後半期間で{change_pct:.0f}%{direction}しています。業務量の変化やデータ品質の問題の可能性があります。",
                "severity": "medium" if change_pct < 100 else "high",
            })
    return results


def _check_category_bias(df: pd.DataFrame) -> list[dict]:
    results = []
    category_keywords = ("担当", "カテゴリ", "分類", "種別", "ステータス", "状態", "部署", "部門", "担当者")
    for col in df.columns:
        col_str = str(col)
        if not any(kw in col_str for kw in category_keywords):
            continue
        counts = df[col].value_counts(dropna=True)
        if len(counts) < 2:
            continue
        total = counts.sum()
        top_value = counts.index[0]
        top_ratio = counts.iloc[0] / total * 100
        if top_ratio > 60:
            results.append({
                "check_type": "偏り",
                "target_column": str(col),
                "target_row": None,
                "message": f"列「{col}」で「{top_value}」が{top_ratio:.0f}%を占めています。業務の偏りや放置案件の可能性があります。",
                "severity": "high" if top_ratio > 80 else "medium",
            })
        if len(counts) >= 3:
            top3_ratio = counts.head(3).sum() / total * 100
            if top3_ratio > 90:
                results.append({
                    "check_type": "偏り",
                    "target_column": str(col),
                    "target_row": None,
                    "message": f"列「{col}」の上位3カテゴリが{top3_ratio:.0f}%を占めています。少数への業務集中が見られます。",
                    "severity": "medium",
                })
    return results


def count_by_severity(results: list[dict]) -> dict:
    counter = Counter(r["severity"] for r in results)
    return {
        "high": counter.get("high", 0),
        "medium": counter.get("medium", 0),
        "low": counter.get("low", 0),
        "total": len(results),
    }
