"""
モジュール名: models/character.py
目的: キャラクター（PC・NPC） SQLAlchemy モデル定義（CoC 7版全パラメータ）

使い方:
    from app.models.character import Character

依存:
    - sqlalchemy
    - app.database.Base

注意:
    - str_ / int_ / pow_ はSQLの予約語回避のため末尾にアンダースコア
    - skills は JSON カラム: {"技能名": {"base": int, "current": int, "growth": bool}}
    - is_pc=True がプレイヤーキャラクター
    - is_template=True かつ session_id=None → 事前作成テンプレートキャラクター
    - is_template=False かつ session_id=あり → セッション内コピー
"""

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_pc: Mapped[bool] = mapped_column(Boolean, default=False)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    image_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # テンプレートキャラクター用フィールド
    occupation: Mapped[str | None] = mapped_column(String, nullable=True)
    backstory: Mapped[str | None] = mapped_column(Text, nullable=True)  # 経歴・背景

    # NPC用フィールド
    personality: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # NPCの個性・話し方
    npc_memory: Mapped[dict] = mapped_column(JSON, default=dict)  # type: ignore[type-arg]

    # 基本値（3d6×5 or 2d6+6×5）
    str_: Mapped[int] = mapped_column("str", Integer, default=50)
    con: Mapped[int] = mapped_column(Integer, default=50)
    siz: Mapped[int] = mapped_column(Integer, default=50)
    int_: Mapped[int] = mapped_column("int", Integer, default=50)
    dex: Mapped[int] = mapped_column(Integer, default=50)
    pow_: Mapped[int] = mapped_column("pow", Integer, default=50)
    app: Mapped[int] = mapped_column(Integer, default=50)
    edu: Mapped[int] = mapped_column(Integer, default=50)
    luk: Mapped[int] = mapped_column(Integer, default=50)

    # 派生値（現在値）
    hp_max: Mapped[int] = mapped_column(Integer, default=10)
    hp_current: Mapped[int] = mapped_column(Integer, default=10)
    mp_max: Mapped[int] = mapped_column(Integer, default=10)
    mp_current: Mapped[int] = mapped_column(Integer, default=10)
    san_max: Mapped[int] = mapped_column(Integer, default=50)
    san_current: Mapped[int] = mapped_column(Integer, default=50)
    san_indefinite: Mapped[int] = mapped_column(Integer, default=0)  # 不定の狂気閾値

    # スキル: {"図書館": {"base": 25, "current": 45, "growth": False}, ...}
    skills: Mapped[dict] = mapped_column(JSON, default=dict)  # type: ignore[type-arg]

    session: Mapped["GameSession"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="characters"
    )
