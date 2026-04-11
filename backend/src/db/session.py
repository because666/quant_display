from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

from .models import Base

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url
    rest = url[len("sqlite:///") :]
    if rest.startswith("./") or (not rest.startswith("/") and ":" not in rest[:3]):
        path = (_BACKEND_ROOT / rest.lstrip("./")).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return url


def reset_engine() -> None:
    """释放全局 Engine（单测切换 database_url 前调用）。"""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        raw = get_settings().database_url
        url = _normalize_sqlite_url(raw)
        _engine = create_engine(url, echo=False, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        logger.debug("SQLAlchemy engine: %s", url)
    return _engine


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    eng = get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
