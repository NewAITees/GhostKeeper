# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

GhostKeeper はクトゥルフ神話TRPG（CoC 7版）のシングルプレイヤー向けウェブアプリ。
ローカルLLM（Ollama）がGMと全NPCを担当し、プレイヤーはチャットで探索・行動を行う。

詳細な要件は `docs/requirements.md` を参照。タスク進捗は `tasks/todo.md`、過去の失敗は `tasks/lessons.md` を参照。

---

## コマンド早見表

### Backend（`backend/` ディレクトリで実行）

```bash
# 依存インストール
uv sync

# 開発サーバー起動（実装後）
uv run uvicorn app.main:app --reload --port 18000

# リント
uv run ruff check .
uv run ruff format .

# 型チェック
uv run mypy .

# テスト（実装後）
uv run pytest
uv run pytest tests/test_game.py::test_skill_check  # 単一テスト

# pre-commit
uv run pre-commit run --all-files
```

### Frontend（`frontend/` ディレクトリで実行）

```bash
npm install
npm run dev       # 開発サーバー（port 5173）
npm run build     # 本番ビルド
npm run lint      # ESLint
```

### Ollama

**環境メモ：OllamaはWSL2ではなくWindowsにインストール済み。**
WSL2からは `http://localhost:11434` でアクセス可能（ポートフォワーディング済み・curl動作確認済み）。
`ollama` コマンドはWSL2シェルからは使えない。デフォルトモデルは `qwen3:14b`（`backend/app/config.py` 参照）。

```bash
# WSL2からOllama疎通確認
curl http://localhost:11434/api/tags

# モデル指定はバックエンドの設定ファイルか環境変数で行う
# OLLAMA_MODEL=qwen3:14b  （backend/.env で上書き可能）
```

---

## アーキテクチャ

### ディレクトリ構成

```
GhostKeeper/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI ルーター（sessions, chat, characters, images）
│   │   ├── game/         # CoC判定ロジック（dice, skill_check, stats計算）
│   │   ├── ai/           # Ollamaクライアント・Tool定義・プロンプト
│   │   ├── models/       # SQLAlchemy モデル（Session, Character, Memory, ChatHistory）
│   │   └── main.py       # FastAPIアプリ本体・CORS・静的配信設定
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── components/   # React コンポーネント
│       ├── hooks/        # カスタムフック（useChat, useCharacter等）
│       └── types/        # TypeScript 型定義（AIレスポンス・キャラクター等）
├── images/
│   ├── characters/{id}/{expression}.png   # 立ち絵（normal/scared/angry/dead）
│   └── scenes/{id}.png                    # シーン背景
└── scenarios/            # シナリオテンプレート JSON
```

### データフロー

```
プレイヤー入力
  → POST /sessions/{id}/chat
  → AI層: Ollamaへ送信（Tool Use + JSON強制出力）
  → Toolが呼ばれる場合: roll_dice / update_stats / add_memory 等を実行
  → JSON レスポンスをパース → DB更新 → フロントへ返却
  → フロント: ナレーション表示 / 立ち絵切り替え / ダイス表示 / パラメータ更新
```

### AI出力スキーマ（JSON強制）

Ollamaの `format: "json"` を使い、全AI応答を以下の構造で受け取る：

```typescript
interface AIResponse {
  thinking: string;           // 内部推論（フロントに非表示）
  gm_narration: string;       // GMナレーション
  npc_dialogues: Array<{
    character: string;
    message: string;
    emotion: "normal" | "scared" | "angry" | "dead";
  }>;
  dice_requests: Array<{
    type: string;             // "1d100" 等
    skill: string;
    character: string;
    difficulty: "normal" | "hard" | "extreme";
  }>;
  stat_updates: Array<{
    target: string;
    field: "hp" | "san" | "mp";
    delta: number;
    reason: string;
  }>;
  image: {
    type: "character" | "scene";
    id: string;
    expression?: string;
  };
  choices: string[];          // プレイヤー向け選択肢（任意入力も常に可）
  game_event: "none" | "combat_start" | "san_check" | "skill_check" | "scenario_end";
}
```

### AI Tool一覧

| ツール | 役割 |
|--------|------|
| `roll_dice(type, count)` | ダイスロール実行 |
| `skill_check(skill, value, difficulty)` | 技能判定（成否・クリティカル/ファンブル） |
| `get_character_stats(character_id)` | パラメータ取得 |
| `update_stats(character_id, field, delta)` | HP/SAN/MP更新 |
| `search_memory(query)` | 過去イベント検索 |
| `add_memory(event, importance)` | 重要イベント記録 |
| `get_image(id, expression)` | 画像パス取得 |

### CoC 7版ゲームロジック

**派生値計算：**
- `HP = floor((CON + SIZ) / 10)`
- `MP = floor(POW / 5)`
- `SAN_max = POW × 5`（現在値・最大値・不定領域を個別管理）
- ダメージボーナス / ビルド は STR+SIZ の合計値から算出

**技能判定：**
- 技能値以下 → 成功
- 技能値の半分以下 → ハード成功
- 技能値の1/5以下 → イクストリーム成功
- 1 → クリティカル
- 96〜100（かつ技能値50未満は96以上） → ファンブル

### Ollamaモデル設定

モデル名は環境変数 or 設定ファイルで切り替え可能にする（デフォルト: `qwen3.5`）。
Qwen3系はThinking機能（内部推論）と Tool Use に対応。

---

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| Backend | FastAPI, Python 3.12, SQLAlchemy, uv |
| Frontend | React 19, Vite 7, TypeScript 5 |
| AI | Ollama (qwen3.5 デフォルト) |
| DB | SQLite |
| Lint/Format | ruff, mypy, ESLint |
| Pre-commit | ruff-check, ruff-format, mypy |
