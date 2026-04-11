"""
多线程股票数据下载脚本
使用多线程并发下载，大幅提升下载速度
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import pandas as pd
from tqdm import tqdm

from src.data_fetcher import (
    META_DATA_DIR,
    RAW_DATA_DIR,
    cache_daily_data,
    download_daily_data,
)
from src.stock_pool import get_surviving_stocks


def download_single_stock(
    code: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
) -> Tuple[str, bool, str]:
    """
    下载单只股票数据

    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        max_retries: 最大重试次数

    Returns:
        (股票代码, 是否成功, 错误信息)
    """
    last_error: str = ""

    for attempt in range(1, max_retries + 1):
        try:
            df = download_daily_data(code, start_date, end_date)
            if df.empty:
                return (code, False, "数据为空")

            cache_daily_data(code, df)
            return (code, True, "")
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1.5 * attempt)

    return (code, False, last_error)


def download_all_stocks_parallel(
    stock_list: pd.DataFrame,
    start_date: str,
    end_date: str,
    max_workers: int = 8,
    max_retries: int = 3,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    多线程并发下载所有股票数据

    Args:
        stock_list: 股票列表DataFrame
        start_date: 开始日期
        end_date: 结束日期
        max_workers: 最大线程数
        max_retries: 每只股票最大重试次数

    Returns:
        (成功列表, 失败列表[(股票代码, 错误信息)])
    """
    if stock_list.empty:
        print("股票列表为空，无数据可下载")
        return [], []

    codes = stock_list["code"].astype(str).tolist()

    existing_files = set()
    for parquet_file in RAW_DATA_DIR.glob("*.parquet"):
        code = parquet_file.stem
        existing_files.add(code)

    codes_to_download = [code for code in codes if code not in existing_files]

    if not codes_to_download:
        print("所有股票数据已存在，无需下载")
        return codes, []

    print(f"总股票数: {len(codes)}")
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
                code, success, error_msg = future.result()
                if success:
                    success_list.append(code)
                else:
                    failed_list.append((code, error_msg))
                pbar.update(1)

    return success_list, failed_list


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="多线程股票数据下载工具")
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
        "--refresh-pool",
        action="store_true",
        help="重新生成股票池缓存",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("股票数据下载工具（多线程版）")
    print("=" * 50)
    print(f"时间范围: {args.start_date} 至 {args.end_date}")
    print(f"并发线程: {args.workers}")
    print()

    print("正在获取股票池...")
    stock_list = get_surviving_stocks(
        start_date=args.start_date,
        end_date=args.end_date,
        refresh_cache=args.refresh_pool,
    )
    print(f"股票池大小: {len(stock_list)}")
    print()

    success_list, failed_list = download_all_stocks_parallel(
        stock_list=stock_list,
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


if __name__ == "__main__":
    main()
