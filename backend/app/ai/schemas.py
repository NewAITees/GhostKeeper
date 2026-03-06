"""
モジュール名: ai/schemas.py
目的: AI出力JSONスキーマ（Pydantic バリデーションモデル）

使い方:
    from app.ai.schemas import AIResponse

    response = AIResponse(**json_data)

依存:
    - pydantic

注意:
    - AIResponse は GmClient.chat() の返り値型
    - パース失敗時はフォールバック用の最小レスポンスを作成すること
"""

from typing import Any, Literal

from pydantic import BaseModel


class NpcDialogue(BaseModel):
    character: str
    message: str
    emotion: Literal["normal", "scared", "angry", "dead"] = "normal"


class DiceRequest(BaseModel):
    type: str
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


class DiceResult(BaseModel):
    """実際に振ったダイスの結果（フロントエンド表示用）"""

    skill: str | None = None
    type: str | None = None
    rolled: int | None = None
    total: int | None = None
    skill_value: int | None = None
    result: str | None = None  # "success", "failure" など
    result_ja: str | None = None  # "成功", "失敗" など
    rolls: list[int] | None = None  # 各ダイスの目


class AIResponse(BaseModel):
    thinking: str = ""
    gm_narration: str
    npc_dialogues: list[NpcDialogue] = []
    dice_requests: list[DiceRequest] = []
    stat_updates: list[StatUpdate] = []
    image: ImageRef | None = None
    choices: list[str] = []
    game_event: Literal[
        "none", "combat_start", "san_check", "skill_check", "scenario_end"
    ] = "none"
    dice_results: list[DiceResult] = []  # 実際のダイス結果（フロントエンド表示用）
    turn_summary: dict[str, Any] | None = None
    session_summary: dict[str, Any] | None = None
