"""
テスト: tests/test_prompts.py
対象: app/ai/prompts.py の build_messages() テスト
"""

from app.ai.prompts import build_messages


class TestBuildMessages:
    """build_messages() のユニットテスト。"""

    def test_basic_structure(self) -> None:
        """基本的なメッセージ構造が正しいこと。"""
        messages = build_messages(
            chat_history=[],
            player_message="図書館へ向かう",
            character_summary="田中一郎 HP:10/10",
            memories=[],
        )
        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "図書館へ向かう"

    def test_character_summary_in_system(self) -> None:
        """キャラクター情報がシステムプロンプトに含まれること。"""
        messages = build_messages(
            chat_history=[],
            player_message="行動する",
            character_summary="山田花子 HP:8/10",
            memories=[],
        )
        assert "山田花子" in messages[0]["content"]

    def test_memories_appended(self) -> None:
        """記憶がシステムプロンプトに追加されること。"""
        messages = build_messages(
            chat_history=[],
            player_message="行動する",
            character_summary="PC",
            memories=["怪物を目撃した", "日誌を発見した"],
        )
        system = messages[0]["content"]
        assert "怪物を目撃した" in system
        assert "日誌を発見した" in system

    def test_no_memories_no_section(self) -> None:
        """記憶がない場合は記憶セクションが追加されないこと。"""
        messages = build_messages(
            chat_history=[],
            player_message="行動する",
            character_summary="PC",
            memories=[],
        )
        assert "重要な記憶" not in messages[0]["content"]

    def test_chat_history_included(self) -> None:
        """会話履歴がメッセージに含まれること。"""
        history = [
            {"role": "user", "content": "前の行動"},
            {"role": "assistant", "content": "GMの応答"},
        ]
        messages = build_messages(
            chat_history=history,
            player_message="新しい行動",
            character_summary="PC",
            memories=[],
        )
        # system + 2件の履歴 + user
        assert len(messages) == 4
        assert messages[1]["content"] == "前の行動"
        assert messages[2]["content"] == "GMの応答"
        assert messages[3]["content"] == "新しい行動"

    def test_scenario_none_no_scenario_section(self) -> None:
        """scenario=None の場合はシナリオセクションが含まれないこと（後方互換性）。"""
        messages = build_messages(
            chat_history=[],
            player_message="行動する",
            character_summary="PC",
            memories=[],
            scenario=None,
        )
        assert "シナリオ情報" not in messages[0]["content"]

    def test_scenario_injected_into_system(self) -> None:
        """scenario が渡された場合はシステムプロンプトに注入されること。"""
        scenario = {
            "id": "test",
            "title": "テストシナリオ",
            "synopsis": "テスト用のあらすじ",
            "objective": "テストの目標",
            "era": "1924年",
            "climax": "クライマックス条件",
            "characters": [
                {
                    "id": "npc1",
                    "name": "テストNPC",
                    "role": "ally",
                    "description": "テストキャラ",
                    "secret": "秘密の情報",
                }
            ],
            "locations": [
                {
                    "id": "loc1",
                    "name": "テスト場所",
                    "description": "場所の説明",
                    "clues": ["手がかり1", "手がかり2"],
                }
            ],
            "gm_instructions": "GM追加指示内容",
        }
        messages = build_messages(
            chat_history=[],
            player_message="行動する",
            character_summary="PC",
            memories=[],
            scenario=scenario,
        )
        system = messages[0]["content"]
        assert "テストシナリオ" in system
        assert "テスト用のあらすじ" in system
        assert "テストの目標" in system
        assert "クライマックス条件" in system
        assert "テストNPC" in system
        assert "秘密の情報" in system
        assert "テスト場所" in system
        assert "手がかり1" in system
        assert "GM追加指示内容" in system

    def test_scenario_no_characters_no_error(self) -> None:
        """characters フィールドなしのシナリオでもエラーが出ないこと。"""
        scenario = {
            "id": "minimal",
            "title": "最小シナリオ",
            "synopsis": "あらすじ",
            "objective": "目標",
            "locations": [],
            "gm_instructions": "指示",
        }
        messages = build_messages(
            chat_history=[],
            player_message="行動",
            character_summary="PC",
            memories=[],
            scenario=scenario,
        )
        system = messages[0]["content"]
        assert "最小シナリオ" in system

    def test_scenario_clues_without_clues_field(self) -> None:
        """clues フィールドなしのロケーションでもエラーが出ないこと。"""
        scenario = {
            "id": "test",
            "title": "テスト",
            "synopsis": "あらすじ",
            "objective": "目標",
            "locations": [
                {
                    "id": "loc1",
                    "name": "場所",
                    "description": "説明",
                    # clues フィールドなし
                }
            ],
            "gm_instructions": "指示",
        }
        messages = build_messages(
            chat_history=[],
            player_message="行動",
            character_summary="PC",
            memories=[],
            scenario=scenario,
        )
        system = messages[0]["content"]
        assert "場所" in system
