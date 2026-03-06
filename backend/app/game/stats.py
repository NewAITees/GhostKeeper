"""
モジュール名: game/stats.py
目的: キャラクターパラメータ操作ヘルパー

使い方:
    from app.game.stats import apply_stat_delta, build_character_summary

    new_hp = apply_stat_delta(current=8, delta=-3, max_val=10, min_val=0)
    summary = build_character_summary(character)

依存:
    - app.models.character.Character

注意:
    - apply_stat_delta は 0〜max_val にクランプして返す
    - build_character_summary は LLM に渡す文字列を生成する
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.character import Character

logger = logging.getLogger(__name__)


def apply_stat_delta(current: int, delta: int, max_val: int, min_val: int = 0) -> int:
    """
    現在値に delta を加算し、[min_val, max_val] にクランプして返す。

    >>> apply_stat_delta(8, -3, 10)
    5
    >>> apply_stat_delta(2, -5, 10)
    0
    """
    new_val = current + delta
    clamped = max(min_val, min(max_val, new_val))
    logger.debug(
        "apply_stat_delta: %d + %d = %d (clamped to %d)",
        current,
        delta,
        new_val,
        clamped,
    )
    return clamped


def get_stat_field(character: "Character", field: str) -> tuple[int, int]:
    """
    field ("hp"|"san"|"mp") に対応する (current, max) を返す。
    """
    if field == "hp":
        return character.hp_current, character.hp_max
    elif field == "san":
        return character.san_current, character.san_max
    elif field == "mp":
        return character.mp_current, character.mp_max
    else:
        raise ValueError(f"Unknown stat field: {field!r}")


def set_stat_field(character: "Character", field: str, new_current: int) -> None:
    """
    field に対応する現在値を更新する（in-place）。
    """
    if field == "hp":
        character.hp_current = new_current
    elif field == "san":
        character.san_current = new_current
    elif field == "mp":
        character.mp_current = new_current
    else:
        raise ValueError(f"Unknown stat field: {field!r}")


def build_character_summary(character: "Character") -> str:
    """
    LLM に渡すキャラクター情報の文字列サマリーを生成する。
    """
    skill_lines = []
    skills: dict = character.skills or {}  # type: ignore[assignment]
    for skill_name, skill_data in skills.items():
        if isinstance(skill_data, dict):
            current = skill_data.get("current", skill_data.get("base", 0))
            skill_lines.append(f"  {skill_name}: {current}")

    role = "PC" if character.is_pc else "NPC"
    lines = [
        f"[{role}] {character.name} (id={character.id})",
        f"  STR={character.str_} CON={character.con} SIZ={character.siz}"
        f" INT={character.int_} DEX={character.dex}"
        f" POW={character.pow_} APP={character.app} EDU={character.edu} LUK={character.luk}",
        f"  HP={character.hp_current}/{character.hp_max}"
        f"  MP={character.mp_current}/{character.mp_max}"
        f"  SAN={character.san_current}/{character.san_max}",
    ]
    if skill_lines:
        lines.append("  スキル:")
        lines.extend(skill_lines)
    return "\n".join(lines)
