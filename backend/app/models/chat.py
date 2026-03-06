"""
モジュール名: models/chat.py
目的: チャット履歴 SQLAlchemy モデル定義

使い方:
    from app.models.chat import ChatHistory, MessageRole

依存:
    - sqlalchemy
    - app.database.Base

注意:
    - raw_ai_response にはAIのJSON生出力を保存（デバッグ用）
    - role: player=プレイヤー入力, gm=AI応答, system=システムメッセージ
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageRole(str, enum.Enum):
    player = "player"
    gm = "gm"
    system = "system"


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["GameSession"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="chat_history"
    )
