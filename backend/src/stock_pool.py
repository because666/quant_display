from __future__ import annotations

import logging
import re
from pathlib import Path

import akshare as ak
import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data_fetcher import META_DATA_DIR, _normalize_stock_code, _retry_call, cache_daily_data, download_daily_data


logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_LOG = LOG_DIR / "data_download.log"


def _cache_path_for_range(start_date: str, end_date: str) -> Path:
    slug_start = start_date.replace("-", "")
    slug_end = end_date.replace("-", "")
    return META_DATA_DIR / f"surviving_stocks_{slug_start}_{slug_end}.parquet"


def _setup_file_logger() -> None:
    if logger.handlers:
        return
    handler = logging.FileHandler(DOWNLOAD_LOG, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _detect_code_col(df: pd.DataFrame) -> str:
    best_col: str | None = None
    best_ratio = -1.0
    for col in df.columns:
        sample = df[col].dropna().astype(str).head(80)
        if sample.empty:
            continue
        ratio = float(sample.str.match(r"^\d{6}$").fillna(False).mean())
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = str(col)

    if best_col is None or best_ratio < 0.6:
        raise ValueError("Unable to detect code column in stock list.")
    return best_col


def _detect_date_col(df: pd.DataFrame) -> str:
    best_col: str | None = None
    best_ratio = -1.0
    for col in df.columns:
        sample = df[col].dropna().head(80)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce")
        ratio = float(parsed.notna().mean())
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = str(col)

    if best_col is None or best_ratio < 0.6:
        raise ValueError("Unable to detect date column in stock list.")
    return best_col


def _detect_name_col(df: pd.DataFrame, code_col: str, date_col: str) -> str:
    candidates = [c for c in df.columns if str(c) not in {code_col, date_col}]
    if not candidates:
        raise ValueError("Unable to detect name column in stock list.")

    best_col: str | None = None
    best_score = -1.0
    for col in candidates:
        sample = df[col].dropna().astype(str).head(80)
        if sample.empty:
            continue
        # name 列通常包含非 6 位数字
        is_code = sample.str.match(r"^\d{6}$").fillna(False)
        ratio_non_code = float((~is_code).mean())
        # date 列也可能被错误选中：用解析成功率做惩罚
        parsed = pd.to_datetime(sample, errors="coerce")
        date_ratio = float(parsed.notna().mean())
        score = ratio_non_code - 0.3 * date_ratio
        if score > best_score:
            best_score = score
            best_col = str(col)

    if best_col is None:
        best_col = str(candidates[0])
    return best_col


def _standardize_stock_list(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["code", "name", "listing_date"])

    code_col = _detect_code_col(df)
    date_col = _detect_date_col(df)
    name_col = _detect_name_col(df, code_col=code_col, date_col=date_col)

    out = pd.DataFrame(
        {
            "code": df[code_col].astype(str).map(_normalize_stock_code),
            "name": df[name_col].astype(str),
            "listing_date": pd.to_datetime(df[date_col], errors="coerce"),
        }
    )
    out = out.dropna(subset=["listing_date"]).drop_duplicates(subset=["code"]).reset_index(drop=True)
    return out[["code", "name", "listing_date"]]


def _build_delisted_map(end_date: str) -> dict[str, pd.Timestamp]:
    sz_delist = _retry_call(ak.stock_info_sz_delist)
    sh_delist = _retry_call(ak.stock_info_sh_delist)
    delist_df = pd.concat([sz_delist, sh_delist], ignore_index=True)
    if delist_df.empty:
        return {}

    code_col = _detect_code_col(delist_df)

    # 找出日期列（通常有 listing_date/delist_date 两列）
    date_cols: list[str] = []
    for col in delist_df.columns:
        if str(col) == code_col:
            continue
        sample = delist_df[col].dropna().head(80)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce")
        ratio = float(parsed.notna().mean())
        if ratio >= 0.8:
            date_cols.append(str(col))

    if not date_cols:
        return {}

    if len(date_cols) == 1:
        delist_date_col = date_cols[0]
    else:
        parsed_dates = {c: pd.to_datetime(delist_df[c], errors="coerce") for c in date_cols}
        # delist_date 一般更晚：取“平均日期更大”的列
        mean_ord = {c: float(parsed_dates[c].dropna().astype("int64").mean()) for c in date_cols}
        delist_date_col = max(mean_ord, key=mean_ord.get)

    end_ts = pd.Timestamp(end_date)
    delist_dates = pd.to_datetime(delist_df[delist_date_col], errors="coerce")
    code_series = delist_df[code_col].astype(str).map(_normalize_stock_code)

    mask = delist_dates.notna() & (delist_dates <= end_ts)
    out = dict(zip(code_series[mask].tolist(), delist_dates[mask].tolist()))
    return out


def get_surviving_stocks(
    start_date: str = "2014-01-01",
    end_date: str = "2024-12-31",
    refresh_cache: bool = False,
) -> pd.DataFrame:
    """
    筛选在 start_date 之前已上市、且在 end_date 时仍未退市的 A 股（SZ+SH）。

    退市判断：
    - 使用 `ak.stock_info_sz_delist` / `ak.stock_info_sh_delist` 批量拿退市日期；
    - 当 `delist_date <= end_date` 时认为已退市（不纳入存活池）。
    """
    cache_path = _cache_path_for_range(start_date, end_date)
    if cache_path.exists() and not refresh_cache:
        cached = pd.read_parquet(cache_path)
        cached["listing_date"] = pd.to_datetime(cached["listing_date"], errors="coerce")
        return cached[["code", "name", "listing_date"]].reset_index(drop=True)

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    # 1) 全量代码（包含已退市股票）
    all_df = _retry_call(ak.stock_info_a_code_name)
    if all_df is None or all_df.empty:
        return pd.DataFrame(columns=["code", "name", "listing_date"])

    code_col = _detect_code_col(all_df)
    # name 列：非 code 的其它列，取字符串样本中非纯数字最多的
    candidates = [c for c in all_df.columns if str(c) != str(code_col)]
    name_col = candidates[0]
    best_score = -1.0
    for c in candidates:
        sample = all_df[c].dropna().astype(str).head(80)
        if sample.empty:
            continue
        is_code = sample.str.match(r"^\d{6}$").fillna(False)
        score = float((~is_code).mean())
        if score > best_score:
            best_score = score
            name_col = c

    all_df_std = pd.DataFrame(
        {
            "code": all_df[code_col].astype(str).map(_normalize_stock_code),
            "name": all_df[name_col].astype(str),
        }
    ).drop_duplicates(subset=["code"])

    # 2) 退市表：批量获取 listing_date/delist_date（用于补齐“end_date 时仍未退市”的定义）
    sz_delist = _retry_call(ak.stock_info_sz_delist)
    sh_delist = _retry_call(ak.stock_info_sh_delist)
    delist_df = pd.concat([sz_delist, sh_delist], ignore_index=True)
    if delist_df is None or delist_df.empty:
        delisted_listing_map: dict[str, pd.Timestamp] = {}
        delisted_date_map: dict[str, pd.Timestamp] = {}
    else:
        delist_code_col = _detect_code_col(delist_df)
        date_like_cols: list[str] = []
        mean_ord: dict[str, float] = {}
        for c in delist_df.columns:
            if str(c) == str(delist_code_col):
                continue
            sample = delist_df[c].dropna().head(80)
            if sample.empty:
                continue
            parsed = pd.to_datetime(sample, errors="coerce")
            ratio = float(parsed.notna().mean())
            if ratio >= 0.8:
                date_like_cols.append(str(c))
                full_parsed = pd.to_datetime(delist_df[c], errors="coerce")
                mean_ord[str(c)] = float(full_parsed.dropna().astype("int64").mean())

        if not date_like_cols:
            delisted_listing_map = {}
            delisted_date_map = {}
        else:
            # 取“较小的均值”列作为 listing_date，“较大的均值”列作为 delist_date
            means = [mean_ord[c] for c in date_like_cols]
            median_mean = float(np.median(means))
            listing_cols = [c for c in date_like_cols if mean_ord[c] <= median_mean]
            delist_cols = [c for c in date_like_cols if mean_ord[c] > median_mean]
            if not listing_cols:
                listing_cols = [min(mean_ord, key=mean_ord.get)]
            if not delist_cols:
                delist_cols = [max(mean_ord, key=mean_ord.get)]

            listing_series = (
                delist_df[listing_cols]
                .apply(lambda x: pd.to_datetime(x, errors="coerce"))
                .bfill(axis=1)
                .iloc[:, 0]
            )
            delist_series = (
                delist_df[delist_cols]
                .apply(lambda x: pd.to_datetime(x, errors="coerce"))
                .bfill(axis=1)
                .iloc[:, 0]
            )
            code_series = delist_df[delist_code_col].astype(str).map(_normalize_stock_code)
            delisted_listing_map = dict(zip(code_series[listing_series.notna()].tolist(), listing_series[listing_series.notna()].tolist()))
            delisted_date_map = dict(zip(code_series[delist_series.notna()].tolist(), delist_series[delist_series.notna()].tolist()))

    # 3) 当前上市表补齐 listing_date（给那些不在退市表里的“尚存续标的”）
    current_std = pd.concat(
        [_standardize_stock_list(_retry_call(ak.stock_info_sz_name_code)), _standardize_stock_list(_retry_call(ak.stock_info_sh_name_code))],
        ignore_index=True,
    )
    current_listing_map = dict(zip(current_std["code"].tolist(), current_std["listing_date"].tolist()))
    # 退市标的以退市表 listing_date/delist_date 为准；未退市标的以当前列表为准

    # 4) 合并并过滤：listing_date < start_date 且 (delist_date > end_date 或 delist_date 为空)
    all_df_std["listing_date"] = all_df_std["code"].map(
        lambda c: delisted_listing_map.get(c, current_listing_map.get(c))
    )
    all_df_std["delist_date"] = all_df_std["code"].map(lambda c: delisted_date_map.get(c, pd.NaT))

    result = all_df_std.dropna(subset=["listing_date"]).copy()
    result = result[result["listing_date"] < start_ts]
    # 去掉“退”字样（可选降噪）
    result = result[~result["name"].str.contains(r"退", na=False)].copy()

    keep_mask = result["delist_date"].isna() | (result["delist_date"] > end_ts)
    result = result[keep_mask].copy()

    result = result.drop(columns=["delist_date"])
    result = result.drop_duplicates(subset=["code"]).sort_values("code").reset_index(drop=True)
    result.to_parquet(cache_path, index=False)
    return result[["code", "name", "listing_date"]]


def _download_one_with_retries(
    code: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
) -> pd.DataFrame:
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return download_daily_data(code, start_date, end_date)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_retries:
                import time

                time.sleep(1.2 * attempt)
    raise RuntimeError(
        f"download failed for {code} after {max_retries} retries"
    ) from last_exc


def download_and_cache_all_stocks(
    stock_list: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> None:
    """
    遍历股票列表，下载日线并写入 data/raw/{code}.parquet。
    单票失败记录日志，不中断整体。
    """
    _setup_file_logger()
    if stock_list.empty:
        logger.warning("stock_list is empty, nothing to download.")
        return

    codes = stock_list["code"].astype(str).tolist()
    failed: list[str] = []

    for code in tqdm(codes, desc="Download & cache daily"):
        try:
            df = _download_one_with_retries(code, start_date, end_date)
            cache_daily_data(code, df)
        except Exception as exc:  # noqa: BLE001
            failed.append(code)
            logger.exception("failed %s: %s", code, exc)

    logger.info(
        "download finished: ok=%s failed=%s",
        len(codes) - len(failed),
        len(failed),
    )
    if failed:
        fail_path = META_DATA_DIR / "download_failed_codes.txt"
        fail_path.write_text("\n".join(failed), encoding="utf-8")
        logger.warning("failed codes written to %s", fail_path)

