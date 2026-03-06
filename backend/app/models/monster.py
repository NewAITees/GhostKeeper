"""
モジュール名: models/monster.py
目的: モンスター/NPC テンプレート SQLAlchemy モデル定義

使い方:
    from app.models.monster import MonsterTemplate

依存:
    - sqlalchemy
    - app.database.Base

注意:
    - id はスラッグ形式（例: "the_presence", "william_morse"）
    - セッション作成時にこのテンプレートから Character(is_pc=False) を生成する
    - hp_max は CoC 派生式を使わず直接指定（モンスター固有の値を持つため）
    - san_loss_success / san_loss_failure はダイス記法文字列（例: "1" / "1d6"）
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MonsterTemplate(Base):
    __tablename__ = "monster_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String, default="monster")  # monster/neutral/ally
    image_id: Mapped[str | None] = mapped_column(String, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 基本値（不要なものはデフォルト50）
    str_: Mapped[int] = mapped_column("str", Integer, default=50)
    con: Mapped[int] = mapped_column(Integer, default=50)
    siz: Mapped[int] = mapped_column(Integer, default=50)
    int_: Mapped[int] = mapped_column("int", Integer, default=50)
    dex: Mapped[int] = mapped_column(Integer, default=50)
    pow_: Mapped[int] = mapped_column("pow", Integer, default=50)

    # HP（派生ではなく直接指定）
    hp_max: Mapped[int] = mapped_column(Integer, default=10)

    # 戦闘スキル {"格闘（拳）": 50, "回避": 30, ...}
    skills: Mapped[dict] = mapped_column(JSON, default=dict)  # type: ignore[type-arg]

    # 戦闘パラメータ
    damage_bonus: Mapped[str] = mapped_column(String, default="0")  # "1d4", "0" など
    armor: Mapped[int] = mapped_column(Integer, default=0)  # 装甲値

    # SAN 喪失（成功/失敗時のダイス記法）
    san_loss_success: Mapped[str] = mapped_column(String, default="0")
    san_loss_failure: Mapped[str] = mapped_column(String, default="1d6")

    # 出典シナリオ（再利用時の参考）
    source_scenario: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
