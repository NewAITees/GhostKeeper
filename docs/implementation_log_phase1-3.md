# 実装ログ: Phase 1〜3（バックエンド基盤・ゲームロジック・AI連携）

## 実施日時
2026-02-27

---

## 完了タスク

### Phase 1: バックエンド基盤
- [x] `backend/app/` ディレクトリ構成作成（api/, game/, ai/, models/）
- [x] 依存パッケージ追加: uvicorn, aiosqlite, pytest, pytest-asyncio, httpx, ollama
- [x] `app/config.py` 実装（Pydantic Settings、.env 対応）
- [x] `app/database.py` 実装（SQLAlchemy async engine、get_db、init_db）
- [x] `app/models/session.py` 実装（GameSession, ScenarioMode）
- [x] `app/models/character.py` 実装（Character、CoC 7版全パラメータ）
- [x] `app/models/memory.py` 実装（Memory）
- [x] `app/models/chat.py` 実装（ChatHistory, MessageRole）
- [x] `app/main.py` 実装（CORS・静的配信・ルーター登録・lifespan DB初期化）
- [x] 旧 `backend/main.py` をコメントのみに変更（移行済み案内）

### Phase 2: ゲームロジック
- [x] `app/game/dice.py` 実装（DiceResult dataclass、roll()、roll_d100()）
- [x] `app/game/rules.py` 実装（skill_check、calc_derived_stats、san_check、ダメージボーナステーブル）
- [x] `app/game/stats.py` 実装（apply_stat_delta、get/set_stat_field、build_character_summary）
- [x] `tests/test_dice.py` 実装（11テスト）
- [x] `tests/test_rules.py` 実装（28テスト）

### Phase 3: AI連携
- [x] `app/ai/schemas.py` 実装（AIResponse、NpcDialogue、DiceRequest、StatUpdate、ImageRef）
- [x] `app/ai/tools.py` 実装（TOOLS定義 7ツール）
- [x] `app/ai/prompts.py` 実装（SYSTEM_PROMPT、build_messages）
- [x] `app/ai/client.py` 実装（GmClient、Tool Useループ、thinking タグ除去、パース失敗フォールバック）
- [x] `app/api/sessions.py` 実装（CRUD + PC自動生成）
- [x] `app/api/chat.py` 実装（ツールハンドラー統合、Ollama未起動時503対応）
- [x] `app/api/characters.py` 実装（キャラクター詳細・部分更新）
- [x] `app/api/images.py` 実装（フォルダスキャン）

---

## 変更ファイル一覧

### 新規作成
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/api/__init__.py`
- `backend/app/api/sessions.py`
- `backend/app/api/chat.py`
- `backend/app/api/characters.py`
- `backend/app/api/images.py`
- `backend/app/game/__init__.py`
- `backend/app/game/dice.py`
- `backend/app/game/rules.py`
- `backend/app/game/stats.py`
- `backend/app/ai/__init__.py`
- `backend/app/ai/schemas.py`
- `backend/app/ai/tools.py`
- `backend/app/ai/prompts.py`
- `backend/app/ai/client.py`
- `backend/app/models/__init__.py`
- `backend/app/models/session.py`
- `backend/app/models/character.py`
- `backend/app/models/memory.py`
- `backend/app/models/chat.py`
- `backend/tests/__init__.py`
- `backend/tests/test_dice.py`
- `backend/tests/test_rules.py`

### 変更
- `backend/main.py`（旧コードを移行済みコメントに変更）
- `backend/pyproject.toml`（依存パッケージ追加）
- `tasks/todo.md`（Phase 1〜4 チェックボックス更新）
- `tasks/lessons.md`（Phase 1〜3 実装での学び追記）

---

## テスト結果

```
============================= test session starts ==============================
collected 39 items

tests/test_dice.py::TestRollNotation::test_simple_d100 PASSED
tests/test_dice.py::TestRollNotation::test_2d6_plus_3 PASSED
tests/test_dice.py::TestRollNotation::test_1d3 PASSED
tests/test_dice.py::TestRollNotation::test_d6_without_count PASSED
tests/test_dice.py::TestRollNotation::test_modifier_negative PASSED
tests/test_dice.py::TestRollNotation::test_total_is_sum_plus_modifier PASSED
tests/test_dice.py::TestRollNotation::test_invalid_notation_raises PASSED
tests/test_dice.py::TestRollNotation::test_dataclass_fields PASSED
tests/test_dice.py::TestRollNotation::test_1d100_range PASSED
tests/test_dice.py::TestRollD100::test_range PASSED
tests/test_dice.py::TestRollD100::test_returns_int PASSED
tests/test_rules.py::TestSkillCheck::* (11 tests) PASSED
tests/test_rules.py::TestCalcDerivedStats::* (10 tests) PASSED
tests/test_rules.py::TestSanCheck::* (5 tests) PASSED

39 passed in 0.03s
```

## 静的解析結果

- `uv run ruff check .` : All checks passed
- `uv run mypy .` : Success: no issues found in 27 source files

---

## 注意事項・設計判断

1. `ollama-python` は `httpx<0.27` 依存で競合するため `ollama` 本家パッケージに切り替えた
2. `calc_derived_stats` 返り値を `TypedDict` (`DerivedStats`) にして mypy 型安全を確保
3. Ollama 未起動時は `httpx.ConnectError` をキャッチして HTTP 503 を返す（サーバー起動は正常）
4. Qwen3 の `<think>...</think>` タグは正規表現で除去してから JSON パース
5. パース失敗時は `gm_narration` のみの最小 `AIResponse` にフォールバック
