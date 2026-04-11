"""将旧表 shadow_accounts / ai_advices 中的数据迁移到 shadow_account / ai_advice（保留主键与关联）。"""

from sqlalchemy import inspect, text

from src.database.database import engine


def migrate_legacy_shadow_ai_tables() -> tuple[int, int]:
    """
    若新表为空且存在旧表，则复制数据。
    返回 (已迁移 shadow_account 行数, 已迁移 ai_advice 行数)。
    """
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "shadow_account" not in tables:
        return (0, 0)
    with engine.begin() as conn:
        n_new = conn.execute(text("SELECT COUNT(*) FROM shadow_account")).scalar_one()
        if n_new > 0:
            return (0, 0)
        if "shadow_accounts" not in tables:
            return (0, 0)
        n_old = conn.execute(text("SELECT COUNT(*) FROM shadow_accounts")).scalar_one()
        if n_old == 0:
            return (0, 0)
        conn.execute(
            text(
                """
                INSERT INTO shadow_account (
                    id, account_name, created_at, updated_at,
                    holdings, backtest_start, backtest_end, prediction_start, prediction_end
                )
                SELECT
                    id,
                    COALESCE(NULLIF(TRIM(COALESCE(account_name, '')), ''), account_id),
                    created_at, updated_at,
                    holdings_json,
                    backtest_start_date, backtest_end_date,
                    prediction_start_date, prediction_end_date
                FROM shadow_accounts
                """
            )
        )
        advice_migrated = 0
        if "ai_advices" in tables and "ai_advice" in tables:
            n_adv_old = conn.execute(text("SELECT COUNT(*) FROM ai_advices")).scalar_one()
            if n_adv_old > 0:
                conn.execute(
                    text(
                        """
                        INSERT INTO ai_advice (
                            id, account_id, request_time,
                            advice_markdown, top_stocks, context_snapshot
                        )
                        SELECT
                            a.id, s.id, a.request_time,
                            a.response_content, a.related_stocks, '{}'
                        FROM ai_advices a
                        JOIN shadow_accounts s ON a.account_id = s.account_id
                        """
                    )
                )
                advice_migrated = n_adv_old
        return (n_old, advice_migrated)
