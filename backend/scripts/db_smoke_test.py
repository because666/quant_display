import sqlite3
from datetime import date

from src.database.database import SessionLocal
from src.database.models import AIAdvice, ShadowAccount, Stock


def inspect_tables() -> None:
    conn = sqlite3.connect("data/app.db")
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    print("tables:", [name for (name,) in rows])


def orm_crud_smoke() -> None:
    db = SessionLocal()
    try:
        stock = Stock(stock_code="000001.SZ", stock_name="平安银行", listing_date=date(1991, 4, 3))
        db.add(stock)

        account = ShadowAccount(
            account_name="demo_account_001",
            holdings=[{"code": "000001", "name": "平安银行", "quantity": 100, "cost": 12.5}],
        )
        db.add(account)
        db.commit()

        advice = AIAdvice(
            account_id=account.id,
            advice_markdown="测试建议",
            top_stocks=["000001.SZ"],
            context_snapshot={"note": "smoke"},
        )
        db.add(advice)
        db.commit()

        account_in_db = db.query(ShadowAccount).filter_by(account_name="demo_account_001").first()
        print("account_found:", account_in_db is not None)

        db.delete(advice)
        db.delete(account)
        db.delete(stock)
        db.commit()
        print("crud_smoke: ok")
    finally:
        db.close()


if __name__ == "__main__":
    inspect_tables()
    orm_crud_smoke()
