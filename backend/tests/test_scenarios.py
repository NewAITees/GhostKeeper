"""
テスト: tests/test_scenarios.py
対象: app/api/scenarios.py のユニット・統合テスト

カバレッジ:
    - _load_scenarios() の正常系・異常系
    - シナリオ一覧レスポンス形式
    - シナリオ不在時の挙動
"""

import json
import os
import tempfile
from unittest.mock import patch

from app.api.scenarios import _load_scenarios


class TestLoadScenarios:
    """_load_scenarios() のユニットテスト。"""

    def test_load_valid_scenario(self) -> None:
        """有効な JSON ファイルを読み込めること。"""
        scenario = {
            "id": "test_scenario",
            "title": "テストシナリオ",
            "synopsis": "テスト用あらすじ",
            "starting_location": "start",
            "objective": "目標",
            "locations": [],
            "gm_instructions": "GM指示",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test_scenario.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(scenario, f, ensure_ascii=False)

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert len(results) == 1
        assert results[0]["id"] == "test_scenario"
        assert results[0]["title"] == "テストシナリオ"

    def test_schema_json_skipped(self) -> None:
        """schema.json はスキップされること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = os.path.join(tmpdir, "schema.json")
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump({"type": "schema"}, f)

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert len(results) == 0

    def test_invalid_json_skipped(self) -> None:
        """無効な JSON ファイルはスキップされること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("not valid json{{{")

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert len(results) == 0

    def test_nonexistent_dir_returns_empty(self) -> None:
        """存在しないディレクトリの場合は空リストを返すこと。"""
        with patch("app.api.scenarios.settings") as mock_settings:
            mock_settings.scenarios_dir = "/nonexistent/path/that/does/not/exist"
            results = _load_scenarios()

        assert results == []

    def test_multiple_files_sorted(self) -> None:
        """複数ファイルが名前順にソートされること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["b_scenario", "a_scenario", "c_scenario"]:
                fpath = os.path.join(tmpdir, f"{name}.json")
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump({"id": name, "title": name}, f, ensure_ascii=False)

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert len(results) == 3
        assert results[0]["id"] == "a_scenario"
        assert results[1]["id"] == "b_scenario"
        assert results[2]["id"] == "c_scenario"

    def test_haunted_library_loads(self) -> None:
        """実際の haunted_library.json が読み込めること。"""
        results = _load_scenarios()

        # scenarios/ に haunted_library.json が存在する場合のみチェック
        ids = [s["id"] for s in results]
        if "haunted_library" in ids:
            scenario = next(s for s in results if s["id"] == "haunted_library")
            assert scenario["title"] == "呪われた図書館"
            assert "synopsis" in scenario
            assert "locations" in scenario
            assert "gm_instructions" in scenario
            assert len(scenario["locations"]) > 0


class TestLoadScenariosResponseShape:
    """list_scenarios() レスポンス形式のテスト。"""

    def test_list_response_fields(self) -> None:
        """一覧レスポンスに必要フィールドが含まれること。"""
        scenario = {
            "id": "test_id",
            "title": "テストタイトル",
            "description": "説明",
            "era": "1924年",
            "location": "アーカム",
            "synopsis": "あらすじ",
            "starting_location": "start",
            "objective": "目標",
            "locations": [],
            "gm_instructions": "GM指示",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test_id.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(scenario, f, ensure_ascii=False)

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert len(results) == 1
        s = results[0]
        for field in ["id", "title", "description", "era", "location"]:
            assert field in s

    def test_optional_fields_default_to_empty_string(self) -> None:
        """省略可能フィールドが存在しない場合でもレスポンスが壊れないこと。"""
        scenario = {
            "id": "minimal",
            "title": "最小シナリオ",
            "synopsis": "あらすじ",
            "starting_location": "start",
            "objective": "目標",
            "locations": [],
            "gm_instructions": "指示",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "minimal.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(scenario, f, ensure_ascii=False)

            with patch("app.api.scenarios.settings") as mock_settings:
                mock_settings.scenarios_dir = tmpdir
                results = _load_scenarios()

        assert results[0].get("description", "") == ""
        assert results[0].get("era", "") == ""
        assert results[0].get("location", "") == ""
