# GhostKeeper - タスク一覧

## 運用ルール
1. タスクを追加するときはチェックボックス形式で書く
2. 完了したら `[x]` にする
3. セクションが全て完了したら、セクションごと削除してよい

---

## Phase 1: バックエンド基盤

- [x] FastAPI アプリ骨格 (`app/main.py`, CORS設定)
- [x] SQLite + SQLAlchemy モデル定義
  - [x] Session モデル
  - [x] Character モデル（基本値・派生値・スキル）
  - [x] Memory モデル（重要イベント記録）
  - [x] ChatHistory モデル
- [x] 画像フォルダ静的配信設定
- [x] 設定ファイル（Ollamaモデル名等）外部化
- [x] 既存 backend/main.py を app/main.py に移行

## Phase 2: ゲームロジック

- [x] CoC 7版 パラメータ計算（HP / MP / SAN / ダメージボーナス / ビルド / MOV）
- [x] ダイスロールエンジン（1d3〜1d100）
- [x] 技能判定ロジック（成功 / ハード / イクストリーム / クリティカル / ファンブル）
- [x] SAN チェック・減少処理
- [x] HP 増減ヘルパー（stats.py）
- [ ] 対抗ロールロジック（Phase 4以降）

## Phase 3: AI連携

- [x] Ollamaクライアント実装（モデル設定で切り替え可能）
- [x] システムプロンプト設計（GM役・CoC世界観）
- [x] JSON強制出力設定（`format: "json"` + スキーマ定義）
- [x] Think機能統合（<think>タグ除去処理）
- [x] Tool use 実装
  - [x] `roll_dice`
  - [x] `skill_check`
  - [x] `get_character_stats`
  - [x] `update_stats`
  - [x] `search_memory`
  - [x] `add_memory`
  - [x] `get_image`
- [x] メモリ検索（キーワード検索）
- [x] チャット API でのツールハンドラー統合

## Phase 4: APIエンドポイント

- [x] `POST /api/sessions` - セッション作成
- [x] `GET /api/sessions` - セッション一覧
- [x] `GET /api/sessions/{id}` - セッション取得
- [x] `DELETE /api/sessions/{id}` - セッション削除
- [x] `GET /api/sessions/{id}/chat` - 会話履歴取得
- [x] `POST /api/sessions/{id}/chat` - チャット送信
- [x] `GET /api/characters/{id}` - キャラクター情報取得
- [x] `PATCH /api/characters/{id}` - キャラクター更新
- [x] `GET /api/images/characters` - キャラクター画像一覧
- [x] `GET /api/images/scenes` - シーン画像一覧
- [ ] `GET /scenarios` - シナリオ一覧（Phase 6）

## Phase 5: フロントエンド

- [x] 全体レイアウト（チャットエリア / サイドパネル）
- [x] チャット入力コンポーネント
- [x] GMメッセージ表示（ストリーミング）
- [x] NPCセリフ表示（キャラ名バッジ付き）
- [x] 行動選択肢ボタン
- [x] ダイス結果ビジュアル表示
- [x] 立ち絵表示（表情切り替えアニメーション）
- [x] シーン画像表示（背景）
- [x] キャラクターシート表示（HP / SAN / MP）
- [x] セッション選択・作成画面

## Phase 6: シナリオ管理

- [x] シナリオテンプレートJSONスキーマ定義（scenarios/schema.json）
- [x] サンプルシナリオ1本作成（scenarios/haunted_library.json）
- [x] GET /api/scenarios, GET /api/scenarios/{id} エンドポイント実装
- [x] シナリオ情報をAIプロンプトに注入（build_messages に scenario 引数追加）
- [x] GmClient.chat() に scenario 引数追加
- [x] send_chat で scenario_id からシナリオデータを取得して AI に渡す
- [x] フロントエンド: api/client.ts に listScenarios() 追加
- [x] フロントエンド: SessionCreate.tsx にシナリオ選択 UI 実装
- [x] フリーモード（AIインプロ生成）切り替え実装

## Phase 7: 品質・仕上げ

- [x] pre-commit 設定（ruff / mypy）- pre-commit install + run --all-files 全通過
- [x] README 作成

---

## Phase 8: ゲームプレイ品質改善（実機テストで発覚）

### 8-1: ターン0 GM開幕ナレーション
- [x] セッション作成直後（プレイヤーが最初のメッセージを送る前）に、GMが自動でオープニングを語る
  - シナリオの世界観・時代背景・場所の説明
  - 探索者（PC）がなぜここにいるかの導入
  - 登場NPC・関係性の紹介
  - 「何をすべきか」の方向性をほのめかす
- [x] 実装方針: `POST /api/sessions` 作成時 or セッション初回チャット時に自動でGM初回メッセージをDBに保存してレスポンスに含める

### 8-2: ダイス・判定のシステム自動処理
- [x] ダイスロール（1d100等）はバックエンドが乱数生成して処理する
  - プレイヤーはダイスを振れない。AIがgame_eventでダイスを要求し、バックエンドが即座に自動で振る
  - 現状: `dice_requests` を返してもバックエンドが自動処理していない
- [x] SANチェックの自動処理
  - `game_event: san_check` を受けたら、バックエンドが1d100を振り、成否を判定し、SAN減少値（成功:1d3/失敗:1d6等）を自動計算してDBに反映
  - 結果をAIへ第2呼び出しで渡し、成否に応じた描写を生成させる
- [x] 技能判定（skill_check）の自動処理
  - 同様に `game_event: skill_check` でバックエンドが自動実行
  - 成功/ハード/イクストリーム/クリティカル/ファンブルをAIに通知して描写生成
- [x] stat_updates の確実な反映
  - AIがSANチェック発生時に `stat_updates` を返さないケースがある
  - バックエンド側でゲームイベント発生時は必ずステータスを更新する

### 8-3: 戦闘システム
- [x] `game_event: combat_start` 時の戦闘フロー実装
  - イニシアチブ計算（DEX順）
  - 攻撃/回避/組みつきの選択肢提示
  - ダメージ計算・HP反映
  - 戦闘終了条件（HP0/逃走/降伏）

### 8-4: セッションサマリー自動生成
- [x] チャット送信レスポンスに毎回サマリー情報を含める
  - 現在HP/SAN/MP（変化があれば差分表示）
  - 発生したgame_event
  - ダイス結果（出目・技能値・成否）
- [x] セッション終了時（`game_event: scenario_end` or 手動）にフルサマリーを生成
  - 全ターンの会話ログ
  - ステータス推移グラフ（SAN変動等）
  - 重要イベント一覧
