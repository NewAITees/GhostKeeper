# 要件書 v1.0 - GhostKeeper（クトゥルフTRPG AI Chat）

## 1. システム概要

シングルプレイヤー向けのクトゥルフ神話TRPGウェブアプリ。
ローカルLLM（Ollama）がGMと全NPCを担当し、プレイヤーはチャットで探索・行動を行う。

```
プレイヤー (ブラウザ)
    │ チャット入力
    ▼
Web Frontend (React + Vite + TypeScript)
    │ HTTP / WebSocket
    ▼
Backend (FastAPI + Python 3.12)
    │ Ollama API
    ▼
Ollama (ローカルLLM: Qwen3.5, 切り替え可能)
    ├── GM AI: シナリオ進行・判定
    └── NPC AI: 他キャラ操作
```

---

## 2. 機能仕様

### 2-1. チャットUI

- プレイヤーがテキストで行動・発言を入力
- GMナレーションをストリーミング表示
- NPCはキャラクター名バッジ付きで発言
- AI提案の行動選択肢を選択ボタンで提示（任意入力も常に可）
- ダイス結果をビジュアル表示

---

### 2-2. AI設計

**モデル：** Ollama（デフォルト Qwen3.5、設定ファイルで切り替え可能）

**Think機能：**
AIは応答前に内部推論（thinking）を実行。プレイヤーには非表示。

**強制JSON出力：** 全AI応答をJSON構造で受け取る

```json
{
  "thinking": "内部推論（非表示）",
  "gm_narration": "GMの描写・ナレーション",
  "npc_dialogues": [
    {"character": "キャラ名", "message": "セリフ", "emotion": "normal"}
  ],
  "dice_requests": [
    {"type": "1d100", "skill": "図書館", "character": "pc", "difficulty": "normal"}
  ],
  "stat_updates": [
    {"target": "pc", "field": "san", "delta": -3, "reason": "怪物を目撃"}
  ],
  "image": {
    "type": "character | scene",
    "id": "string",
    "expression": "normal | scared | angry | dead"
  },
  "choices": ["行動選択肢A", "行動選択肢B"],
  "game_event": "none | combat_start | san_check | skill_check | scenario_end"
}
```

**AIが使えるツール（Tool Use）：**

| ツール | 引数 | 説明 |
|--------|------|------|
| `roll_dice` | type, count | ダイスロール実行 |
| `skill_check` | skill, value, difficulty | 技能判定（成否・クリティカル判定） |
| `get_character_stats` | character_id | パラメータ取得 |
| `update_stats` | character_id, field, delta | HP/SAN/MP更新 |
| `search_memory` | query | 過去イベント意味検索 |
| `add_memory` | event, importance | イベントを記憶 |
| `get_image` | id, expression | 画像パス取得 |

---

### 2-3. キャラクターシステム（CoC 7版）

**基本パラメータ（3d6×5 or 2d6+6×5）：**
```
STR / CON / SIZ / INT / DEX / POW / APP / EDU / LUK
```

**派生値：**
```
HP  = (CON + SIZ) / 10  （端数切り捨て）
MP  = POW / 5
SAN = POW × 5           （現在値・最大値・不定領域を管理）
ダメージボーナス（STR+SIZ から算出）
ビルド（STR+SIZ から算出）
MOV（移動力）
```

**スキル：** CoC 7版標準スキル一覧（初期値・現在値・成長フラグ）

---

### 2-4. ダイスシステム

- 対応ダイス：1d3 / 1d4 / 1d6 / 1d8 / 1d10 / 1d20 / 1d100
- 技能判定：成功 / ハード成功 / イクストリーム成功 / クリティカル / 失敗 / ファンブル
- 対抗ロール（PC vs NPC）
- ダメージロール + ダメージボーナス計算

---

### 2-5. 画像システム

```
images/
├── characters/
│   └── {character_id}/
│       ├── normal.png
│       ├── scared.png
│       ├── angry.png
│       └── dead.png
└── scenes/
    └── {scene_id}.png
```

- **立ち絵（キャラクター画像）：** NPCが発言するたびに表情差分を切り替え表示
- **シーン画像：** 場所・場面転換時に背景として表示
- 画像はFastAPIで静的配信、フォルダ追加だけで自動認識

---

### 2-6. メモリシステム

- 会話履歴（直近 N件、SQLite保存）
- 重要イベント記録（キーワード検索）
- GMが `add_memory` ツールで明示的に記録
- セッション間を跨いで記憶を保持

---

### 2-7. シナリオ管理

- **テンプレートモード：** JSON定義ファイルから読み込み（場所・登場人物・目的・クライマックス定義）
- **フリーモード：** AIがシナリオをインプロで自由生成
- 切り替えはセッション作成時に選択

---

### 2-8. セッション管理

- セッション作成 / 保存 / ロード / 削除
- 複数シナリオを切り替えて管理
- 途中再開（全ゲーム状態をSQLiteに永続化）

---

## 3. 技術スタック

| レイヤー | 技術 | 補足 |
|----------|------|------|
| Frontend | React + Vite + TypeScript | UIは日本語 |
| Backend | FastAPI (Python 3.12) | コードは英語 |
| AI | Ollama (Qwen3.5) | 設定ファイルで切り替え可能 |
| DB | SQLite + SQLAlchemy | セッション・キャラ・メモリ保存 |
| パッケージ管理 | uv | |
| 画像配信 | FastAPI Static Files | |

---

## 4. ディレクトリ構成

```
GhostKeeper/
├── backend/
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── game/         # ゲームロジック（CoC判定など）
│   │   ├── ai/           # Ollamaクライアント・Tool定義
│   │   ├── models/       # SQLAlchemyモデル
│   │   └── main.py
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── components/   # Reactコンポーネント
│   │   ├── hooks/        # カスタムフック
│   │   └── types/        # TypeScript型定義
│   └── package.json
├── images/
│   ├── characters/
│   └── scenes/
├── scenarios/             # シナリオテンプレートJSON
├── docs/
│   └── requirements.md   # この文書
└── tasks/
    ├── todo.md
    └── lessons.md
```
