"""
モジュール名: game/dice.py
目的: ダイスロールエンジン（CoC 7版対応）

使い方:
    from app.game.dice import roll, roll_d100, DiceResult

    result = roll("2d6+3")
    print(result.total)  # 各ダイスの目 + 修正値

    value = roll_d100()  # 1〜100 の整数

依存:
    - random (標準ライブラリ)
    - dataclasses

注意:
    - 対応記法: "NdM", "NdM+K", "NdM-K"（N=個数, M=面数, K=修正値）
    - N を省略した場合は 1 個扱い（例: "d6" -> "1d6"）
    - 修正値はダイス目の合計に加算
"""

import logging
import random
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_NOTATION_RE = re.compile(
    r"^(\d+)?d(\d+)(?:([+-])(\d+))?$",
    re.IGNORECASE,
)


@dataclass
class DiceResult:
    notation: str  # "2d6+3" 等
    rolls: list[int] = field(default_factory=list)  # 各ダイスの目
    modifier: int = 0  # 修正値
    total: int = 0


def roll(notation: str) -> DiceResult:
    """
    ダイス記法をパースしてロールする。

    対応記法: "1d100", "2d6+3", "1d3", "d6"
    返り値: DiceResult（rolls, modifier, total を含む）
    """
    logger.debug("roll called: notation=%s", notation)
    m = _NOTATION_RE.match(notation.strip())
    if not m:
        raise ValueError(f"Invalid dice notation: {notation!r}")

    count = int(m.group(1)) if m.group(1) else 1
    sides = int(m.group(2))
    sign = m.group(3)
    mod_value = int(m.group(4)) if m.group(4) else 0
    modifier = -mod_value if sign == "-" else mod_value

    if count < 1:
        raise ValueError(f"Dice count must be >= 1, got {count}")
    if sides < 1:
        raise ValueError(f"Dice sides must be >= 1, got {sides}")

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    result = DiceResult(notation=notation, rolls=rolls, modifier=modifier, total=total)
    logger.debug("roll result: %s -> %s (total=%d)", notation, rolls, total)
    return result


def roll_d100() -> int:
    """1d100 を振り、1〜100 の整数を返す。"""
    return random.randint(1, 100)
