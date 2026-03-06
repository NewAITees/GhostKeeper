"""
モジュール名: models/session.py
目的: ゲームセッション SQLAlchemy モデル定義

使い方:
    from app.models.session import GameSession, ScenarioMode

依存:
    - sqlalchemy
    - app.database.Base

注意:
    - relationships は lazy="select"（デフォルト）
    - cascade="all, delete-orphan" で関連レコードを連鎖削除
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScenarioMode(str, enum.Enum):
    template = "template"
    free = "free"


class GameSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[ScenarioMode] = mapped_column(
        SAEnum(ScenarioMode), default=ScenarioMode.free
    )
    scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    scenario_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_location: Mapped[str | None] = mapped_column(String, nullable=True)
    # AI がシーンを進める際に現在地を更新する

    characters: Mapped[list["Character"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )
    memories: Mapped[list["Memory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )
    chat_history: Mapped[list["ChatHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )
