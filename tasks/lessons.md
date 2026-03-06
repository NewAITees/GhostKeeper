# Lessons - 過去の失敗と学び

## 記録ルール
- バグを解決したら、ここにパターンと対策を追記する
- 設計上の判断ミスや整合性の注意点も記録する
- 同じ失敗を繰り返さないための知見をまとめる

---

## 2026-02-27 Phase 1〜3 実装

### ollama-python vs ollama パッケージ競合
- `ollama-python==0.1.2` は `httpx<0.27` に依存しており、`httpx>=0.28` との共存不可
- 対策: `uv remove ollama-python && uv add ollama` で本家パッケージに切り替え
- 本家 `ollama` パッケージは `AsyncClient` を提供し、`httpx` 制約もない

### mypy: dict[str, object] vs TypedDict
- `calc_derived_stats` の返り値を `dict[str, object]` にすると、呼び出し側で `int()` キャストが必要になりエラー
- 対策: `TypedDict` を定義して具体的な型を返すようにする

### mypy: select(Memory) の結果型推論
- `res.scalars().all()` を変数に入れると、同スコープ内の別 `res = await db.execute(select(Character)...)` の型が引き継がれることがある
- 対策: 変数名を重複させず、型注釈 `list[Memory]` を明示する

### pydantic_settings: Config クラスの非推奨警告
- Pydantic v2 では `class Config:` は非推奨。`model_config = {"env_file": ".env"}` を使う

<!-- 実装が進んだら追記していく -->

## 2026-02-27 Phase 6〜7 実装

### pre-commit: backend/ で実行しても「no files to check」になる問題
- `.pre-commit-config.yaml` はプロジェクトルートにあるが、`backend/` ディレクトリで `uv run pre-commit install` すると hook が `.git/hooks/pre-commit` に登録される
- `uv run pre-commit run --all-files` をステージングなしで実行すると「no files to check」となりスキップされる
- 対策: `git add` でファイルをステージングしてから実行する（またはプロジェクトルートから実行する）

### ruff-format の自動修正
- pre-commit で ruff-format を初回実行すると、長い行の折り返し・f-string 内のクォート変更が自動適用される
- 対策: pre-commit run 後にファイルが変更されたら再度 `git add` して再実行する（2回目でパスする）

### mypy: list の型注釈省略エラー
- `results = []` のような空リストへの代入は mypy が `var-annotated` エラーを出す
- 対策: `results: list[dict] = []` と明示的に型注釈を付ける

## 2026-02-27 環境構築
- `uv` はキャッシュディレクトリ権限の都合でサンドボックス実行に失敗する場合がある。`require_escalated` で再実行する。
- `npm create vite` はネットワーク制限下で `EAI_AGAIN` になるため、必要時は権限昇格で実行する。
- `uv init` 後の `requires-python` は環境の実行版に引っ張られるため、要件（今回は Python 3.12）に合わせて `pyproject.toml` と `.python-version` を明示修正する。

## 2026-03-06 Phase 8 実装

### game_event は AI 任せにせずバックエンドで確定処理する
- AI が `stat_updates` を返さないケースがあるため、`san_check`/`skill_check`/`combat_start` はバックエンド側で必ず判定・反映する設計にした
- 対策: `game_event` ごとに専用ヘルパーを用意し、実適用した `stat_updates` のみをレスポンスへ返す

### 第2AI呼び出しは「dice_requestsの有無」ではなく「実処理結果の有無」で判定する
- SANチェックや戦闘など、`dice_requests` 以外の自動処理結果も描写に反映させる必要がある
- 対策: ダイス・イベント結果テキストが1行でもあれば第2呼び出しする条件に変更した

### セッション要約は毎ターンのスナップショット保存が重要
- 終了時に推移を復元するには、その時点の状態を各ターンで残しておく必要がある
- 対策: `turn_summary` を毎レスポンスに含め、`raw_ai_response` から `session_summary` を組み立てる方式にした
