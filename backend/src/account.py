"""
影子账户管理：CRUD、持仓替换、时间区间更新；无鉴权，以 account_name 区分用户（最多 10 个账户）。

数据库：`shadow_account` / `ai_advice`（删除账户时 ORM + 外键 CASCADE 清除关联建议）。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.database.database import SessionLocal
from src.database.models import AIAdvice, ShadowAccount

logger = logging.getLogger(__name__)

MAX_SHADOW_ACCOUNTS = 10

# 错误码（API/脚本可据此展示）
E_DUPLICATE_ACCOUNT_NAME = "DUPLICATE_ACCOUNT_NAME"
E_ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
E_MAX_ACCOUNTS_EXCEEDED = "MAX_ACCOUNTS_EXCEEDED"
E_INVALID_HOLDINGS = "INVALID_HOLDINGS"
E_INVALID_ACCOUNT_NAME = "INVALID_ACCOUNT_NAME"
E_DATABASE_ERROR = "DATABASE_ERROR"

T = TypeVar("T")


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    """统一结果：成功时 ok=True 且 value 非空；失败时 error_code + message。"""

    ok: bool
    value: T | None = None
    error_code: str | None = None
    message: str = ""

    @staticmethod
    def success(val: T) -> ServiceResult[T]:
        return ServiceResult(ok=True, value=val)

    @staticmethod
    def failure(code: str, message: str) -> ServiceResult[T]:
        return ServiceResult(ok=False, error_code=code, message=message)


@contextmanager
def _session_scope() -> Any:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _normalize_account_name(name: str) -> str:
    s = (name or "").strip()
    return s


def _validate_account_name(name: str) -> ServiceResult[None]:
    n = _normalize_account_name(name)
    if not n:
        return ServiceResult.failure(E_INVALID_ACCOUNT_NAME, "账户名不能为空")
    if len(n) > 128:
        return ServiceResult.failure(E_INVALID_ACCOUNT_NAME, "账户名长度不能超过 128")
    return ServiceResult.success(None)


def _validate_holdings(holdings: list[dict[str, Any]] | None) -> ServiceResult[list[dict[str, Any]]]:
    if holdings is None:
        return ServiceResult.success([])
    if not isinstance(holdings, list):
        return ServiceResult.failure(E_INVALID_HOLDINGS, "holdings 必须为列表")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(holdings):
        if not isinstance(item, dict):
            return ServiceResult.failure(E_INVALID_HOLDINGS, f"持仓第 {i} 项必须为对象")
        for key in ("code", "name", "quantity", "cost"):
            if key not in item:
                return ServiceResult.failure(
                    E_INVALID_HOLDINGS,
                    f"持仓第 {i} 项缺少字段: {key}（需包含 code, name, quantity, cost）",
                )
        code = str(item["code"]).strip()
        name = str(item["name"]).strip()
        try:
            qty = float(item["quantity"])
            cost = float(item["cost"])
        except (TypeError, ValueError):
            return ServiceResult.failure(E_INVALID_HOLDINGS, f"持仓第 {i} 项 quantity/cost 必须为数字")
        out.append({"code": code, "name": name, "quantity": qty, "cost": cost})
    return ServiceResult.success(out)


def _account_to_dict(acc: ShadowAccount, *, include_holdings: bool = True) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": acc.id,
        "account_name": acc.account_name,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
        "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
        "backtest_start": acc.backtest_start.isoformat() if acc.backtest_start else None,
        "backtest_end": acc.backtest_end.isoformat() if acc.backtest_end else None,
        "prediction_start": acc.prediction_start.isoformat() if acc.prediction_start else None,
        "prediction_end": acc.prediction_end.isoformat() if acc.prediction_end else None,
    }
    if include_holdings:
        d["holdings"] = acc.holdings if isinstance(acc.holdings, list) else list(acc.holdings or [])
    return d


def create_account(
    account_name: str,
    holdings: list[dict[str, Any]] | None = None,
    backtest_range: tuple[date | None, date | None] | None = None,
    prediction_range: tuple[date | None, date | None] | None = None,
) -> ServiceResult[dict[str, Any]]:
    """
    创建影子账户。account_name 全库唯一（去首尾空格后比较）。
    backtest_range / prediction_range 为 (start, end)，可为 None 表示不设区间。
    """
    vn = _validate_account_name(account_name)
    if not vn.ok:
        return ServiceResult.failure(vn.error_code or E_INVALID_ACCOUNT_NAME, vn.message)

    name = _normalize_account_name(account_name)
    vh = _validate_holdings(holdings)
    if not vh.ok or vh.value is None:
        return ServiceResult.failure(vh.error_code or E_INVALID_HOLDINGS, vh.message)

    bs = be = ps = pe = None
    if backtest_range is not None:
        bs, be = backtest_range
    if prediction_range is not None:
        ps, pe = prediction_range

    try:
        with _session_scope() as session:
            n = session.scalar(select(func.count()).select_from(ShadowAccount))
            if n is not None and int(n) >= MAX_SHADOW_ACCOUNTS:
                logger.warning("创建账户被拒绝：已达上限 %s", MAX_SHADOW_ACCOUNTS)
                return ServiceResult.failure(
                    E_MAX_ACCOUNTS_EXCEEDED,
                    f"影子账户最多 {MAX_SHADOW_ACCOUNTS} 个",
                )

            exists = session.scalars(select(ShadowAccount).where(ShadowAccount.account_name == name)).first()
            if exists is not None:
                logger.info("创建账户失败，名称已存在: %s", name)
                return ServiceResult.failure(E_DUPLICATE_ACCOUNT_NAME, "账户名已存在")

            acc = ShadowAccount(
                account_name=name,
                holdings=vh.value,
                backtest_start=bs,
                backtest_end=be,
                prediction_start=ps,
                prediction_end=pe,
            )
            session.add(acc)
            session.flush()
            logger.info("已创建影子账户 id=%s name=%s", acc.id, name)
            return ServiceResult.success(_account_to_dict(acc))
    except IntegrityError as exc:
        logger.warning("创建账户唯一约束冲突: %s", exc)
        return ServiceResult.failure(E_DUPLICATE_ACCOUNT_NAME, "账户名已存在")
    except SQLAlchemyError as exc:
        logger.exception("创建账户数据库错误: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def get_account(account_id: int) -> ServiceResult[dict[str, Any]]:
    """按主键查询，含持仓与其它字段。"""
    try:
        with _session_scope() as session:
            acc = session.get(ShadowAccount, account_id)
            if acc is None:
                return ServiceResult.failure(E_ACCOUNT_NOT_FOUND, f"账户不存在: id={account_id}")
            return ServiceResult.success(_account_to_dict(acc))
    except SQLAlchemyError as exc:
        logger.exception("查询账户失败: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def get_account_by_name(account_name: str) -> ServiceResult[dict[str, Any]]:
    name = _normalize_account_name(account_name)
    if not name:
        return ServiceResult.failure(E_INVALID_ACCOUNT_NAME, "账户名不能为空")
    try:
        with _session_scope() as session:
            acc = session.scalars(select(ShadowAccount).where(ShadowAccount.account_name == name)).first()
            if acc is None:
                return ServiceResult.failure(E_ACCOUNT_NOT_FOUND, f"账户不存在: {name}")
            return ServiceResult.success(_account_to_dict(acc))
    except SQLAlchemyError as exc:
        logger.exception("按名称查询账户失败: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def update_holdings(account_id: int, new_holdings: list[dict[str, Any]]) -> ServiceResult[dict[str, Any]]:
    """整体替换持仓（JSON 列表：code, name, quantity, cost）。"""
    vh = _validate_holdings(new_holdings)
    if not vh.ok or vh.value is None:
        return ServiceResult.failure(vh.error_code or E_INVALID_HOLDINGS, vh.message)

    try:
        with _session_scope() as session:
            acc = session.get(ShadowAccount, account_id)
            if acc is None:
                return ServiceResult.failure(E_ACCOUNT_NOT_FOUND, f"账户不存在: id={account_id}")
            acc.holdings = vh.value
            logger.info("已更新持仓 account_id=%s 条数=%s", account_id, len(vh.value))
            return ServiceResult.success(_account_to_dict(acc))
    except SQLAlchemyError as exc:
        logger.exception("更新持仓失败: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def update_ranges(
    account_id: int,
    backtest_start: date | None,
    backtest_end: date | None,
    prediction_start: date | None,
    prediction_end: date | None,
) -> ServiceResult[dict[str, Any]]:
    """更新四个日期字段；任一项可为 None 表示置空（未设置）。"""
    try:
        with _session_scope() as session:
            acc = session.get(ShadowAccount, account_id)
            if acc is None:
                return ServiceResult.failure(E_ACCOUNT_NOT_FOUND, f"账户不存在: id={account_id}")
            acc.backtest_start = backtest_start
            acc.backtest_end = backtest_end
            acc.prediction_start = prediction_start
            acc.prediction_end = prediction_end
            logger.info("已更新回测/预测区间 account_id=%s", account_id)
            return ServiceResult.success(_account_to_dict(acc))
    except SQLAlchemyError as exc:
        logger.exception("更新时间区间失败: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def delete_account(account_id: int) -> ServiceResult[None]:
    """删除账户；关联的 ai_advice 由数据库 ON DELETE CASCADE 一并删除。"""
    try:
        with _session_scope() as session:
            acc = session.get(ShadowAccount, account_id)
            if acc is None:
                return ServiceResult.failure(E_ACCOUNT_NOT_FOUND, f"账户不存在: id={account_id}")
            # 显式统计子表（日志）；实际删除依赖 FK CASCADE
            n_adv = session.scalar(
                select(func.count()).select_from(AIAdvice).where(AIAdvice.account_id == account_id)
            )
            session.delete(acc)
            logger.info("已删除影子账户 id=%s，级联 AI 建议约 %s 条", account_id, int(n_adv or 0))
            return ServiceResult.success(None)
    except SQLAlchemyError as exc:
        logger.exception("删除账户失败: %s", exc)
        return ServiceResult.failure(E_DATABASE_ERROR, str(exc))


def list_accounts() -> dict[str, Any]:
    """
    返回所有账户基本信息。若数据库中超过 10 条，仍全部返回并在 warning 中提示（正常情况创建端已限制为 10）。
    """
    try:
        with _session_scope() as session:
            rows = list(session.scalars(select(ShadowAccount).order_by(ShadowAccount.id)).all())
            total = len(rows)
            basics = [
                {
                    "id": r.id,
                    "account_name": r.account_name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]
    except SQLAlchemyError as exc:
        logger.exception("列出账户失败: %s", exc)
        return {
            "accounts": [],
            "total_count": 0,
            "warning": f"数据库错误: {exc}",
        }

    warning: str | None = None
    if total > MAX_SHADOW_ACCOUNTS:
        warning = f"当前共有 {total} 个账户，超过建议上限 {MAX_SHADOW_ACCOUNTS}，请清理或联系管理员"
        logger.warning("%s", warning)

    return {"accounts": basics, "total_count": total, "warning": warning}


def _main() -> None:
    """简单脚本自测：创建 → 更新持仓 → 查询 → 删除。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = create_account(
        "demo_shadow_cli",
        holdings=[{"code": "000001", "name": "平安银行", "quantity": 100, "cost": 12.5}],
    )
    print("create:", r)
    if not r.ok or not r.value:
        return
    aid = r.value["id"]
    print("get:", get_account(aid))
    print("update_holdings:", update_holdings(aid, [{"code": "600000", "name": "浦发银行", "quantity": 200, "cost": 8.0}]))
    print("list:", list_accounts())
    print("delete:", delete_account(aid))


if __name__ == "__main__":
    _main()
