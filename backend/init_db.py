from src.database.database import Base, engine
from src.database.migrate_legacy_shadow_ai import migrate_legacy_shadow_ai_tables
from src.database.models import AIAdvice, BacktestResult, FactorData, ShadowAccount, Stock  # noqa: F401


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    sa_n, adv_n = migrate_legacy_shadow_ai_tables()
    if sa_n or adv_n:
        print(f"Migrated legacy shadow/AI tables: shadow_account={sa_n}, ai_advice={adv_n}.")
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_database()
