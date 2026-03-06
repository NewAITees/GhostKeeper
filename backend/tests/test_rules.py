"""
テスト: tests/test_rules.py
対象: app/game/rules.py のユニット・統合テスト

注意:
    - skill_check はランダムダイスを使うため、unittest.mock.patch でロールを固定する
"""

from unittest.mock import patch

from app.game.rules import (
    SkillCheckResult,
    calc_derived_stats,
    san_check,
    skill_check,
)


class TestSkillCheck:
    """skill_check() のテスト（ダイス目を mock で固定）。"""

    def _check_with_roll(
        self, skill_value: int, rolled: int, difficulty: str = "normal"
    ) -> SkillCheckResult:
        with patch("app.game.rules.roll_d100", return_value=rolled):
            return skill_check(skill_value, difficulty).result

    # --- Critical ---
    def test_skill_check_critical(self) -> None:
        """ロール 1 → クリティカル（技能値に依らない）。"""
        assert self._check_with_roll(50, 1) == SkillCheckResult.CRITICAL

    def test_skill_check_critical_low_skill(self) -> None:
        assert self._check_with_roll(10, 1) == SkillCheckResult.CRITICAL

    # --- Fumble ---
    def test_skill_check_fumble_skill_lt50(self) -> None:
        """技能値 < 50 → 96 以上でファンブル。"""
        assert self._check_with_roll(49, 96) == SkillCheckResult.FUMBLE
        assert self._check_with_roll(49, 100) == SkillCheckResult.FUMBLE

    def test_skill_check_fumble_skill_ge50(self) -> None:
        """技能値 >= 50 → 100 のみファンブル。"""
        assert self._check_with_roll(50, 100) == SkillCheckResult.FUMBLE
        # 96〜99 はファンブルではない
        assert self._check_with_roll(50, 96) != SkillCheckResult.FUMBLE

    # --- Extreme Success ---
    def test_skill_check_extreme(self) -> None:
        """技能値の 1/5 以下（かつ 1 より大）でイクストリーム成功。"""
        # skill=50 → threshold_extreme=10
        assert self._check_with_roll(50, 2) == SkillCheckResult.EXTREME
        assert self._check_with_roll(50, 10) == SkillCheckResult.EXTREME

    # --- Hard Success ---
    def test_skill_check_hard(self) -> None:
        """技能値の 1/2 以下（1/5 超）でハード成功。"""
        # skill=50 → threshold_hard=25, threshold_extreme=10
        assert self._check_with_roll(50, 11) == SkillCheckResult.HARD
        assert self._check_with_roll(50, 25) == SkillCheckResult.HARD

    # --- Normal Success ---
    def test_skill_check_success(self) -> None:
        """技能値以下（1/2 超）で通常成功。"""
        # skill=50 → success range: 26〜50
        assert self._check_with_roll(50, 26) == SkillCheckResult.SUCCESS
        assert self._check_with_roll(50, 50) == SkillCheckResult.SUCCESS

    # --- Failure ---
    def test_skill_check_failure(self) -> None:
        """技能値超（かつファンブルでない）で失敗。"""
        assert self._check_with_roll(50, 51) == SkillCheckResult.FAILURE
        assert self._check_with_roll(50, 95) == SkillCheckResult.FAILURE

    # --- Difficulty ---
    def test_skill_check_hard_difficulty(self) -> None:
        """hard difficulty は実効技能値を 1/2 に変更。skill=60 → effective=30。"""
        # rolled=30 なら hard difficulty では成功（threshold_hard=15 以下でハード）
        result = self._check_with_roll(60, 30, "hard")
        assert result == SkillCheckResult.SUCCESS

    def test_skill_check_extreme_difficulty(self) -> None:
        """extreme difficulty は実効技能値を 1/5 に変更。skill=60 → effective=12。"""
        # rolled=13 なら失敗
        result = self._check_with_roll(60, 13, "extreme")
        assert result == SkillCheckResult.FAILURE


class TestCalcDerivedStats:
    """calc_derived_stats() のテスト。"""

    def test_hp_calculation(self) -> None:
        """HP = floor((CON + SIZ) / 10)。"""
        stats = calc_derived_stats(str_=50, con=50, siz=60, pow_=50)
        assert stats["hp_max"] == (50 + 60) // 10  # 11

    def test_mp_calculation(self) -> None:
        """MP = floor(POW / 5)。"""
        stats = calc_derived_stats(str_=50, con=50, siz=50, pow_=55)
        assert stats["mp_max"] == 55 // 5  # 11

    def test_san_calculation(self) -> None:
        """SAN = POW * 5。"""
        stats = calc_derived_stats(str_=50, con=50, siz=50, pow_=60)
        assert stats["san_max"] == 60 * 5  # 300

    def test_damage_bonus_zero(self) -> None:
        """STR+SIZ = 85〜124 → ダメージボーナス 0。"""
        stats = calc_derived_stats(str_=50, con=50, siz=50, pow_=50)
        assert stats["damage_bonus"] == "0"
        assert stats["build"] == 0

    def test_damage_bonus_minus2(self) -> None:
        """STR+SIZ = 2〜64 → ダメージボーナス -2。"""
        stats = calc_derived_stats(str_=30, con=50, siz=30, pow_=50)
        assert stats["damage_bonus"] == "-2"
        assert stats["build"] == -2

    def test_damage_bonus_minus1(self) -> None:
        """STR+SIZ = 65〜84 → ダメージボーナス -1。"""
        stats = calc_derived_stats(str_=35, con=50, siz=35, pow_=50)
        assert stats["damage_bonus"] == "-1"

    def test_damage_bonus_plus1d4(self) -> None:
        """STR+SIZ = 125〜164 → ダメージボーナス +1d4。"""
        stats = calc_derived_stats(str_=70, con=50, siz=60, pow_=50)
        assert stats["damage_bonus"] == "+1d4"
        assert stats["build"] == 1

    def test_damage_bonus_plus2d6(self) -> None:
        """STR+SIZ >= 205 → ダメージボーナス +2d6。"""
        stats = calc_derived_stats(str_=110, con=50, siz=100, pow_=50)
        assert stats["damage_bonus"] == "+2d6"
        assert stats["build"] == 3

    def test_mov_both_lt_siz(self) -> None:
        """DEX < SIZ かつ STR < SIZ → MOV = 7。"""
        stats = calc_derived_stats(str_=40, con=50, siz=60, pow_=50, dex=40)
        assert stats["mov"] == 7

    def test_mov_both_gt_siz(self) -> None:
        """DEX > SIZ かつ STR > SIZ → MOV = 9。"""
        stats = calc_derived_stats(str_=70, con=50, siz=60, pow_=50, dex=70)
        assert stats["mov"] == 9

    def test_mov_default(self) -> None:
        """それ以外 → MOV = 8。"""
        stats = calc_derived_stats(str_=60, con=50, siz=60, pow_=50, dex=40)
        assert stats["mov"] == 8

    def test_mov_age_reduction(self) -> None:
        """40歳以上は MOV -1。"""
        young = calc_derived_stats(str_=70, con=50, siz=60, pow_=50, dex=70, age=25)
        old = calc_derived_stats(str_=70, con=50, siz=60, pow_=50, dex=70, age=40)
        assert old["mov"] == young["mov"] - 1

    def test_all_keys_present(self) -> None:
        """返り値に必須キーが全て含まれる。"""
        stats = calc_derived_stats(str_=50, con=50, siz=50, pow_=50)
        for key in ("hp_max", "mp_max", "san_max", "damage_bonus", "build", "mov"):
            assert key in stats


class TestSanCheck:
    """san_check() のテスト。"""

    def test_success_fixed_loss(self) -> None:
        """成功時の固定値喪失。"""
        with patch("app.game.rules.roll_d100", return_value=20):
            result_detail = skill_check(50)
        loss = san_check(50, "1", "1d6", result_detail.result)
        assert loss == 1

    def test_failure_fixed_loss(self) -> None:
        """失敗時の固定値喪失。"""
        with patch("app.game.rules.roll_d100", return_value=99):
            result_detail = skill_check(49)  # 99 >= 96 → FUMBLE
        loss = san_check(50, "1", "3", result_detail.result)
        assert loss == 3

    def test_loss_capped_at_current_san(self) -> None:
        """喪失量は現在SANを超えない。"""
        with patch("app.game.rules.roll_d100", return_value=99):
            result_detail = skill_check(49)
        loss = san_check(2, "1", "5", result_detail.result)
        assert loss == 2  # SAN=2 なので最大2

    def test_loss_nonnegative(self) -> None:
        """喪失量は非負。"""
        with patch("app.game.rules.roll_d100", return_value=20):
            result_detail = skill_check(50)
        loss = san_check(50, "0", "0", result_detail.result)
        assert loss == 0

    def test_dice_notation_loss(self) -> None:
        """dice 記法での喪失量（1d6 形式）。"""
        with patch("app.game.rules.roll_d100", return_value=99):
            result_detail = skill_check(49)
        # 1d6 の期待値は 1〜6
        with patch("app.game.dice.random.randint", return_value=4):
            loss = san_check(50, "1", "1d6", result_detail.result)
        assert loss == 4
