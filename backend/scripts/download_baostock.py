"""
使用 Baostock 数据源下载A股历史日线数据
优势：免费、稳定、支持并行下载、约20分钟可完成全量下载
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import baostock as bs
import pandas as pd
from tqdm import tqdm

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
META_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "meta"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
META_DATA_DIR.mkdir(parents=True, exist_ok=True)


def login_bs() -> None:
    """登录Baostock"""
    lg = bs.login()
    if lg.error_code != "0":
        raise ConnectionError(f"Baostock登录失败: {lg.error_msg}")
    print("Baostock登录成功")


def logout_bs() -> None:
    """登出Baostock"""
    bs.logout()


def get_all_stock_codes() -> List[str]:
    """
    获取全部A股股票代码（含已退市）

    Returns:
        股票代码列表，格式如 ['sh.600000', 'sz.000001']
    """
    rs = bs.query_all_stock(day="")
    data_list = []
    while rs.error_code == "0" and rs.next():
        row = rs.get_row_data()
        code = row[0]
        if code.startswith(("sh.6", "sz.0", "sz.3")):
            data_list.append(code)
    return data_list


def get_surviving_stock_codes_from_cache(
    start_date: str = "2014-01-01",
    end_date: str = "2024-12-31",
) -> List[str]:
    """
    从缓存文件读取存续股票代码

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        存续股票代码列表（格式如 ['sh.600000', 'sz.000001']）
    """
    slug_start = start_date.replace("-", "")
    slug_end = end_date.replace("-", "")
    cache_path = META_DATA_DIR / f"surviving_stocks_{slug_start}_{slug_end}.parquet"

    if cache_path.exists():
        print(f"从缓存读取股票池: {cache_path}")
        df = pd.read_parquet(cache_path)
        codes = []
        for code in df["code"].astype(str).tolist():
            if code.startswith("6"):
                codes.append(f"sh.{code}")
            else:
                codes.append(f"sz.{code}")
        print(f"存续股票数量: {len(codes)}")
        return codes

    print("缓存文件不存在，使用Baostock筛选...")
    return get_surviving_stock_codes(start_date, end_date)


def get_surviving_stock_codes(
    start_date: str = "2014-01-01",
    end_date: str = "2024-12-31",
) -> List[str]:
    """
    使用Baostock筛选存续股票代码（在start_date前上市且在end_date时未退市）

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        存续股票代码列表
    """
    all_codes = get_all_stock_codes()

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    surviving_codes = []

    print(f"正在筛选存续股票（上市日期 < {start_date} 且未在 {end_date} 前退市）...")

    for code in tqdm(all_codes, desc="筛选股票池"):
        try:
            rs = bs.query_stock_basic(code=code)
            if rs.error_code != "0":
                continue

            data = rs.get_row_data()
            if not data:
                continue

            listing_date = pd.to_datetime(data[2], errors="coerce")
            delist_date = pd.to_datetime(data[3], errors="coerce")

            if pd.isna(listing_date):
                continue

            if listing_date >= start_ts:
                continue

            if pd.notna(delist_date) and delist_date <= end_ts:
                continue

            surviving_codes.append(code)

        except Exception:
            continue

    print(f"存续股票数量: {len(surviving_codes)}")
    return surviving_codes


def download_single_stock(
    code: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
) -> Tuple[str, bool, str, pd.DataFrame]:
    """
    下载单只股票日线数据

    Args:
        code: 股票代码（如 'sh.600000'）
        start_date: 开始日期（如 '2014-01-01'）
        end_date: 结束日期（如 '2024-12-31'）
        max_retries: 最大重试次数

    Returns:
        (股票代码, 是否成功, 错误信息, 数据DataFrame)
    """
    last_error: str = ""

    for attempt in range(1, max_retries + 1):
        try:
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",
            )

            if rs.error_code != "0":
                last_error = f"Baostock错误: {rs.error_msg}"
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
                continue

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return (code, False, "数据为空", pd.DataFrame())

            df = pd.DataFrame(data_list, columns=rs.fields)

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            for col in ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.rename(columns={
                "pctChg": "pct_chg",
                "turn": "turnover",
            })

            df["stock_code"] = code.split(".")[1]

            prev_close = df["close"].shift(1)
            df["is_suspended"] = (
                (df["volume"].fillna(0) == 0) & prev_close.notna() & (df["close"] == prev_close)
            )
            df["is_limit_up"] = (df["pct_chg"].fillna(0) >= 9.5) & (~df["is_suspended"])
            df["is_limit_down"] = (df["pct_chg"].fillna(0) <= -9.5) & (~df["is_suspended"])

            return (code, True, "", df)

        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1.5 * attempt)

    return (code, False, last_error, pd.DataFrame())


def save_stock_data(code: str, df: pd.DataFrame) -> None:
    """
    保存股票数据到Parquet文件

    Args:
        code: 股票代码（如 'sh.600000'）
        df: 数据DataFrame
    """
    stock_code = code.split(".")[1]
    file_path = RAW_DATA_DIR / f"{stock_code}.parquet"
    df.to_parquet(file_path, index=False)


def download_all_stocks_parallel(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8,
    max_retries: int = 3,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    多线程并行下载所有股票数据

    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        max_workers: 最大线程数
        max_retries: 每只股票最大重试次数

    Returns:
        (成功列表, 失败列表[(股票代码, 错误信息)])
    """
    if not stock_codes:
        print("股票列表为空，无数据可下载")
        return [], []

    existing_files = set()
    for parquet_file in RAW_DATA_DIR.glob("*.parquet"):
        code = parquet_file.stem
        existing_files.add(code)

    codes_to_download = []
    for code in stock_codes:
        stock_code = code.split(".")[1]
        if stock_code not in existing_files:
            codes_to_download.append(code)

    if not codes_to_download:
        print("所有股票数据已存在，无需下载")
        return [c.split(".")[1] for c in stock_codes], []

    print(f"总股票数: {len(stock_codes)}")
    print(f"已下载: {len(existing_files)}")
    print(f"待下载: {len(codes_to_download)}")
    print(f"并发线程数: {max_workers}")
    print("-" * 50)

    success_list: List[str] = []
    failed_list: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                download_single_stock, code, start_date, end_date, max_retries
            ): code
            for code in codes_to_download
        }

        with tqdm(total=len(codes_to_download), desc="下载进度") as pbar:
            for future in as_completed(futures):
                code, success, error_msg, df = future.result()
                if success and not df.empty:
                    save_stock_data(code, df)
                    success_list.append(code.split(".")[1])
                else:
                    failed_list.append((code.split(".")[1], error_msg))
                pbar.update(1)

    return success_list, failed_list


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="使用Baostock下载A股日线数据")
    parser.add_argument(
        "--start-date",
        default="2014-01-01",
        help="开始日期 (默认: 2014-01-01)",
    )
    parser.add_argument(
        "--end-date",
        default="2024-12-31",
        help="结束日期 (默认: 2024-12-31)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="并发线程数 (默认: 8)",
    )
    parser.add_argument(
        "--all-stocks",
        action="store_true",
        help="下载全部A股（而非仅存续股票）",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("A股日线数据下载工具（Baostock版）")
    print("=" * 50)
    print(f"时间范围: {args.start_date} 至 {args.end_date}")
    print(f"并发线程: {args.workers}")
    print()

    login_bs()

    try:
        if args.all_stocks:
            print("正在获取全部A股代码...")
            stock_codes = get_all_stock_codes()
        else:
            stock_codes = get_surviving_stock_codes_from_cache(
                start_date=args.start_date,
                end_date=args.end_date,
            )

        success_list, failed_list = download_all_stocks_parallel(
            stock_codes=stock_codes,
            start_date=args.start_date,
            end_date=args.end_date,
            max_workers=args.workers,
        )

        print()
        print("=" * 50)
        print("下载完成统计")
        print("=" * 50)
        print(f"成功: {len(success_list)}")
        print(f"失败: {len(failed_list)}")

        if failed_list:
            print()
            print("失败股票列表:")
            for code, error in failed_list[:10]:
                print(f"  {code}: {error}")
            if len(failed_list) > 10:
                print(f"  ... 还有 {len(failed_list) - 10} 只股票失败")

            fail_path = META_DATA_DIR / "download_failed_codes.txt"
            with open(fail_path, "w", encoding="utf-8") as f:
                for code, error in failed_list:
                    f.write(f"{code}\t{error}\n")
            print(f"\n失败记录已保存到: {fail_path}")

        print()
        print(f"数据存储位置: {RAW_DATA_DIR}")

    finally:
        logout_bs()


if __name__ == "__main__":
    main()
