"""
使用 Baostock 稳定版下载A股历史日线数据
- 单线程顺序下载，避免并发错误
- 自动重试机制
- 支持断点续传
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import baostock as bs
import pandas as pd
from tqdm import tqdm

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
META_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "meta"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
META_DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_stock_list_from_cache() -> List[str]:
    """从缓存读取股票池"""
    cache_path = META_DATA_DIR / "surviving_stocks_20140101_20241231.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        codes = df["code"].astype(str).tolist()
        print(f"从缓存读取股票池: {len(codes)} 只股票")
        return codes
    raise FileNotFoundError("股票池缓存文件不存在")


def download_single_stock_bs(code: str, start_date: str, end_date: str, max_retries: int = 5) -> Tuple[bool, str, pd.DataFrame]:
    """
    使用Baostock下载单只股票数据

    Args:
        code: 股票代码（如 '000001'）
        start_date: 开始日期
        end_date: 结束日期
        max_retries: 最大重试次数

    Returns:
        (是否成功, 错误信息, 数据DataFrame)
    """
    market = "sh" if code.startswith("6") else "sz"
    bs_code = f"{market}.{code}"

    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",
            )

            if rs.error_code != "0":
                last_error = f"Baostock错误[{attempt}]: {rs.error_msg}"
                if attempt < max_retries:
                    time.sleep(2 * attempt)
                continue

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return False, "数据为空", pd.DataFrame()

            df = pd.DataFrame(data_list, columns=rs.fields)

            for col in ["date", "open", "high", "low", "close", "volume", "amount", "pctChg"]:
                if col in df.columns:
                    if col == "date":
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                    else:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.rename(columns={"pctChg": "pct_chg"})
            df["stock_code"] = code
            df = df.sort_values("date").reset_index(drop=True)

            return True, "", df

        except Exception as e:
            last_error = f"异常[{attempt}]: {str(e)}"
            if attempt < max_retries:
                time.sleep(2 * attempt)

    return False, last_error, pd.DataFrame()


def process_and_save(code: str, df: pd.DataFrame) -> None:
    """处理并保存数据"""
    prev_close = df["close"].shift(1)
    df["is_suspended"] = (
        (df["volume"].fillna(0) == 0) & prev_close.notna() & (df["close"] == prev_close)
    )
    df["is_limit_up"] = (df["pct_chg"].fillna(0) >= 9.5) & (~df["is_suspended"])
    df["is_limit_down"] = (df["pct_chg"].fillna(0) <= -9.5) & (~df["is_suspended"])

    file_path = RAW_DATA_DIR / f"{code}.parquet"
    df.to_parquet(file_path, index=False)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Baostock稳定版A股数据下载")
    parser.add_argument("--start-date", default="2014-01-01")
    parser.add_argument("--end-date", default="2024-12-31")
    parser.add_argument("--delay", type=float, default=0.8)
    args = parser.parse_args()

    print("=" * 60)
    print("  A股日线数据下载工具（Baostock稳定版）")
    print("=" * 60)
    print(f"时间范围: {args.start_date} ~ {args.end_date}")
    print(f"请求间隔: {args.delay}秒")
    print()

    lg = bs.login()
    if lg.error_code != "0":
        print(f"❌ Baostock登录失败: {lg.error_msg}")
        return
    print("✅ Baostock登录成功")

    try:
        stock_codes = get_stock_list_from_cache()

        existing = set(p.stem for p in RAW_DATA_DIR.glob("*.parquet"))
        to_download = [c for c in stock_codes if c not in existing]

        print(f"\n📊 统计信息:")
        print(f"   总股票数: {len(stock_codes)}")
        print(f"   已下载: {len(existing)}")
        print(f"   待下载: {len(to_download)}")
        print()

        if not to_download:
            print("✅ 所有数据已下载完成！")
            return

        success_count = 0
        fail_count = 0
        failed_codes = []

        print("开始下载...")
        for i, code in enumerate(tqdm(to_download, desc="下载进度"), 1):
            success, error_msg, df = download_single_stock_bs(
                code, args.start_date, args.end_date
            )

            if success and not df.empty:
                process_and_save(code, df)
                success_count += 1
            else:
                fail_count += 1
                failed_codes.append((code, error_msg))

            time.sleep(args.delay)

            if i % 50 == 0:
                print(f"\n  📈 进度: {i}/{len(to_download)} | 成功: {success_count} | 失败: {fail_count}")

        print("\n" + "=" * 60)
        print("  下载完成统计")
        print("=" * 60)
        print(f"  ✅ 成功: {success_count}")
        print(f"  ❌ 失败: {fail_count}")

        if failed_codes:
            print(f"\n  失败股票列表（前10个）:")
            for c, e in failed_codes[:10]:
                print(f"    {c}: {e}")
            if len(failed_codes) > 10:
                print(f"    ... 还有 {len(failed_codes) - 10} 只")

            with open(META_DATA_DIR / "download_failed.txt", "w", encoding="utf-8") as f:
                for c, e in failed_codes:
                    f.write(f"{c}\t{e}\n")
            print(f"\n  失败记录已保存到: {META_DATA_DIR / 'download_failed.txt'}")

        print(f"\n  📁 数据存储位置: {RAW_DATA_DIR}")

    finally:
        bs.logout()
        print("\n✅ Baostock已登出")


if __name__ == "__main__":
    main()
