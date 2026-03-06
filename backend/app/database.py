"""
モジュール名: database.py
目的: SQLAlchemy 非同期エンジン・セッション管理

使い方:
    from app.database import get_db, init_db, Base

    # FastAPI依存性注入
    async def endpoint(db: AsyncSession = Depends(get_db)):
        ...

    # 起動時テーブル作成
    await init_db()

依存:
    - sqlalchemy
    - aiosqlite

注意:
    - aiosqlite バックエンドを使用（非同期専用）
    - Base.metadata.create_all() はモデルがインポートされた後に呼び出すこと
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依存性注入用のDBセッションジェネレータ。"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """全テーブルを作成する（モデルが事前にインポートされている必要あり）。"""
    logger.info("init_db: creating tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("init_db: done")
