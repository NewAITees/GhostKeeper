# GhostKeeper AI プレイヤーマニュアル

このマニュアルは、AIエージェントが GhostKeeper API を操作してCoC TRPGをプレイするための手順書です。

---

## 前提条件

| 項目 | 内容 |
|------|------|
| バックエンド起動 | `cd backend && uv run uvicorn app.main:app --port 18000` |
| ベースURL | `http://localhost:18000` |
| Ollama | Windows側で起動済み（`http://localhost:11434` でWSL2から到達可能） |
| モンスターシード | 後述の手順で実施 |

疎通確認:
```bash
curl http://localhost:18000/api/health
# → {"status":"ok"}
```

---

## ゲームプレイの全体フロー

```
① キャラクター作成
        ↓
② モンスターシード（シナリオごとに1回）
        ↓
③ セッション作成 → 開幕ナレーション受け取り
        ↓
④ チャットループ（プレイヤーメッセージ送信 → GM応答解釈 → 繰り返し）
        ↓
⑤ セッション終了（scenario_end イベント or [SESSION_END] 送信）
```

---

## ステップ①：キャラクター作成

探索者（PC）テンプレートを作成します。セッションをまたいで再利用できます。

```bash
curl -X POST http://localhost:18000/api/characters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "エドワード・グレイ",
    "age": 32,
    "occupation": "探偵",
    "str": 60, "con": 55, "siz": 65, "dex": 70,
    "app": 50, "int": 75, "pow": 60, "edu": 70, "luck": 55,
    "skills": {
      "図書館": 60,
      "目星": 55,
      "聞き耳": 50,
      "心理学": 45,
      "拳銃": 40
    }
  }'
```

レスポンスから `id` を保存してください（以降 `{CHARACTER_ID}` と表記）。

既存キャラクター一覧を確認する場合:
```bash
curl http://localhost:18000/api/characters
```

---

## ステップ②：モンスターシード（シナリオ初回のみ）

シナリオのNPC/モンスターをDBに登録します。同じシナリオへの再実行は上書き（upsert）です。

```bash
curl -X POST http://localhost:18000/api/monsters/seed/haunted_library
```

登録済みのテンプレート一覧:
```bash
curl http://localhost:18000/api/monsters
```

利用可能なシナリオ一覧:
```bash
curl http://localhost:18000/api/scenarios
```

---

## ステップ③：セッション作成

```bash
curl -X POST http://localhost:18000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "呪われた図書館",
    "mode": "template",
    "character_id": "{CHARACTER_ID}",
    "scenario_id": "haunted_library"
  }'
```

**モード指定:**
| mode | 内容 |
|------|------|
| `"template"` | シナリオJSONを使用。NPC/モンスターが自動生成される |
| `"free"` | AIが即興でシナリオを生成する |

**レスポンス例:**
```json
{
  "id": "7490705f-...",
  "name": "呪われた図書館",
  "mode": "template",
  "scenario_id": "haunted_library",
  "initial_gm_message": "1924年、マサチューセッツ州アーカム...\n導入: 失踪した司書の行方を...",
  "created_at": "2026-03-06T07:12:29"
}
```

`initial_gm_message` がターン0のGM開幕ナレーションです。これを読んで状況を把握してからプレイを開始してください。

`id` を保存します（以降 `{SESSION_ID}` と表記）。

---

## ステップ④：チャットループ

### メッセージ送信

```bash
curl -X POST http://localhost:18000/api/sessions/{SESSION_ID}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "図書館の入口を観察します"}'
```

### レスポンス構造（AIResponse）

```json
{
  "gm_narration": "重厚な木製のドアが開く...",
  "npc_dialogues": [
    {
      "character": "エレン・チェイス",
      "message": "お願いします、地下には近づかないで...",
      "emotion": "scared"
    }
  ],
  "dice_requests": [],
  "dice_results": [
    {
      "skill": "SAN",
      "rolled": 45,
      "skill_value": 250,
      "result": "success",
      "result_ja": "成功"
    }
  ],
  "stat_updates": [
    {
      "target": "pc",
      "field": "san",
      "delta": -1,
      "reason": "SANチェック(1/1d6)"
    }
  ],
  "image": {
    "type": "scene",
    "id": "library_entrance"
  },
  "choices": [
    "エレンに詳細を尋ねる",
    "受付の引き出しを調べる",
    "地下への階段を確認する"
  ],
  "game_event": "san_check",
  "turn_summary": {
    "current_stats": {
      "hp":  {"current": 12, "max": 12},
      "san": {"current": 249, "max": 250},
      "mp":  {"current": 10, "max": 10}
    },
    "stat_delta": {"hp": 0, "san": -1, "mp": 0},
    "game_events": ["san_check"],
    "dice_results": [...]
  },
  "session_summary": null
}
```

### 各フィールドの意味と対応

| フィールド | 内容 | AIプレイヤーの対応 |
|-----------|------|------------------|
| `gm_narration` | GMの語り・状況描写 | 必ず読む。次の行動判断の基盤 |
| `npc_dialogues` | NPCのセリフと感情 | `emotion` を参考に関係性を把握する |
| `choices` | 推奨行動選択肢 | 参考にしつつ、自由な行動も送信可能 |
| `game_event` | 発生したゲームイベント | 下表参照 |
| `dice_results` | バックエンドが自動で振ったダイス結果 | 結果を把握して行動を決める（AIがダイスを振る必要はない） |
| `stat_updates` | HP/SAN/MPの変化 | `turn_summary.stat_delta` で確認 |
| `turn_summary` | 毎ターンのステータス現在値と差分 | SANが低下したら慎重な行動を検討 |
| `session_summary` | セッション終了時のフルログ | `null` でなければゲーム終了 |

### game_event の種類と意味

| game_event | 意味 | 自動処理されること |
|-----------|------|-----------------|
| `"none"` | 通常進行 | なし |
| `"san_check"` | 正気度チェック発生 | バックエンドが1d100を振り、SAN値を自動減少 |
| `"skill_check"` | 技能判定発生 | バックエンドが1d100を振り、成否を判定 |
| `"combat_start"` | 戦闘開始 | イニシアチブ計算・攻撃判定を自動処理 |
| `"scenario_end"` | シナリオ終了 | session_summaryが生成される |

**重要: ダイスはすべてバックエンドが自動で振ります。AIプレイヤーはダイス値を指定したり、ロールを拒否したりする必要はありません。**

### 戦闘時のメッセージ例

`game_event: "combat_start"` を受けたら、`choices` から行動を選んで送信します:

```bash
# 攻撃する
curl -X POST http://localhost:18000/api/sessions/{SESSION_ID}/chat \
  -d '{"message": "攻撃する"}'

# 回避する
curl -X POST http://localhost:18000/api/sessions/{SESSION_ID}/chat \
  -d '{"message": "回避する"}'

# 逃走する
curl -X POST http://localhost:18000/api/sessions/{SESSION_ID}/chat \
  -d '{"message": "逃走する"}'
```

戦闘の選択肢: `攻撃する` / `回避する` / `組みつきを試みる` / `逃走する` / `降伏する`

---

## ステップ⑤：セッション終了

### 自動終了（シナリオエンド）

`game_event: "scenario_end"` が返ってきたら、`session_summary` にフルログが入っています。

### 手動終了

```bash
curl -X POST http://localhost:18000/api/sessions/{SESSION_ID}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "[SESSION_END]"}'
```

### session_summary の構造

```json
{
  "conversation_log": [
    {"role": "gm", "content": "1924年...", "created_at": "..."},
    {"role": "player", "content": "図書館に入ります", "created_at": "..."}
  ],
  "stat_history": [
    {
      "turn": 1,
      "created_at": "...",
      "current_stats": {"hp": {...}, "san": {...}, "mp": {...}},
      "stat_delta": {"hp": 0, "san": -1, "mp": 0}
    }
  ],
  "important_events": [
    "2026-03-06T07:20:00 san_check",
    "2026-03-06T07:22:00 skill_check"
  ]
}
```

---

## 補足：セッション・キャラクター確認 API

```bash
# セッション一覧
curl http://localhost:18000/api/sessions

# セッション詳細（PC/NPCのHP・SANなど）
curl http://localhost:18000/api/sessions/{SESSION_ID}

# 会話履歴
curl http://localhost:18000/api/sessions/{SESSION_ID}/chat

# セッション削除
curl -X DELETE http://localhost:18000/api/sessions/{SESSION_ID}
```

---

## AIプレイヤーとしての行動指針

1. **`initial_gm_message` を必ず読む** — シナリオの世界観・目的・登場人物が書かれている

2. **`gm_narration` と `npc_dialogues` を解釈して行動を決める** — `choices` は参考程度。自由な行動テキストを送っても良い

3. **`turn_summary.stat_delta` を毎ターン確認する** — SANが大きく下がったら慎重な行動を。HPが0になると即死

4. **ダイスに介入しない** — `dice_results` に結果が自動で入るので、AIは「ダイスを振る」メッセージを送る必要はない。バックエンドが処理する

5. **シナリオ目的に向かって行動する** — `opening_narration` に書かれた `objective` を達成することがゴール

6. **戦闘は `choices` を参照して行動を選ぶ** — 毎ターン1アクション。`逃走する` は常に有効

---

## クイックスタート（コピペ用）

```bash
BASE="http://localhost:18000"

# 1. キャラクター確認または作成
CHAR_ID=$(curl -s $BASE/api/characters | python3 -c "import sys,json; cs=json.load(sys.stdin); print(cs[0]['id'] if cs else '')")

# 2. モンスターシード
curl -s -X POST $BASE/api/monsters/seed/haunted_library > /dev/null

# 3. セッション作成
SESSION=$(curl -s -X POST $BASE/api/sessions \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"テストプレイ\",\"mode\":\"template\",\"character_id\":\"$CHAR_ID\",\"scenario_id\":\"haunted_library\"}")
SESSION_ID=$(echo $SESSION | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo $SESSION | python3 -c "import sys,json; print(json.load(sys.stdin).get('initial_gm_message',''))"

# 4. チャット送信
curl -s -X POST $BASE/api/sessions/$SESSION_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "図書館に入ります。状況を観察します。"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('GM:', d['gm_narration'])
for npc in d.get('npc_dialogues', []):
    print(f\"NPC [{npc['character']}]: {npc['message']}\")
print('選択肢:', d.get('choices', []))
print('event:', d['game_event'])
ts = d.get('turn_summary', {})
print('SAN:', ts.get('current_stats', {}).get('san'))
"
```
