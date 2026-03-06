"""
モジュール名: game/rules.py
目的: CoC 7版ゲームルール（技能判定・派生値計算・SANチェック）

使い方:
    from app.game.rules import skill_check, calc_derived_stats, san_check

    detail = skill_check(45)
    stats = calc_derived_stats(str_=60, con=50, siz=55, pow_=55, dex=60)
    san_loss = san_check(50, "1", "1d6", detail.result)

依存:
    - app.game.dice

注意:
    - ファンブル条件: 技能値 < 50 → 96以上, 技能値 >= 50 → 100のみ
    - difficulty="hard" は実効技能値を half に変更、"extreme" は 1/5 に変更
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from app.game.dice import roll, roll_d100

logger = logging.getLogger(__name__)


class SkillCheckResult(str, Enum):
    CRITICAL = "critical"
    EXTREME = "extreme_success"
    HARD = "hard_success"
    SUCCESS = "success"
    FAILURE = "failure"
    FUMBLE = "fumble"


@dataclass
class SkillCheckDetail:
    result: SkillCheckResult
    rolled: int
    skill_value: int
    threshold_critical: int = 1
    threshold_extreme: int = 0
    threshold_hard: int = 0


def skill_check(skill_value: int, difficulty: str = "normal") -> SkillCheckDetail:
    """
    CoC 7版技能判定。

    difficulty:
        "normal"  - 技能値そのままで判定
        "hard"    - 実効技能値を skill_value // 2 で判定
        "extreme" - 実効技能値を skill_value // 5 で判定

    ファンブル条件:
        技能値 < 50 → ロール 96 以上
        技能値 >= 50 → ロール 100 のみ
    """
    logger.info("skill_check: skill_value=%d, difficulty=%s", skill_value, difficulty)

    effective: int
    if difficulty == "hard":
        effective = skill_value // 2
    elif difficulty == "extreme":
        effective = skill_value // 5
    else:
        effective = skill_value

    rolled = roll_d100()
    threshold_extreme = effective // 5
    threshold_hard = effective // 2

    fumble_threshold = 95 if skill_value < 50 else 99

    result: SkillCheckResult
    if rolled == 1:
        result = SkillCheckResult.CRITICAL
    elif rolled > fumble_threshold:
        result = SkillCheckResult.FUMBLE
    elif rolled <= threshold_extreme:
        result = SkillCheckResult.EXTREME
    elif rolled <= threshold_hard:
        result = SkillCheckResult.HARD
    elif rolled <= effective:
        result = SkillCheckResult.SUCCESS
    else:
        result = SkillCheckResult.FAILURE

    detail = SkillCheckDetail(
        result=result,
        rolled=rolled,
        skill_value=skill_value,
        threshold_critical=1,
        threshold_extreme=threshold_extreme,
        threshold_hard=threshold_hard,
    )
    logger.info("skill_check result: rolled=%d, result=%s", rolled, result)
    return detail


# ダメージボーナス / ビルド テーブル（CoC 7版）
_DB_TABLE: list[tuple[int, int, str, int]] = [
    # (min_sum, max_sum, damage_bonus, build)
    (2, 64, "-2", -2),
    (65, 84, "-1", -1),
    (85, 124, "0", 0),
    (125, 164, "+1d4", 1),
    (165, 204, "+1d6", 2),
    (205, 9999, "+2d6", 3),
]


def _calc_damage_bonus(str_: int, siz: int) -> tuple[str, int]:
    """STR + SIZ からダメージボーナスとビルドを返す。"""
    total = str_ + siz
    for min_s, max_s, db, build in _DB_TABLE:
        if min_s <= total <= max_s:
            return db, build
    return "+2d6", 3


class DerivedStats(TypedDict):
    hp_max: int
    mp_max: int
    san_max: int
    damage_bonus: str
    build: int
    mov: int


def calc_derived_stats(
    str_: int,
    con: int,
    siz: int,
    pow_: int,
    dex: int = 50,
    age: int = 25,
) -> DerivedStats:
    """
    CoC 7版 派生値を計算して辞書で返す。

    返り値キー:
        hp_max, mp_max, san_max, damage_bonus, build, mov
    """
    logger.debug(
        "calc_derived_stats: STR=%d CON=%d SIZ=%d POW=%d DEX=%d age=%d",
        str_,
        con,
        siz,
        pow_,
        dex,
        age,
    )
    hp_max = (con + siz) // 10
    mp_max = pow_ // 5
    san_max = pow_ * 5

    damage_bonus, build = _calc_damage_bonus(str_, siz)

    # MOV テーブル
    if dex < siz and str_ < siz:
        mov = 7
    elif dex > siz and str_ > siz:
        mov = 9
    else:
        mov = 8
    if age >= 40:
        mov -= 1

    result: DerivedStats = {
        "hp_max": hp_max,
        "mp_max": mp_max,
        "san_max": san_max,
        "damage_bonus": damage_bonus,
        "build": build,
        "mov": mov,
    }
    logger.debug("calc_derived_stats result: %s", result)
    return result


def san_check(
    san_current: int,
    success_loss: str,
    failure_loss: str,
    roll_result: SkillCheckResult,
) -> int:
    """
    SANチェック。成功/失敗に応じたSAN喪失量を返す（正の整数）。

    success_loss, failure_loss は "1" や "1d6" 形式。
    """
    logger.info(
        "san_check: san=%d, success_loss=%s, failure_loss=%s, roll=%s",
        san_current,
        success_loss,
        failure_loss,
        roll_result,
    )
    is_success = roll_result in (
        SkillCheckResult.CRITICAL,
        SkillCheckResult.EXTREME,
        SkillCheckResult.HARD,
        SkillCheckResult.SUCCESS,
    )

    loss_notation = success_loss if is_success else failure_loss

    # 固定値の場合はそのまま整数化
    try:
        loss = int(loss_notation)
    except ValueError:
        loss = roll(loss_notation).total

    loss = max(0, loss)
    result = min(loss, san_current)
    logger.info("san_check: loss=%d (capped at %d)", result, san_current)
    return result
