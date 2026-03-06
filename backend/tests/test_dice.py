"""
テスト: tests/test_dice.py
対象: app/game/dice.py のユニット・統合テスト
"""

import pytest

from app.game.dice import DiceResult, roll, roll_d100


class TestRollNotation:
    """ダイス記法パースのテスト。"""

    def test_simple_d100(self) -> None:
        result = roll("1d100")
        assert result.notation == "1d100"
        assert len(result.rolls) == 1
        assert 1 <= result.rolls[0] <= 100
        assert result.modifier == 0
        assert result.total == result.rolls[0]

    def test_2d6_plus_3(self) -> None:
        result = roll("2d6+3")
        assert len(result.rolls) == 2
        assert result.modifier == 3
        for r in result.rolls:
            assert 1 <= r <= 6
        assert result.total == sum(result.rolls) + 3

    def test_1d3(self) -> None:
        for _ in range(20):
            result = roll("1d3")
            assert 1 <= result.total <= 3

    def test_d6_without_count(self) -> None:
        """個数省略 → 1 個扱い。"""
        result = roll("d6")
        assert len(result.rolls) == 1
        assert 1 <= result.total <= 6

    def test_modifier_negative(self) -> None:
        result = roll("2d6-2")
        assert result.modifier == -2
        assert result.total == sum(result.rolls) - 2

    def test_total_is_sum_plus_modifier(self) -> None:
        for _ in range(50):
            result = roll("3d6+5")
            assert result.total == sum(result.rolls) + 5

    def test_invalid_notation_raises(self) -> None:
        with pytest.raises(ValueError):
            roll("invalid")

    def test_dataclass_fields(self) -> None:
        result = roll("1d6")
        assert isinstance(result, DiceResult)
        assert isinstance(result.rolls, list)
        assert isinstance(result.modifier, int)
        assert isinstance(result.total, int)

    def test_1d100_range(self) -> None:
        """1d100 の範囲テスト（多数回試行）。"""
        for _ in range(200):
            result = roll("1d100")
            assert 1 <= result.total <= 100


class TestRollD100:
    """roll_d100() 関数のテスト。"""

    def test_range(self) -> None:
        for _ in range(100):
            value = roll_d100()
            assert 1 <= value <= 100

    def test_returns_int(self) -> None:
        assert isinstance(roll_d100(), int)
