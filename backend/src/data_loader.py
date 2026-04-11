from __future__ import annotations

import argparse
import logging
import pickle
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_OUT_DIR = PROJECT_ROOT / "data"

logger = logging.getLogger(__name__)

# 内存缓存：(data_dir 绝对路径, 文件名, parquet mtime) -> 解析后的元组，避免重复 IO
_split_cache: dict[tuple[str, str, float, bool, str], tuple[pd.DataFrame, np.ndarray, list[int]]] = {}
_factor_cols_cache: dict[tuple[str, float], list[str]] = {}
_snapshot_cache: dict[tuple[str, float], tuple[pd.DataFrame, list[str]]] = {}


def clear_data_loader_cache() -> None:
    """清空 load_* 系列函数的内存缓存（换数据或单测时可用）。"""
    _split_cache.clear()
    _factor_cols_cache.clear()
    _snapshot_cache.clear()


def _require_columns(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"Required one of columns {candidates} not found. Got: {list(df.columns)}")


def _normalize_weekly_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    date_col = _require_columns(out, ["date", "日期"])
    code_col = _require_columns(out, ["stock_code", "股票代码", "code"])
    out["date"] = pd.to_datetime(out[date_col])
    out["stock_code"] = out[code_col].astype(str)
    return out


def add_future_return(weekly_df: pd.DataFrame, forward_weeks: int = 1) -> pd.DataFrame:
    """
    为每个股票添加 future_return_1w：
    future_close / close - 1

    future_close 使用 groupby('stock_code') + shift(-forward_weeks)
    这要求 weekly_df 为规整周频（如每周周五截面），否则“下周五”需要在上游确保对齐。
    """
    if weekly_df.empty:
        return weekly_df.copy()

    df = _normalize_weekly_df(weekly_df)
    close_col = _require_columns(df, ["close", "收盘"])
    df["close"] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.sort_values(["stock_code", "date"]).reset_index(drop=True)

    g = df.groupby("stock_code", group_keys=False)
    future_close = g["close"].shift(-forward_weeks)
    df["future_return_1w"] = future_close / df["close"] - 1.0

    return df


def split_by_time(
    df: pd.DataFrame,
    train_end: str = "2020-12-31",
    val_end: str = "2022-12-31",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    按 date 切分训练/验证/测试：
    - train: date <= train_end
    - val: train_end < date <= val_end
    - test: date > val_end
    """
    if df.empty:
        empty = df.copy()
        return empty, empty, empty

    out = _normalize_weekly_df(df)
    train_end_ts = pd.Timestamp(train_end)
    val_end_ts = pd.Timestamp(val_end)

    train = out[out["date"] <= train_end_ts].copy()
    val = out[(out["date"] > train_end_ts) & (out["date"] <= val_end_ts)].copy()
    test = out[out["date"] > val_end_ts].copy()

    return train, val, test


def to_query_format(
    df: pd.DataFrame,
    *,
    factor_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    将 df 转为 LightGBM 排序学习 query 格式：
    - group：每个 date 一个组（记录 group_sizes）

    返回：
    - formatted_df：包含 date, stock_code, X 因子列, y=future_return_1w, group_id, group_size
    - group_sizes：按 date 升序对应的每组样本数
    """
    if df.empty:
        return df.copy(), np.array([], dtype=int)

    out = _normalize_weekly_df(df)
    if "future_return_1w" not in out.columns:
        raise KeyError("future_return_1w column not found. Call add_future_return() first.")

    out = out.sort_values(["date", "stock_code"]).reset_index(drop=True)

    if factor_cols is None:
        forbidden = {"date", "stock_code", "future_return_1w", "close"}
        factor_cols = [c for c in out.columns if c not in forbidden]

    # group_id：date -> code 0..(n_groups-1)
    date_cat = pd.Categorical(out["date"], categories=np.sort(out["date"].unique()), ordered=True)
    out["group_id"] = date_cat.codes.astype(int)

    group_sizes_series = out.groupby("group_id", sort=True).size()
    # 确保 group_id 连续从 0 开始（若没有某些组，会导致 mismatch）
    group_sizes = group_sizes_series.reindex(range(out["group_id"].nunique())).to_numpy(dtype=int)
    group_size_map = out["group_id"].map(group_sizes_series.to_dict())
    out["group_size"] = group_size_map.astype(int)

    keep_cols = ["date", "stock_code", *factor_cols, "future_return_1w", "group_id", "group_size"]
    formatted_df = out[keep_cols].copy()
    return formatted_df, group_sizes


def generate_query_datasets(
    weekly_df: pd.DataFrame,
    *,
    output_dir: Path = DATA_OUT_DIR,
    train_end: str = "2020-12-31",
    val_end: str = "2022-12-31",
    forward_weeks: int = 1,
) -> dict[str, Path]:
    """
    从 weekly_df 生成排序学习 query 数据集并落盘：
    - data/train.parquet
    - data/val.parquet
    - data/test.parquet
    - data/factor_columns.pkl
    """
    if weekly_df.empty:
        raise ValueError("weekly_df is empty.")

    output_dir.mkdir(parents=True, exist_ok=True)

    df_with_label = add_future_return(weekly_df, forward_weeks=forward_weeks)
    # 标签为空的行（尾部无法构造 future）需要丢弃，否则样本会污染训练
    df_with_label = df_with_label.dropna(subset=["future_return_1w"]).copy()

    train_df, val_df, test_df = split_by_time(df_with_label, train_end=train_end, val_end=val_end)

    # 推断因子列：去除已知字段
    forbidden = {"date", "stock_code", "future_return_1w", "close"}
    factor_cols = [c for c in df_with_label.columns if c not in forbidden]
    with open(output_dir / "factor_columns.pkl", "wb") as f:
        pickle.dump(factor_cols, f)

    def _format_and_save(split_df: pd.DataFrame, out_path: Path) -> np.ndarray:
        formatted, group_sizes = to_query_format(split_df, factor_cols=factor_cols)
        # 过滤该 split 下日期组为空的情况
        if formatted.empty:
            raise ValueError(f"Split empty when saving to {out_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        formatted.to_parquet(out_path, index=False)
        return group_sizes

    train_sizes = _format_and_save(train_df, output_dir / "train.parquet")
    val_sizes = _format_and_save(val_df, output_dir / "val.parquet")
    test_sizes = _format_and_save(test_df, output_dir / "test.parquet")

    # 可选：保存 group_sizes，便于 LightGBM 直接读取
    for name, sizes in [("train", train_sizes), ("val", val_sizes), ("test", test_sizes)]:
        with open(output_dir / f"{name}_group_sizes.pkl", "wb") as f:
            pickle.dump(sizes, f)

    return {"train": output_dir / "train.parquet", "val": output_dir / "val.parquet", "test": output_dir / "test.parquet"}


def _parquet_mtime(path: Path) -> float:
    if not path.exists():
        return -1.0
    return path.stat().st_mtime


def load_factor_columns(*, data_dir: Path = DATA_OUT_DIR) -> list[str]:
    """
    返回任务 4 落盘的因子列名列表（与 factor_columns.pkl 一致）。
    结果按文件 mtime 缓存。
    """
    data_dir = Path(data_dir).resolve()
    pkl_path = data_dir / "factor_columns.pkl"
    mtime = _parquet_mtime(pkl_path)
    cache_key = (str(data_dir), mtime)
    if cache_key in _factor_cols_cache:
        return list(_factor_cols_cache[cache_key])

    if not pkl_path.exists():
        raise FileNotFoundError(f"factor_columns.pkl not found at {pkl_path}")

    with open(pkl_path, "rb") as f:
        cols = pickle.load(f)
    if not isinstance(cols, list) or not all(isinstance(x, str) for x in cols):
        raise TypeError("factor_columns.pkl must be a list[str].")

    _factor_cols_cache[cache_key] = list(cols)
    return list(cols)


def fill_missing_factors(
    df: pd.DataFrame,
    factor_cols: list[str] | None = None,
    *,
    method: Literal["median", "zero"] = "median",
) -> pd.DataFrame:
    """
    对因子列缺失值做统一填充（默认列内中位数），并记录填充日志。
    返回新 DataFrame，不修改入参。
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    if factor_cols is None:
        forbidden = {"date", "stock_code", "future_return_1w", "group_id", "group_size"}
        factor_cols = [c for c in out.columns if c not in forbidden]

    present = [c for c in factor_cols if c in out.columns]
    if not present:
        logger.warning("fill_missing_factors: no factor columns present in df")
        return out

    for col in present:
        s = pd.to_numeric(out[col], errors="coerce")
        n_missing = int(s.isna().sum())
        if n_missing == 0:
            continue
        if method == "median":
            fill_v = s.median()
            if pd.isna(fill_v):
                fill_v = 0.0
        elif method == "zero":
            fill_v = 0.0
        else:
            raise ValueError(f"Unknown method: {method}")
        out[col] = s.fillna(fill_v)
        logger.info(
            "fill_missing_factors | column=%s | method=%s | filled=%d | fill_value=%s",
            col,
            method,
            n_missing,
            fill_v,
        )

    return out


def _group_sizes_from_df(df: pd.DataFrame) -> np.ndarray:
    """与 to_query_format 一致：按 date 升序，每组样本数。"""
    if df.empty:
        return np.array([], dtype=int)
    d = df.sort_values(["date", "stock_code"])
    return d.groupby("date", sort=True).size().to_numpy(dtype=int)


def _load_split_arrays(
    split: Literal["train", "val", "test"],
    *,
    data_dir: Path,
    apply_fill: bool,
    fill_method: Literal["median", "zero"],
) -> tuple[pd.DataFrame, np.ndarray, list[int]]:
    data_dir = Path(data_dir).resolve()
    parquet_path = data_dir / f"{split}.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"{split}.parquet not found at {parquet_path}")

    mtime = _parquet_mtime(parquet_path)
    cache_key = (str(data_dir), split, mtime, apply_fill, fill_method)
    if cache_key in _split_cache:
        X_df, y_arr, groups = _split_cache[cache_key]
        return X_df.copy(), y_arr.copy(), list(groups)

    df = pd.read_parquet(parquet_path)
    factor_cols = load_factor_columns(data_dir=data_dir)
    missing_fc = [c for c in factor_cols if c not in df.columns]
    if missing_fc:
        raise KeyError(f"{split}.parquet missing factor columns: {missing_fc}")

    if "future_return_1w" not in df.columns:
        raise KeyError(f"{split}.parquet missing future_return_1w")

    X_df = df[factor_cols].copy()
    y_arr = pd.to_numeric(df["future_return_1w"], errors="coerce").to_numpy(dtype=np.float64)

    pkl_gs = data_dir / f"{split}_group_sizes.pkl"
    if pkl_gs.exists():
        with open(pkl_gs, "rb") as f:
            gs = pickle.load(f)
        groups = [int(x) for x in np.asarray(gs).ravel()]
    else:
        groups = _group_sizes_from_df(df).tolist()

    if apply_fill:
        X_df = fill_missing_factors(X_df, factor_cols=factor_cols, method=fill_method)

    _split_cache[cache_key] = (X_df, y_arr, groups)
    return X_df.copy(), y_arr.copy(), list(groups)


def load_training_data(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = False,
    fill_method: Literal["median", "zero"] = "median",
) -> tuple[pd.DataFrame, np.ndarray, list[int]]:
    """
    加载训练集：与任务 4 落盘的 train.parquet / train_group_sizes.pkl 一致。
    默认 fill_missing=False，X/y 与落盘一致；建模前可设 fill_missing=True 统一去 NaN。
    返回 (X_train, y_train, groups_train)，groups_train 为按日期升序每组样本数。
    """
    return _load_split_arrays(
        "train",
        data_dir=data_dir,
        apply_fill=fill_missing,
        fill_method=fill_method,
    )


def load_validation_data(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = False,
    fill_method: Literal["median", "zero"] = "median",
) -> tuple[pd.DataFrame, np.ndarray, list[int]]:
    return _load_split_arrays(
        "val",
        data_dir=data_dir,
        apply_fill=fill_missing,
        fill_method=fill_method,
    )


def load_test_data(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = False,
    fill_method: Literal["median", "zero"] = "median",
) -> tuple[pd.DataFrame, np.ndarray, list[int]]:
    return _load_split_arrays(
        "test",
        data_dir=data_dir,
        apply_fill=fill_missing,
        fill_method=fill_method,
    )


def load_current_snapshot(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = True,
    fill_method: Literal["median", "zero"] = "median",
    refresh: bool = False,
    history_weeks: int = 60,
    latest_date: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    调用 realtime_updater.get_current_prediction_data()，返回当前截面因子矩阵与股票代码列表。
    因子列顺序与 load_factor_columns() 一致（仅保留当前结果中存在的列）。

    使用 refresh=True 或 clear_data_loader_cache() 可强制重新拉取；默认在同参数下使用内存缓存避免重复 IO/网络请求。
    """
    from . import realtime_updater  # 延迟导入，避免循环依赖

    cache_key = ("snapshot", str(data_dir.resolve()), latest_date or "_auto_", history_weeks)
    if not refresh and cache_key in _snapshot_cache:
        X_df, codes = _snapshot_cache[cache_key]
        return X_df.copy(), list(codes)

    raw = realtime_updater.get_current_prediction_data(
        latest_date=latest_date,
        history_weeks=history_weeks,
    )
    if raw is None or raw.empty:
        raise RuntimeError(
            "get_current_prediction_data() returned empty. "
            "Check network, stock pool, and local raw parquet cache."
        )

    factor_cols = load_factor_columns(data_dir=data_dir)
    codes = raw["stock_code"].astype(str).tolist()
    use_cols = [c for c in factor_cols if c in raw.columns]
    if not use_cols:
        numeric_omit = {"date", "stock_code"}
        use_cols = [c for c in raw.columns if c not in numeric_omit and pd.api.types.is_numeric_dtype(raw[c])]

    X_df = raw[use_cols].apply(pd.to_numeric, errors="coerce")
    if fill_missing:
        X_df = fill_missing_factors(X_df, factor_cols=use_cols, method=fill_method)

    _snapshot_cache[cache_key] = (X_df.copy(), list(codes))
    return X_df.copy(), list(codes)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate ranking learning query datasets")
    parser.add_argument("--input", required=True, help="Path to weekly_df parquet (must include date/stock_code/close and factor columns)")
    parser.add_argument("--output-dir", default=str(DATA_OUT_DIR), help="Output dir for train/val/test parquet")
    parser.add_argument("--train-end", default="2020-12-31")
    parser.add_argument("--val-end", default="2022-12-31")
    parser.add_argument("--forward-weeks", type=int, default=1)
    args = parser.parse_args()

    weekly_df = pd.read_parquet(args.input)
    generate_query_datasets(
        weekly_df,
        output_dir=Path(args.output_dir),
        train_end=args.train_end,
        val_end=args.val_end,
        forward_weeks=args.forward_weeks,
    )


if __name__ == "__main__":
    _main()

