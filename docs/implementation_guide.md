# GhostKeeper 実装ガイド（Phase 1〜3）

## 前提

- 作業ディレクトリ: `/home/perso/analysis/GhostKeeper`
- Backend: `backend/` 以下、Python 3.12、uv管理
- Frontend: `frontend/` 以下、React 19 + Vite 7 + TypeScript
- Ollama: ローカル起動済み前提（`http://localhost:11434`）
- DB: SQLite（`backend/ghostkeeper.db`）

実装前に必ず `tasks/todo.md` を確認し、完了タスクに `[x]` を付けること。
問題・学びは `tasks/lessons.md` に追記すること。

---

## Phase 1: バックエンド基盤

### ディレクトリ構成（作成すること）

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPIアプリ本体
│   ├── config.py         # 設定管理（Pydantic Settings）
│   ├── database.py       # SQLAlchemy engine / session
│   ├── api/
│   │   ├── __init__.py
│   │   ├── sessions.py   # セッションCRUD
│   │   ├── chat.py       # チャット送受信
│   │   ├── characters.py # キャラクター操作
│   │   └── images.py     # 画像一覧取得
│   ├── game/
│   │   ├── __init__.py
│   │   ├── dice.py       # ダイスロール
│   │   ├── rules.py      # CoC 7版ルール（判定・派生値計算）
│   │   └── stats.py      # キャラクターパラメータ操作
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── client.py     # Ollamaクライアント
│   │   ├── tools.py      # Tool Use 定義
│   │   ├── prompts.py    # システムプロンプト
│   │   └── schemas.py    # AI出力JSONスキーマ（Pydantic）
│   └── models/
│       ├── __init__.py
│       ├── session.py    # Sessionモデル
│       ├── character.py  # Characterモデル
│       ├── memory.py     # Memoryモデル
│       └── chat.py       # ChatHistoryモデル
├── tests/
│   ├── __init__.py
│   ├── test_dice.py
│   └── test_rules.py
├── pyproject.toml        # 既存（uvicorn / pytest を追加）
└── main.py               # 既存（削除して app/main.py に移行）
```

### 1-1. 依存パッケージ追加

`backend/pyproject.toml` の `dependencies` に以下を追加（`uv add` で追加する）:

```
uvicorn>=0.34
aiosqlite>=0.21
pytest>=8.0
pytest-asyncio>=0.24
httpx>=0.28        # テスト用
```

### 1-2. config.py

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5"
    database_url: str = "sqlite+aiosqlite:///./ghostkeeper.db"
    images_dir: str = "../images"
    scenarios_dir: str = "../scenarios"
    memory_context_limit: int = 20  # 会話履歴の最大保持件数

    class Config:
        env_file = ".env"

settings = Settings()
```

### 1-3. database.py

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### 1-4. SQLAlchemy モデル

#### models/session.py

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class ScenarioMode(str, enum.Enum):
    template = "template"
    free = "free"

class GameSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[ScenarioMode] = mapped_column(SAEnum(ScenarioMode), default=ScenarioMode.free)
    scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)  # テンプレートモード時
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    characters: Mapped[list["Character"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    chat_history: Mapped[list["ChatHistory"]] = relationship(back_populates="session", cascade="all, delete-orphan")
```

#### models/character.py

CoC 7版のパラメータを全て持つ。PCとNPCを同じモデルで管理。

```python
from sqlalchemy import String, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_pc: Mapped[bool] = mapped_column(Boolean, default=False)
    image_id: Mapped[str | None] = mapped_column(String, nullable=True)  # images/characters/{image_id}/

    # 基本値（3d6×5 or 2d6+6×5）
    str_: Mapped[int] = mapped_column("str", Integer, default=50)
    con: Mapped[int] = mapped_column(Integer, default=50)
    siz: Mapped[int] = mapped_column(Integer, default=50)
    int_: Mapped[int] = mapped_column("int", Integer, default=50)
    dex: Mapped[int] = mapped_column(Integer, default=50)
    pow_: Mapped[int] = mapped_column("pow", Integer, default=50)
    app: Mapped[int] = mapped_column(Integer, default=50)
    edu: Mapped[int] = mapped_column(Integer, default=50)
    luk: Mapped[int] = mapped_column(Integer, default=50)

    # 派生値（現在値）
    hp_max: Mapped[int] = mapped_column(Integer, default=10)
    hp_current: Mapped[int] = mapped_column(Integer, default=10)
    mp_max: Mapped[int] = mapped_column(Integer, default=10)
    mp_current: Mapped[int] = mapped_column(Integer, default=10)
    san_max: Mapped[int] = mapped_column(Integer, default=50)
    san_current: Mapped[int] = mapped_column(Integer, default=50)
    san_indefinite: Mapped[int] = mapped_column(Integer, default=0)  # 不定の狂気閾値

    # スキル: {"図書館": {"base": 25, "current": 45, "growth": False}, ...}
    skills: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped["GameSession"] = relationship(back_populates="characters")
```

#### models/memory.py

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["GameSession"] = relationship(back_populates="memories")
```

#### models/chat.py

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class MessageRole(str, enum.Enum):
    player = "player"
    gm = "gm"
    system = "system"

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # AIのJSON生出力
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["GameSession"] = relationship(back_populates="chat_history")
```

### 1-5. main.py

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.config import settings
from app.api import sessions, chat, characters, images
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="GhostKeeper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 画像フォルダを静的配信
images_path = os.path.abspath(settings.images_dir)
if os.path.exists(images_path):
    app.mount("/images", StaticFiles(directory=images_path), name="images")

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])
app.include_router(characters.router, prefix="/api/characters", tags=["characters"])
app.include_router(images.router, prefix="/api/images", tags=["images"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

### 1-6. APIエンドポイント仕様

#### api/sessions.py

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/sessions` | セッション一覧 |
| POST | `/api/sessions` | セッション作成（name, mode, scenario_id） |
| GET | `/api/sessions/{id}` | セッション詳細取得 |
| DELETE | `/api/sessions/{id}` | セッション削除 |

セッション作成時にPCキャラクターも同時生成する。
`id` は `uuid4()` で生成。

#### api/chat.py

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/sessions/{id}/chat` | 会話履歴取得 |
| POST | `/api/sessions/{id}/chat` | メッセージ送信（AI応答を返す） |

POST bodyの例:
```json
{"message": "図書館に向かい、クトゥルフ神話に関する文献を調べる"}
```

Response:
```json
{
  "gm_narration": "...",
  "npc_dialogues": [...],
  "dice_results": [...],
  "stat_updates": [...],
  "image": {...},
  "choices": [...]
}
```

#### api/images.py

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/images/characters` | キャラクター画像一覧（フォルダスキャン） |
| GET | `/api/images/scenes` | シーン画像一覧 |

---

## Phase 2: ゲームロジック

### 2-1. game/dice.py

```python
import random
from dataclasses import dataclass

@dataclass
class DiceResult:
    notation: str    # "2d6+3" 等
    rolls: list[int] # 各ダイスの目
    modifier: int    # 修正値
    total: int

def roll(notation: str) -> DiceResult:
    """
    "1d100", "2d6+3", "1d3" 等のダイス記法をパースしてロール。
    返り値: DiceResult
    """
    ...

def roll_d100() -> int:
    return random.randint(1, 100)
```

### 2-2. game/rules.py（CoC 7版ルール）

```python
from enum import Enum
from dataclasses import dataclass

class SkillCheckResult(str, Enum):
    CRITICAL = "critical"           # 1
    EXTREME = "extreme_success"     # 技能値の1/5以下
    HARD = "hard_success"           # 技能値の1/2以下
    SUCCESS = "success"             # 技能値以下
    FAILURE = "failure"             # 技能値超え
    FUMBLE = "fumble"               # 96-100（技能値<50の場合）または 100

@dataclass
class SkillCheckDetail:
    result: SkillCheckResult
    rolled: int
    skill_value: int
    threshold_critical: int    # = 1
    threshold_extreme: int     # = skill_value // 5
    threshold_hard: int        # = skill_value // 2

def skill_check(skill_value: int, difficulty: str = "normal") -> SkillCheckDetail:
    """
    difficulty: "normal" | "hard" | "extreme"
    hardの場合、実効技能値をskill_value//2に、
    extremeの場合skill_value//5に変えてロール。
    """
    ...

def calc_derived_stats(str_: int, con: int, siz: int, pow_: int) -> dict:
    """
    HP, MP, SAN, ダメージボーナス, ビルド, MOVを計算して返す。
    HP = floor((CON + SIZ) / 10)
    MP = floor(POW / 5)
    SAN = POW * 5
    ダメージボーナス / ビルド は STR+SIZ の合計値テーブルから算出。
    """
    ...

def san_check(san_current: int, success_loss: str, failure_loss: str, roll_result: SkillCheckResult) -> int:
    """
    SANチェック。成功時・失敗時のSAN喪失ダイスを受け取り、実際の喪失量を返す。
    success_loss, failure_loss は "1" や "1d6" 形式。
    """
    ...
```

**ダメージボーナス / ビルド テーブル（CoC 7版）:**

| STR+SIZ | ダメージボーナス | ビルド |
|---------|----------------|--------|
| 2-64    | -2             | -2     |
| 65-84   | -1             | -1     |
| 85-124  | 0              | 0      |
| 125-164 | +1d4           | 1      |
| 165-204 | +1d6           | 2      |
| 205+    | +2d6           | 3      |

**MOV テーブル:**
- DEX < SIZ かつ STR < SIZ → 7
- DEX >= SIZ または STR >= SIZ → 8
- DEX > SIZ かつ STR > SIZ → 9
- 40歳以上は1減少

### 2-3. テスト

`tests/test_dice.py` と `tests/test_rules.py` を作成し、主要なロジックをテストすること。
例:
- `test_skill_check_critical`: roll=1 → CRITICAL
- `test_skill_check_fumble`: roll=100、技能値49 → FUMBLE
- `test_calc_derived_stats`: 正しいHP/MP/SAN が返るか
- `test_roll_notation`: "2d6+3" のパース・ロール

---

## Phase 3: AI連携

### 3-1. ai/schemas.py（Pydantic）

AI出力の検証に使うPydanticモデルを定義する。

```python
from pydantic import BaseModel
from typing import Literal

class NpcDialogue(BaseModel):
    character: str
    message: str
    emotion: Literal["normal", "scared", "angry", "dead"] = "normal"

class DiceRequest(BaseModel):
    type: str           # "1d100"
    skill: str
    character: str
    difficulty: Literal["normal", "hard", "extreme"] = "normal"

class StatUpdate(BaseModel):
    target: str
    field: Literal["hp", "san", "mp"]
    delta: int
    reason: str

class ImageRef(BaseModel):
    type: Literal["character", "scene"]
    id: str
    expression: str = "normal"

class AIResponse(BaseModel):
    thinking: str = ""
    gm_narration: str
    npc_dialogues: list[NpcDialogue] = []
    dice_requests: list[DiceRequest] = []
    stat_updates: list[StatUpdate] = []
    image: ImageRef | None = None
    choices: list[str] = []
    game_event: Literal["none", "combat_start", "san_check", "skill_check", "scenario_end"] = "none"
```

### 3-2. ai/tools.py（Tool Use定義）

Ollamaのtool calling形式でツールを定義する。

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "指定したダイスを振る。例: 1d100, 2d6+3",
            "parameters": {
                "type": "object",
                "properties": {
                    "notation": {"type": "string", "description": "ダイス記法 (例: '1d100', '2d6')"},
                },
                "required": ["notation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_check",
            "description": "キャラクターの技能判定を行う",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "skill_name": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["normal", "hard", "extreme"]},
                },
                "required": ["character_id", "skill_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_character_stats",
            "description": "キャラクターのパラメータを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                },
                "required": ["character_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_stats",
            "description": "キャラクターのHP/SAN/MPを増減させる",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "field": {"type": "string", "enum": ["hp", "san", "mp"]},
                    "delta": {"type": "integer", "description": "変化量（負=減少）"},
                    "reason": {"type": "string"},
                },
                "required": ["character_id", "field", "delta", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_memory",
            "description": "重要なイベントをセッション記憶に追加する",
            "parameters": {
                "type": "object",
                "properties": {
                    "event": {"type": "string"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["event"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "過去の記憶イベントをキーワード検索する",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_image",
            "description": "キャラクターまたはシーンの画像パスを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["character", "scene"]},
                    "id": {"type": "string"},
                    "expression": {"type": "string", "enum": ["normal", "scared", "angry", "dead"]},
                },
                "required": ["type", "id"],
            },
        },
    },
]
```

### 3-3. ai/prompts.py

```python
SYSTEM_PROMPT = """
あなたはクトゥルフ神話TRPGのゲームマスター（GM）です。
CoC 7版のルールに従い、1920年代の探索シナリオを進行します。

## 役割
- GMとして状況・場所・NPCの行動を描写する
- 必要に応じてNPCのセリフを演じる
- プレイヤーの行動に対してルールに従った判定を行う
- SANチェック・技能ロール・ダメージ計算を適切に実施する

## 出力形式
必ず以下のJSON形式で応答すること。自然言語の混在は禁止。

{
  "thinking": "内部推論（プレイヤーには表示しない）",
  "gm_narration": "GMの描写・ナレーション（日本語）",
  "npc_dialogues": [...],
  "dice_requests": [...],
  "stat_updates": [...],
  "image": null or {...},
  "choices": ["選択肢A", "選択肢B"],
  "game_event": "none"
}

## ゲームルール（CoC 7版）
- 技能判定: 1d100 ≤ 技能値で成功
- クリティカル: 1
- ファンブル: 96-100（技能値<50時）または100
- SAN喪失は神話的存在との遭遇・目撃で発生

## 注意事項
- 描写は日本語で行う
- 恐怖・狂気・不条理を適切に演出する
- プレイヤーに選択の余地を常に与える
"""

def build_messages(
    chat_history: list[dict],
    player_message: str,
    character_summary: str,
    memories: list[str],
) -> list[dict]:
    """
    Ollama に渡すメッセージリストを構築する。
    - system: SYSTEM_PROMPT + キャラクター情報 + 記憶
    - history: 直近N件の会話
    - user: 今回のプレイヤーメッセージ
    """
    system_content = SYSTEM_PROMPT + f"\n\n## 探索者情報\n{character_summary}"
    if memories:
        system_content += "\n\n## 重要な記憶\n" + "\n".join(f"- {m}" for m in memories)

    messages = [{"role": "system", "content": system_content}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": player_message})
    return messages
```

### 3-4. ai/client.py

```python
import json
from ollama import AsyncClient
from app.config import settings
from app.ai.schemas import AIResponse
from app.ai.tools import TOOLS
from app.ai.prompts import build_messages

class GmClient:
    def __init__(self):
        self.client = AsyncClient(host=settings.ollama_base_url)
        self.model = settings.ollama_model

    async def chat(
        self,
        player_message: str,
        chat_history: list[dict],
        character_summary: str,
        memories: list[str],
        tool_handler,  # callable: tool_name, args -> result
    ) -> AIResponse:
        """
        1. Ollamaにメッセージ送信（Tool Use有効、format=json）
        2. ツール呼び出しがあれば tool_handler で処理してループ
        3. 最終応答をAIResponseにパースして返す
        """
        messages = build_messages(chat_history, player_message, character_summary, memories)

        while True:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                format="json",
                options={"temperature": 0.8},
            )

            msg = response.message

            # ツール呼び出し処理
            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
                for tool_call in msg.tool_calls:
                    result = await tool_handler(
                        tool_call.function.name,
                        tool_call.function.arguments,
                    )
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                continue  # 再度AIに送信

            # 最終応答をパース
            raw = msg.content or "{}"
            data = json.loads(raw)
            return AIResponse(**data)
```

### 3-5. api/chat.py でのツールハンドラー統合

`POST /api/sessions/{id}/chat` の実装で、以下のツールハンドラーを定義してGmClientに渡す：

```python
async def tool_handler(session_id: str, db: AsyncSession):
    async def handle(tool_name: str, args: dict):
        if tool_name == "roll_dice":
            from app.game.dice import roll
            result = roll(args["notation"])
            return {"rolls": result.rolls, "total": result.total}

        elif tool_name == "skill_check":
            # DBからキャラクター取得 → 技能値取得 → skill_check実行
            ...

        elif tool_name == "get_character_stats":
            # DBからキャラクター取得してdict返す
            ...

        elif tool_name == "update_stats":
            # DBでHP/SAN/MP更新
            ...

        elif tool_name == "add_memory":
            # Memoryレコード作成
            ...

        elif tool_name == "search_memory":
            # Memoryテーブルをキーワードで検索（LIKE）
            ...

        elif tool_name == "get_image":
            # images/{type}s/{id}/{expression}.png の存在確認してパス返す
            ...

        return {"error": f"unknown tool: {tool_name}"}
    return handle
```

---

## 完了条件

以下を満たしたら Phase 1〜3 完了とする：

- [ ] `cd backend && uv run uvicorn app.main:app --reload` でサーバー起動
- [ ] `GET /api/health` → `{"status": "ok"}`
- [ ] `uv run pytest` でゲームロジックのテストが全通過
- [ ] `uv run ruff check . && uv run mypy .` でエラーなし
- [ ] `POST /api/sessions` でセッション・PC作成ができる
- [ ] `POST /api/sessions/{id}/chat` でOllamaとの往復が動作する（Ollama起動必須）

---

## 注意事項

- `backend/main.py`（既存のHello World）は `backend/app/main.py` に置き換えること
- SQLite非同期アクセスのため `aiosqlite` が必要（uvicorn起動前に `uv add aiosqlite` する）
- Ollamaのtool callingはモデルによって挙動が異なる。Qwen3はサポート済みだが、応答が純粋なJSONでない場合はthinkingタグ（`<think>...</think>`）を除去してからパースすること
- `format="json"` を指定してもスキーマを満たさない場合がある。パース失敗時はgm_narationのみの最小レスポンスにフォールバックする
