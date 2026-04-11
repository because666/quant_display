"""影子账户 account 模块。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.models import AIAdvice, ShadowAccount  # noqa: F401 — 注册表

from src import account as acc


@pytest.fixture
def isolated_account_session(tmp_path, monkeypatch):
    db_path = tmp_path / "acct.db"
    url = f"sqlite:///{db_path.as_posix()}"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    monkeypatch.setattr(acc, "SessionLocal", factory)
    yield factory
    eng.dispose()


def test_create_get_update_delete(isolated_account_session) -> None:
    r = acc.create_account("user_a", holdings=[{"code": "000001", "name": "平安银行", "quantity": 100, "cost": 10.0}])
    assert r.ok and r.value
    aid = r.value["id"]

    g = acc.get_account(aid)
    assert g.ok and g.value["account_name"] == "user_a"
    assert g.value["holdings"][0]["code"] == "000001"

    u = acc.update_holdings(aid, [{"code": "600000", "name": "浦发银行", "quantity": 1, "cost": 7.5}])
    assert u.ok and u.value["holdings"][0]["code"] == "600000"

    rng = acc.update_ranges(aid, None, None, None, None)
    assert rng.ok

    d = acc.delete_account(aid)
    assert d.ok
    assert not acc.get_account(aid).ok


def test_duplicate_name(isolated_account_session) -> None:
    assert acc.create_account("dup").ok
    r2 = acc.create_account("dup")
    assert not r2.ok
    assert r2.error_code == acc.E_DUPLICATE_ACCOUNT_NAME


def test_max_accounts(isolated_account_session, monkeypatch) -> None:
    monkeypatch.setattr(acc, "MAX_SHADOW_ACCOUNTS", 2)
    assert acc.create_account("m1").ok
    assert acc.create_account("m2").ok
    r = acc.create_account("m3")
    assert not r.ok
    assert r.error_code == acc.E_MAX_ACCOUNTS_EXCEEDED


def test_invalid_holdings(isolated_account_session) -> None:
    r = acc.create_account("bad", holdings=[{"code": "x"}])
    assert not r.ok
    assert r.error_code == acc.E_INVALID_HOLDINGS


def test_list_accounts_warning_when_too_many(isolated_account_session) -> None:
    s = isolated_account_session()
    for i in range(11):
        s.add(ShadowAccount(account_name=f"warn_{i}", holdings=[]))
    s.commit()
    s.close()
    out = acc.list_accounts()
    assert out["total_count"] == 11
    assert out["warning"] is not None
