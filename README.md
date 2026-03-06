# GhostKeeper

クトゥルフ神話TRPG（CoC 7版）シングルプレイヤー向けウェブアプリ。
ローカルLLM（Ollama）がゲームマスターと全NPCを担当し、プレイヤーはチャットで探索・行動を行う。

---

## 必要環境

- Python 3.12 以上
- Node.js 18 以上
- [Ollama](https://ollama.com/) （ローカルLLM実行環境）

---

## クイックスタート

```bash
# 1. Ollama サーバーを起動してモデルを取得（初回のみ）
ollama pull qwen3:14b

# 2. 依存パッケージをインストール（初回のみ）
make install

# 3. 両サービスを同時起動
make dev
```

ブラウザで `http://localhost:5173` を開いてください。

停止するには:

```bash
make stop
```

ログを確認するには:

```bash
make logs
```

---

## セットアップ手順（個別起動）

### 1. Ollama のインストール・モデル取得

[Ollama 公式サイト](https://ollama.com/) からインストール後、以下を実行:

```bash
ollama serve                 # Ollama サーバー起動
ollama pull qwen3.5:9b        # デフォルトモデル取得（初回のみ）
```

### 2. バックエンド起動

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 18000
```

バックエンドが `http://localhost:18000` で起動します。

### 3. フロントエンド起動

別ターミナルで:

```bash
cd frontend
npm install
npm run dev
```

フロントエンドが `http://localhost:5173` で起動します。ブラウザで開いてください。

---

## 設定変更方法

### Ollama モデルの切り替え

`backend/.env` ファイルを作成（または編集）して、使用するモデルを指定できます:

```env
OLLAMA_MODEL=モデル名
```

例:

```env
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_MODEL=llama3.2
OLLAMA_MODEL=gemma3
```

設定可能な項目一覧（`backend/app/config.py` 参照）:

| 環境変数 | デフォルト値 | 説明 |
|----------|-------------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama サーバーアドレス |
| `OLLAMA_MODEL` | `qwen3.5:9b` | 使用するモデル名 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ghostkeeper.db` | データベース接続先 |
| `MEMORY_CONTEXT_LIMIT` | `20` | 会話履歴の最大保持件数 |

---

## 画像の追加方法

### キャラクター立ち絵

```
images/characters/{キャラクターID}/normal.png
images/characters/{キャラクターID}/scared.png
images/characters/{キャラクターID}/angry.png
images/characters/{キャラクターID}/dead.png
```

例: `images/characters/william_morse/normal.png`

対応フォーマット: PNG、JPG、JPEG、WebP

### シーン背景

```
images/scenes/{シーンID}.png
```

例: `images/scenes/library_entrance.png`

---

## シナリオの追加方法

`scenarios/` フォルダに JSON ファイルを置くだけで自動的に認識されます。

```
scenarios/
├── schema.json           # JSONスキーマ定義（参照用）
├── haunted_library.json  # サンプルシナリオ: 呪われた図書館
└── my_scenario.json      # 追加したシナリオ
```

### スキーマ

スキーマの詳細は `scenarios/schema.json` を参照してください。

最小構成の例:

```json
{
  "id": "my_scenario",
  "title": "私のシナリオ",
  "description": "シナリオの簡単な説明",
  "era": "1920年代、ニューイングランド",
  "location": "アーカム",
  "synopsis": "GMだけが知るあらすじ（プレイヤー非公開）",
  "objective": "プレイヤーの目標",
  "starting_location": "entrance",
  "locations": [
    {
      "id": "entrance",
      "name": "入口",
      "description": "場所の説明",
      "clues": ["発見できる手がかり"]
    }
  ],
  "gm_instructions": "AIへの追加指示。雰囲気・禁止事項・特別ルールなど"
}
```

---

## ゲームの遊び方

1. **セッション作成**: トップ画面で「新しいシナリオを始める」をクリック
   - フリーモード: AIがアドリブでシナリオを進行
   - テンプレート: 用意されたシナリオから選択してプレイ

2. **探索**: チャット入力欄にプレイヤーの行動を日本語で入力
   - 例: 「図書館の受付に近づき、司書に話しかける」
   - 表示される選択肢ボタンをクリックしても行動できる

3. **判定**: AIがCoC 7版ルールに従い技能判定・SANチェックを実施
   - ダイスの結果はリアルタイムで表示される

4. **キャラクターシート**: 右サイドパネルでHP・SAN・MPの現在値を確認できる

5. **セッション管理**: トップ画面でセッションの一覧・選択・削除ができる

---

## 開発者向け

### テスト実行

```bash
cd backend
uv run pytest -v
```

### コード品質チェック

```bash
cd backend
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pre-commit run --all-files
```

```bash
cd frontend
npm run lint
npm run build
```

### ディレクトリ構成

```
GhostKeeper/
├── backend/               # FastAPI バックエンド
│   ├── app/
│   │   ├── api/           # エンドポイント（sessions, chat, characters, images, scenarios）
│   │   ├── ai/            # Ollama クライアント・プロンプト・ツール定義
│   │   ├── game/          # CoC 7版ゲームロジック
│   │   ├── models/        # SQLAlchemy モデル
│   │   └── main.py        # アプリ本体
│   └── tests/             # pytest テスト
├── frontend/              # React フロントエンド
│   └── src/
│       ├── api/           # APIクライアント
│       ├── components/    # React コンポーネント
│       ├── hooks/         # カスタムフック
│       └── types/         # TypeScript 型定義
├── images/                # 画像ファイル（キャラクター・シーン）
└── scenarios/             # シナリオ JSON ファイル
```
