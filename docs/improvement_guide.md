# GhostKeeper 改善実装ガイド

## 変更概要

1. **キャラクター管理の独立化** - キャラクターをセッションと分離し、事前作成・使い回しを可能に
2. **キャラクター作成専用画面** - ダイス振り→職業選択→スキル割り振りの専用フロー
3. **オープニングナレーション** - ゲーム開始時にAIが自動で場面描写
4. **2段階ダイスフロー** - AI→ダイス実行→AI（結果を受けて続き）という往復処理
5. **NPC個別記憶** - NPCがGMとは別の記憶・個性を持つ
6. **NAVパネル + クイックボタン** - 現在地・NPC一覧・文脈に応じたボタン

---

## 前提確認

- 作業ディレクトリ: `/home/perso/analysis/GhostKeeper`
- 実装前に `tasks/todo.md` と `tasks/lessons.md` を確認すること
- 既存コードを必ず読んでから修正すること（特にDB周り）

---

## Part 1: キャラクター管理の独立化

### 1-1. DBスキーマ変更（Character モデル）

`backend/app/models/character.py` に以下のフィールドを追加する:

```python
# session_id を nullable にする（既存はすでに nullable のはず）
# 以下を追加:
is_template: Mapped[bool] = mapped_column(Boolean, default=False)
# is_template=True かつ session_id=None → 事前作成キャラクター（テンプレート）
# is_template=False かつ session_id=あり → セッション内コピー

occupation: Mapped[str | None] = mapped_column(String, nullable=True)
backstory: Mapped[str | None] = mapped_column(Text, nullable=True)  # 経歴・背景

# NPC用フィールド
personality: Mapped[str | None] = mapped_column(Text, nullable=True)  # NPCの個性・話し方
npc_memory: Mapped[dict] = mapped_column(JSON, default=dict)  # NPC個別記憶
```

`backend/app/models/session.py` に以下を追加する:

```python
current_location: Mapped[str | None] = mapped_column(String, nullable=True)
# AI がシーンを進める際に現在地を更新する
```

**Alembic は使わず**、`init_db()` の `create_all` で差分を追加する（開発段階なので DROP＆CREATE でOK。既存DBを削除して再作成）。

---

### 1-2. キャラクターCRUD API（テンプレート専用）

`backend/app/api/characters.py` を修正して以下エンドポイントを追加・変更する:

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/characters` | テンプレートキャラ一覧（is_template=True かつ session_id=None） |
| POST | `/api/characters` | テンプレートキャラ作成 |
| GET | `/api/characters/{id}` | キャラ詳細（既存・変更不要） |
| PATCH | `/api/characters/{id}` | キャラ更新（既存・変更不要） |
| DELETE | `/api/characters/{id}` | テンプレートキャラ削除（is_template=True のみ許可） |

**テンプレートキャラ作成リクエストボディ:**
```json
{
  "name": "田中一郎",
  "age": 28,
  "occupation": "探偵",
  "backstory": "元刑事。3年前に妻を不審な事故で亡くし、真相を追っている。",
  "str_": 65, "con": 60, "siz": 55, "int_": 70,
  "dex": 60, "pow_": 65, "app": 50, "edu": 75, "luk": 50,
  "skills": {
    "目星": {"base": 25, "current": 60, "growth": false},
    "聞き耳": {"base": 20, "current": 50, "growth": false},
    "図書館": {"base": 20, "current": 45, "growth": false},
    "心理学": {"base": 10, "current": 40, "growth": false},
    "追跡": {"base": 10, "current": 50, "growth": false}
  }
}
```

---

### 1-3. 職業一覧API

`backend/app/api/occupations.py` を新規作成する:

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/occupations` | CoC 7版職業一覧を返す |
| POST | `/api/occupations/roll-stats` | キャラ用ダイスロール実行（ステータス全項目） |

**職業データ（コード内に定数として定義）:**

```python
OCCUPATIONS = [
    {
        "id": "detective",
        "name": "探偵",
        "description": "謎を解くことを生業とする者。観察眼と推理力が武器。",
        "skill_points_formula": "EDU×2 + DEX×2",
        "credit_rating": "9-30",
        "typical_skills": ["図書館", "目星", "聞き耳", "心理学", "法律", "追跡", "写真術", "言いくるめ"],
    },
    {
        "id": "doctor",
        "name": "医師",
        "description": "医療の専門家。人体と薬の知識を持つ。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "30-80",
        "typical_skills": ["医学", "心理学", "薬学", "図書館", "説得", "応急手当", "科学（生物学）"],
    },
    {
        "id": "journalist",
        "name": "記者",
        "description": "真実を追い求める報道人。情報収集と人脈が強み。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "9-30",
        "typical_skills": ["図書館", "心理学", "歴史", "写真術", "説得", "聞き耳", "目星", "言いくるめ"],
    },
    {
        "id": "professor",
        "name": "教授・研究者",
        "description": "大学で研究・教育に携わる学者。専門知識と文献調査が得意。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "20-70",
        "typical_skills": ["図書館", "歴史", "考古学", "言語（ラテン語）", "心理学", "オカルト"],
    },
    {
        "id": "police",
        "name": "警察官",
        "description": "法の執行者。市民の安全を守る。",
        "skill_points_formula": "EDU×2 + STR×2",
        "credit_rating": "9-30",
        "typical_skills": ["目星", "聞き耳", "心理学", "法律", "格闘（拳）", "射撃（拳銃）", "追跡"],
    },
    {
        "id": "soldier",
        "name": "軍人",
        "description": "戦闘訓練を受けた兵士。戦術と体力が武器。",
        "skill_points_formula": "EDU×2 + STR×2",
        "credit_rating": "9-30",
        "typical_skills": ["格闘（拳）", "射撃", "応急手当", "目星", "歴史", "電気修理"],
    },
    {
        "id": "clergy",
        "name": "聖職者",
        "description": "宗教的指導者。信仰と人心掌握に長ける。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "9-60",
        "typical_skills": ["図書館", "歴史", "心理学", "説得", "言語（ラテン語）", "オカルト"],
    },
    {
        "id": "antiquarian",
        "name": "古物研究家",
        "description": "骨董品・古書の収集家・研究者。謎めいた品々に詳しい。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "30-70",
        "typical_skills": ["図書館", "歴史", "考古学", "芸術/工芸（鑑定）", "目星", "オカルト"],
    },
]
```

**`POST /api/occupations/roll-stats` レスポンス:**
```json
{
  "str_": 65,
  "con": 50,
  "siz": 70,
  "int_": 80,
  "dex": 55,
  "pow_": 60,
  "app": 45,
  "edu": 75,
  "luk": 50,
  "roll_details": {
    "str_": [4, 5, 6],
    "con": [3, 4, 3],
    ...
  }
}
```

ダイスロール規則（CoC 7版）:
- STR / CON / DEX / APP / POW / LUK: 3d6 × 5
- SIZ / INT / EDU: (2d6 + 6) × 5

`backend/app/main.py` にルーター追加:
```python
from app.api import occupations
app.include_router(occupations.router, prefix="/api/occupations", tags=["occupations"])
```

---

### 1-4. セッション作成の変更

`backend/app/api/sessions.py` の `SessionCreate` と `create_session` を変更する:

```python
class SessionCreate(BaseModel):
    name: str
    mode: ScenarioMode = ScenarioMode.free
    scenario_id: str | None = None
    character_id: str          # ← pc_name の代わりに既存キャラIDを指定
    # pc_name は削除
```

`create_session` の処理:
1. `character_id` でテンプレートキャラを取得（なければ 404）
2. キャラクターを **コピー** して `session_id` を設定した新レコードを作成（`is_template=False`）
3. 元のテンプレートは変更しない（セッション中のHP/SAN変化は複製先のみに反映）

---

## Part 2: オープニングナレーション

### バックエンド変更

`backend/app/api/chat.py` の `send_chat` を修正:

```python
GAME_START_TRIGGER = "[GAME_START]"

@router.post("/{session_id}/chat")
async def send_chat(...):
    is_game_start = body.message.strip() == GAME_START_TRIGGER

    if is_game_start:
        # プレイヤーメッセージはDBに保存しない
        player_message_for_ai = (
            "ゲームを開始します。探索者が最初のシーンに登場する冒頭の描写を行ってください。"
            "探索者の状況、場所の雰囲気、最初の出来事を生き生きと描写し、"
            "探索者が最初に取るべき行動の選択肢を3つ提示してください。"
        )
    else:
        player_message_for_ai = body.message
        # 通常通りDBに保存
        db.add(ChatHistory(session_id=session_id, role=MessageRole.player, content=body.message))
        await db.commit()

    # ... 以降のAI呼び出し処理
```

### フロントエンド変更

`frontend/src/hooks/useGame.ts` に以下を追加:

```typescript
// ゲーム画面に入った時、チャット履歴が空なら自動でGAME_STARTを送信
useEffect(() => {
  if (sessionId && displayMessages.length === 0 && !isSending) {
    sendMessage('[GAME_START]')
  }
}, [sessionId])
```

---

## Part 3: 2段階ダイスフロー

### バックエンド変更

`backend/app/api/chat.py` の `send_chat` を2段階処理に変更する。

**処理フロー:**

```
1. プレイヤーメッセージ受信
2. [第1AI呼び出し] → gm_narration + dice_requests
3. dice_requests が空 → そのまま返す
4. dice_requests がある → サーバーでダイスを振る
5. [第2AI呼び出し] ダイス結果を渡して「続きを語って」
6. 最終レスポンスを返す
```

**`GmClient` に `chat_with_dice_result` メソッドを追加:**

```python
async def chat_with_dice_result(
    self,
    previous_messages: list[dict],
    first_narration: str,
    dice_results_text: str,
) -> AIResponse:
    """
    ダイス結果を踏まえた第2AI呼び出し。
    previous_messages に第1応答を追加し、ダイス結果を渡して続きを生成。
    """
    messages = list(previous_messages)
    # 第1応答をアシスタントのメッセージとして追加
    messages.append({
        "role": "assistant",
        "content": json.dumps({"gm_narration": first_narration}, ensure_ascii=False),
    })
    # ダイス結果をユーザーメッセージとして追加
    messages.append({
        "role": "user",
        "content": (
            f"ダイスロール結果:\n{dice_results_text}\n\n"
            "上記の結果を踏まえて、続きを語ってください。"
            "成功・失敗・クリティカル・ファンブルに応じて劇的に描写を変えてください。"
        ),
    })

    response = await self.client.chat(
        model=self.model,
        messages=messages,
        format="json",
        options={"temperature": 0.8},
    )
    raw = response.message.content or "{}"
    return _parse_ai_response(raw)
```

**`send_chat` のダイス処理部分:**

```python
async def _execute_dice_requests(
    ai_response: AIResponse,
    pc: Character,
    db: AsyncSession,
) -> tuple[list[dict], str]:
    """
    AIのdice_requestsを実行してダイス結果と説明テキストを返す。
    stat_updatesも適用する。
    """
    from app.game.dice import roll
    from app.game.rules import skill_check
    from app.game.stats import get_stat_field, apply_stat_delta, set_stat_field

    results = []
    lines = []

    for req in ai_response.dice_requests:
        if req.skill and req.character in ("pc", pc.name, pc.id):
            # スキルチェック
            skills: dict = pc.skills or {}
            skill_data = skills.get(req.skill, {})
            skill_val = int(
                skill_data.get("current", skill_data.get("base", 25))
                if isinstance(skill_data, dict) else skill_data
            )
            detail = skill_check(skill_val, req.difficulty)
            result_ja = {
                "critical": "クリティカル！",
                "extreme_success": "イクストリーム成功",
                "hard_success": "ハード成功",
                "success": "成功",
                "failure": "失敗",
                "fumble": "ファンブル！",
            }.get(detail.result.value, detail.result.value)

            results.append({
                "skill": req.skill,
                "rolled": detail.rolled,
                "skill_value": skill_val,
                "result": detail.result.value,
                "result_ja": result_ja,
            })
            lines.append(
                f"【{req.skill}判定】1d100={detail.rolled} vs {skill_val} → {result_ja}"
            )
        else:
            # 単純ダイスロール
            dice_result = roll(req.type or "1d6")
            results.append({
                "type": req.type,
                "rolls": dice_result.rolls,
                "total": dice_result.total,
            })
            lines.append(f"【{req.type}】= {dice_result.total}（{dice_result.rolls}）")

    # stat_updates をここで適用
    for upd in ai_response.stat_updates:
        if upd.target in ("pc", pc.name, pc.id):
            current, max_val = get_stat_field(pc, upd.field)
            new_val = apply_stat_delta(current, upd.delta, max_val)
            set_stat_field(pc, upd.field, new_val)
    await db.commit()

    return results, "\n".join(lines)
```

`send_chat` の末尾近くに2段階呼び出しを組み込む:

```python
    # --- 第1AI呼び出し ---
    ai_response = await gm_client.chat(
        player_message=player_message_for_ai,
        chat_history=chat_history,
        character_summary=character_summary,
        memories=memories,
        tool_handler=_make_tool_handler(session_id, db),
        scenario=scenario_data,
    )

    # --- ダイスリクエストがあれば実行 + 第2AI呼び出し ---
    if ai_response.dice_requests:
        pc_result = await db.execute(
            select(Character).where(
                Character.session_id == session_id,
                Character.is_pc == True,
            )
        )
        pc = pc_result.scalar_one_or_none()
        if pc:
            dice_results, dice_text = await _execute_dice_requests(ai_response, pc, db)
            # 第2AI呼び出し（ダイス結果を渡す）
            first_messages = build_messages(chat_history, player_message_for_ai, character_summary, memories, scenario_data)
            ai_response = await gm_client.chat_with_dice_result(
                previous_messages=first_messages,
                first_narration=ai_response.gm_narration,
                dice_results_text=dice_text,
            )
            # ダイス結果をレスポンスに追加
            # dice_requestsにresultsを付与 (フロントに返すため)
            ai_response = ai_response.model_copy(
                update={"dice_results": dice_results}  # schemas.pyに追加
            )
```

**AIResponseスキーマに `dice_results` フィールドを追加:**

`backend/app/ai/schemas.py`:
```python
class DiceResult(BaseModel):
    """実際に振ったダイスの結果（フロントエンド表示用）"""
    skill: str | None = None
    type: str | None = None
    rolled: int | None = None
    total: int | None = None
    skill_value: int | None = None
    result: str | None = None       # "success", "failure" など
    result_ja: str | None = None    # "成功", "失敗" など

class AIResponse(BaseModel):
    # ... 既存フィールド ...
    dice_results: list[DiceResult] = []  # 追加
```

---

## Part 4: NPC個別記憶

### システムプロンプト変更

`backend/app/ai/prompts.py` の `build_messages` を修正して、NPC情報を含める:

```python
def build_messages(
    chat_history, player_message, character_summary, memories,
    scenario=None,
    npcs: list[dict] | None = None,   # ← 追加
) -> list[dict]:
    # ... 既存処理 ...

    if npcs:
        system_content += "\n\n## 現在のNPC状態\n"
        for npc in npcs:
            system_content += f"\n### {npc['name']}（{npc.get('role', '')}）\n"
            if npc.get("personality"):
                system_content += f"個性: {npc['personality']}\n"
            if npc.get("npc_memory"):
                mem_items = npc["npc_memory"].get("events", [])
                if mem_items:
                    system_content += "記憶:\n"
                    for ev in mem_items[-5:]:  # 直近5件
                        system_content += f"  - {ev}\n"

    # ...
```

### NPCメモリ更新

`backend/app/api/chat.py` のツールハンドラーに `update_npc_memory` を追加:

```python
elif tool_name == "update_npc_memory":
    char_id = args["character_id"]
    event = args["event"]
    res = await db.execute(select(Character).where(Character.id == char_id))
    npc = res.scalar_one_or_none()
    if npc:
        mem = npc.npc_memory or {"events": []}
        mem.setdefault("events", []).append(event)
        npc.npc_memory = mem
        await db.commit()
    return {"status": "ok"}
```

`backend/app/ai/tools.py` にツール定義を追加:

```python
{
    "type": "function",
    "function": {
        "name": "update_npc_memory",
        "description": "NPCの個別記憶にイベントを追加する",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "event": {"type": "string"},
            },
            "required": ["character_id", "event"],
        },
    },
},
```

---

## Part 5: フロントエンド改善

### 5-1. 新しい画面フロー

```
ホーム（SessionList）
  ├─ キャラクターを管理する → CharacterManager
  │    ├─ キャラクター一覧
  │    ├─ 新規作成 → CharacterCreator
  │    │    ├─ Step1: 名前・年齢・経歴入力
  │    │    ├─ Step2: ダイスロール（🎲ランダム生成 ボタン）
  │    │    ├─ Step3: 職業選択（スキルポイント計算）
  │    │    ├─ Step4: スキル割り振り
  │    │    └─ 保存
  │    └─ 編集・削除
  └─ セッション開始 → SessionCreate（キャラ選択付き）
       └─ GameScreen
```

### 5-2. CharacterCreator コンポーネント

`frontend/src/components/character/CharacterCreator.tsx`

**Step 1: 基本情報**
```
名前: [         ]
年齢: [  ]
経歴: [                    ]（任意）
```

**Step 2: ステータスロール**
```
[🎲 ダイスを振る]  ← クリックでアニメーション付きロール

STR [65 ▲▼]  CON [50 ▲▼]  SIZ [70 ▲▼]
INT [80 ▲▼]  DEX [55 ▲▼]  POW [60 ▲▼]
APP [45 ▲▼]  EDU [75 ▲▼]  LUK [50 ▲▼]

HP: 12  MP: 12  SAN: 60

※▲▼で±5の微調整可（ポイント制限なし、フレーバー調整）
```

**Step 3: 職業選択**
```
[探偵] [医師] [記者] [教授] [警察官] [軍人] [聖職者] [古物研究家]

選択中: 探偵
  スキルポイント: EDU(75)×2 + DEX(55)×2 = 260
  趣味ポイント: INT(80)×2 = 160
  推奨スキル: 図書館, 目星, 聞き耳, 心理学, 追跡...
```

**Step 4: スキル割り振り**

CoC標準スキル一覧を表示。職業SPと趣味SPを割り振れる:
```
残り職業SP: [210]  残り趣味SP: [160]

スキル名    基本値  職業SP  趣味SP  合計
目星         25     35      0      60  [+5][-5]
聞き耳       20     30      0      50  [+5][-5]
図書館       20     25      0      45  [+5][-5]
...
```

**標準スキルリスト（コード内に定数として定義）:**
```typescript
const STANDARD_SKILLS: Record<string, number> = {
  "格闘（拳）": 25, "回避": 0, // DEX/2で計算
  "射撃（拳銃）": 20, "射撃（ライフル）": 25,
  "目星": 25, "聞き耳": 20, "図書館": 20,
  "心理学": 10, "説得": 10, "言いくるめ": 5,
  "応急手当": 30, "医学": 1, "薬学": 1,
  "法律": 5, "会計": 5, "コンピューター": 5,
  "電気修理": 10, "機械修理": 10,
  "忍び歩き": 20, "隠す": 20, "変装": 5,
  "追跡": 10, "水泳": 20, "跳躍": 20, "登攀": 20,
  "乗馬": 5, "運転（自動車）": 20,
  "操縦（航空機）": 1, "航海": 1,
  "写真術": 5, "芸術/工芸": 5,
  "歴史": 5, "考古学": 1, "人類学": 1,
  "オカルト": 5, "クトゥルフ神話": 0,
  "言語（英語）": 1, "言語（ラテン語）": 1,
  "科学（生物学）": 1, "科学（化学）": 1,
  "科学（物理学）": 1, "科学（天文学）": 1,
}
```

### 5-3. SessionCreate の変更

キャラクター選択プルダウンを追加:
```
シナリオ名: [         ]
モード: ○ フリー  ● テンプレート
キャラクター: [▼ 田中一郎（探偵）]  [+ 新規作成]
探索者名: （キャラ選択で自動入力）

[開始する]
```

`api/client.ts` に追加:
```typescript
// Characters
listTemplateCharacters: () => req<Character[]>('/api/characters'),
createCharacter: (body: CharacterCreateBody) =>
  req<Character>('/api/characters', { method: 'POST', body: JSON.stringify(body) }),
deleteCharacter: (id: string) =>
  req<void>(`/api/characters/${id}`, { method: 'DELETE' }),

// Occupations
listOccupations: () => req<Occupation[]>('/api/occupations'),
rollStats: () => req<RolledStats>('/api/occupations/roll-stats', { method: 'POST' }),
```

### 5-4. GameScreen の変更

#### NAVパネル（サイドバー上部に追加）

```
現在地: 大閲覧室
────────────────
NPC:
  📖 ウィリアム・モース
  👤 エレン・チェイス
```

セッション詳細（`GET /api/sessions/{id}`）の `characters` リストからNPCを取得して表示。

#### ダイスロールボタン（dice_requestsがある時のみ表示）

AIの`dice_requests`が返ってきたら、ChoiceButtons の上に表示:

```
GM がダイスを求めています:
[🎲 図書館 (1d100) を振る]  [🎲 目星 (1d100) を振る]
```

ボタンをクリック → `sendMessage('[DICE_ROLL:図書館]')` などのトリガーを送信
→ バックエンドで処理して第2AIコールを実行

実際には：**フロントのボタンはUIのみ**で、実際のダイス処理はバックエンドが自動で行う（Phase 4の2段階フロー）。
`dice_requests` がある場合、フロントには「GMがダイスを振っています...」というローディング表示のみでよい。

#### DiceResultCard コンポーネント

`dice_results`（schemas.DiceResult の配列）が返ってきた時のチャット表示:

```
🎲 図書館判定
   1d100 = 45   技能値: 60
   ────────────
   ✅ 成功！
```

成功=緑、失敗=赤、クリティカル=金色、ファンブル=赤点滅

---

## Part 6: 既存DBの再作成

スキーマ変更があるため、開発用DBを削除して再作成する:

```bash
cd /home/perso/analysis/GhostKeeper/backend
rm -f ghostkeeper.db
# uvicorn 起動時に init_db() が自動でテーブルを再作成する
```

---

## 完了条件

### バックエンド
- [ ] `GET /api/characters` でテンプレートキャラ一覧が返る
- [ ] `GET /api/occupations` で職業一覧が返る
- [ ] `POST /api/occupations/roll-stats` でダイス結果が返る
- [ ] `POST /api/sessions` で `character_id` を使ってセッション作成できる
- [ ] `POST /api/sessions/{id}/chat` に `[GAME_START]` を送るとオープニングが返る
- [ ] dice_requests がある場合、自動でダイスを振り第2AIコールが実行される
- [ ] `uv run pytest` が全通過
- [ ] `uv run ruff check . && uv run mypy .` がクリーン

### フロントエンド
- [ ] キャラクター管理画面でキャラクター作成・一覧・削除ができる
- [ ] ダイスロールアニメーション（数字がランダムにちらつくエフェクト）がある
- [ ] セッション作成時にキャラクターを選択できる
- [ ] ゲーム開始時にAIのオープニングが自動表示される
- [ ] ダイス結果カードが色分けで表示される
- [ ] NAVパネルにNPC一覧が表示される
- [ ] `npm run build` エラーなし

## 注意事項

- 既存の `ghostkeeper.db` を削除してから起動すること
- `Character.session_id` は nullable（テンプレートは NULL）
- セッション作成時はキャラクターをコピーし、オリジナルは変更しない
- `_coerce_data` の `dice_results` フィールド対応も忘れずに
- フロント側の `types/index.ts` に `DiceResult`, `Occupation`, `RolledStats` 型を追加すること
- `useGame.ts` のゲーム開始トリガー（`[GAME_START]`）は チャット履歴が空の時のみ送信
