"""
モジュール名: models/memory.py
目的: セッション記憶（重要イベント） SQLAlchemy モデル定義

使い方:
    from app.models.memory import Memory

依存:
    - sqlalchemy
    - app.database.Base

注意:
    - importance は 1〜5 の整数（高いほど重要）
    - GMが add_memory ツールで明示的に追加する
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["GameSession"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="memories"
    )
