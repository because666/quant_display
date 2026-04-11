"""
使用 finshare 多数据源下载A股历史日线数据
优势：支持多数据源（东方财富、腾讯、新浪、通达信、BaoStock），自动故障切换
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from tqdm import tqdm

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
META_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "meta"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
META_DATA_DIR.mkdir(parents=True, exist_ok=True)

import finshare as fs


def get_stock_list_from_cache(
    start_date: str = "2014-01-01",
    end_date: str = "2024-12-31",
) -> List[str]:
    """
    从缓存文件读取存续股票代码

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        存续股票代码列表（格式如 ['000001.SZ', '600000.SH']）
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
                codes.append(f"{code}.SH")
            else:
                codes.append(f"{code}.SZ")
        print(f"存续股票数量: {len(codes)}")
        return codes

    raise FileNotFoundError(f"股票池缓存文件不存在: {cache_path}")


def download_single_stock(
    code: str,
    start_date: str,
    end_date: str,
    max_retries: int = 5,
) -> Tuple[str, bool, str, pd.DataFrame]:
    """
    下载单只股票日线数据

    Args:
        code: 股票代码（如 '000001.SZ'）
        start_date: 开始日期（如 '2014-01-01'）
        end_date: 结束日期（如 '2024-12-31'）
        max_retries: 最大重试次数

    Returns:
        (股票代码, 是否成功, 错误信息, 数据DataFrame)
    """
    last_error: str = ""

    for attempt in range(1, max_retries + 1):
        try:
            df = fs.get_historical_data(
                code,
                start=start_date,
                end=end_date,
                adjust="qfq",
            )

            if df is None or df.empty:
                return (code, False, "数据为空", pd.DataFrame())

            df = df.reset_index()

            df = df.rename(columns={
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            })

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            stock_code = code.split(".")[0]
            df["stock_code"] = stock_code

            if "amount" not in df.columns:
                df["amount"] = df["close"] * df["volume"]
            if "turnover" not in df.columns:
                df["turnover"] = float("nan")
            if "pct_chg" not in df.columns:
                df["pct_chg"] = df["close"].pct_change() * 100

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
                time.sleep(2 * attempt)

    return (code, False, last_error, pd.DataFrame())


def save_stock_data(code: str, df: pd.DataFrame) -> None:
    """
    保存股票数据到Parquet文件

    Args:
        code: 股票代码（如 '000001.SZ'）
        df: 数据DataFrame
    """
    stock_code = code.split(".")[0]
    file_path = RAW_DATA_DIR / f"{stock_code}.parquet"
    df.to_parquet(file_path, index=False)


def download_all_stocks(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    max_retries: int = 5,
    delay: float = 0.5,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    下载所有股票数据（顺序下载，避免触发限流）

    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        max_retries: 每只股票最大重试次数
        delay: 每次请求间隔（秒）

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
        stock_code = code.split(".")[0]
        if stock_code not in existing_files:
            codes_to_download.append(code)

    if not codes_to_download:
        print("所有股票数据已存在，无需下载")
        return [c.split(".")[0] for c in stock_codes], []

    print(f"总股票数: {len(stock_codes)}")
    print(f"已下载: {len(existing_files)}")
    print(f"待下载: {len(codes_to_download)}")
    print(f"请求间隔: {delay}秒")
    print("-" * 50)

    success_list: List[str] = []
    failed_list: List[Tuple[str, str]] = []

    for code in tqdm(codes_to_download, desc="下载进度"):
        code_result, success, error_msg, df = download_single_stock(
            code, start_date, end_date, max_retries
        )
        if success and not df.empty:
            save_stock_data(code, df)
            success_list.append(code.split(".")[0])
        else:
            failed_list.append((code.split(".")[0], error_msg))

        time.sleep(delay)

    return success_list, failed_list


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="使用finshare下载A股日线数据")
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
        "--delay",
        type=float,
        default=0.5,
        help="请求间隔秒数 (默认: 0.5)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="单只股票最大重试次数 (默认: 5)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("A股日线数据下载工具（finshare多数据源版）")
    print("=" * 50)
    print(f"时间范围: {args.start_date} 至 {args.end_date}")
    print(f"请求间隔: {args.delay}秒")
    print()

    stock_codes = get_stock_list_from_cache(
        start_date=args.start_date,
        end_date=args.end_date,
    )

    success_list, failed_list = download_all_stocks(
        stock_codes=stock_codes,
        start_date=args.start_date,
        end_date=args.end_date,
        max_retries=args.max_retries,
        delay=args.delay,
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


if __name__ == "__main__":
    main()
