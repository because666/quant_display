"""
使用多数据源下载A股历史日线数据
数据源优先级：网易财经 > 腾讯财经
"""
from __future__ import annotations

import sys
import time
from io import StringIO
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import requests
from tqdm import tqdm

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
META_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "meta"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
META_DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://finance.sina.com.cn",
}


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
        存续股票代码列表（格式如 ['000001', '600000']）
    """
    slug_start = start_date.replace("-", "")
    slug_end = end_date.replace("-", "")
    cache_path = META_DATA_DIR / f"surviving_stocks_{slug_start}_{slug_end}.parquet"

    if cache_path.exists():
        print(f"从缓存读取股票池: {cache_path}")
        df = pd.read_parquet(cache_path)
        codes = df["code"].astype(str).tolist()
        print(f"存续股票数量: {len(codes)}")
        return codes

    raise FileNotFoundError(f"股票池缓存文件不存在: {cache_path}")


def download_from_netease(code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """
    从网易财经下载历史数据

    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        数据DataFrame或None
    """
    try:
        market = "0" if code.startswith("6") else "1"
        full_code = f"{market}{code}"

        start_str = start_date.replace("-", "")
        end_str = end_date.replace("-", "")

        url = "http://quotes.money.163.com/service/chddata.html"
        params = {
            "code": full_code,
            "start": start_str,
            "end": end_str,
            "fields": "TCLOSE;HIGH;LOW;TOPEN;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER",
        }

        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None

        df = pd.read_csv(StringIO(r.text), encoding="gbk")

        if df.empty:
            return None

        df = df.rename(columns={
            "日期": "date",
            "开盘价": "open",
            "最高价": "high",
            "最低价": "low",
            "收盘价": "close",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "pct_chg",
        })

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["open", "high", "low", "close", "volume", "amount", "pct_chg"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["stock_code"] = code

        cols = ["date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "stock_code"]
        df = df[[c for c in cols if c in df.columns]]

        return df

    except Exception:
        return None


def download_from_tencent(code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """
    从腾讯财经下载历史数据

    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        数据DataFrame或None
    """
    try:
        market = "sh" if code.startswith("6") else "sz"
        full_code = f"{market}{code}"

        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            "_var": f"kline_{full_code}",
            "param": f"{full_code},day,,320,qfq",
            "r": str(int(time.time() * 1000)),
        }

        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None

        json_data = r.json()
        if not json_data or "data" not in json_data:
            return None

        stock_data = json_data["data"].get(full_code, {})
        day_data = stock_data.get("day", [])

        if not day_data:
            return None

        df = pd.DataFrame(day_data, columns=["date", "open", "close", "high", "low", "volume", "amount"])

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["stock_code"] = code
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

        return df

    except Exception:
        return None


def download_single_stock(
    code: str,
    start_date: str,
    end_date: str,
) -> Tuple[str, bool, str, pd.DataFrame]:
    """
    下载单只股票日线数据（尝试多个数据源）

    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        (股票代码, 是否成功, 错误信息, 数据DataFrame)
    """
    sources = [
        ("网易财经", download_from_netease),
        ("腾讯财经", download_from_tencent),
    ]

    for source_name, download_func in sources:
        try:
            df = download_func(code, start_date, end_date)
            if df is not None and not df.empty:
                return (code, True, f"数据源: {source_name}", df)
        except Exception:
            continue

    return (code, False, "所有数据源均失败", pd.DataFrame())


def process_and_save_data(code: str, df: pd.DataFrame) -> None:
    """
    处理并保存股票数据

    Args:
        code: 股票代码
        df: 原始数据DataFrame
    """
    df = df.sort_values("date").reset_index(drop=True)

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

    file_path = RAW_DATA_DIR / f"{code}.parquet"
    df.to_parquet(file_path, index=False)


def download_all_stocks(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    delay: float = 0.5,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    下载所有股票数据

    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        delay: 请求间隔（秒）

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

    codes_to_download = [code for code in stock_codes if code not in existing_files]

    if not codes_to_download:
        print("所有股票数据已存在，无需下载")
        return stock_codes, []

    print(f"总股票数: {len(stock_codes)}")
    print(f"已下载: {len(existing_files)}")
    print(f"待下载: {len(codes_to_download)}")
    print(f"请求间隔: {delay}秒")
    print("-" * 50)

    success_list: List[str] = []
    failed_list: List[Tuple[str, str]] = []

    for code in tqdm(codes_to_download, desc="下载进度"):
        _, success, msg, df = download_single_stock(code, start_date, end_date)
        if success and not df.empty:
            process_and_save_data(code, df)
            success_list.append(code)
        else:
            failed_list.append((code, msg))

        time.sleep(delay)

    return success_list, failed_list


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="使用多数据源下载A股日线数据")
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
    args = parser.parse_args()

    print("=" * 50)
    print("A股日线数据下载工具（多数据源版）")
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
