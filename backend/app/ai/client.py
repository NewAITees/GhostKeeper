"""
モジュール名: ai/client.py
目的: Ollama GM クライアント（Tool Use ループ付き）

使い方:
    from app.ai.client import GmClient

    client = GmClient()
    response = await client.chat(
        player_message="...",
        chat_history=[],
        character_summary="...",
        memories=[],
        tool_handler=my_handler,
    )

依存:
    - ollama (AsyncClient)
    - app.ai.schemas.AIResponse
    - app.ai.tools.TOOLS
    - app.ai.prompts.build_messages

注意:
    - Qwen3 の thinking タグ（<think>...</think>）は JSON パース前に除去
    - パース失敗時は gm_narration のみの最小レスポンスにフォールバック
    - Ollama 未起動時は API 呼び出し時に ConnectionError が発生する（サーバー起動には影響しない）
"""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from ollama import AsyncClient

from app.ai.prompts import build_messages
from app.ai.schemas import AIResponse
from app.config import settings

logger = logging.getLogger(__name__)

# thinking タグ除去パターン
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Qwen3 の <think>...</think> タグを除去する。"""
    return _THINK_RE.sub("", text).strip()


def _coerce_data(data: dict) -> AIResponse:
    """
    モデルの出力揺れを吸収して AIResponse を返す。
    各フィールドの型ずれは空値にフォールバックする。
    """
    # npc_dialogues: 文字列 → {"character": "???", "message": str} に変換
    raw_npc = data.get("npc_dialogues", [])
    fixed_npc: list[dict] = []
    if isinstance(raw_npc, list):
        for item in raw_npc:
            if isinstance(item, str):
                fixed_npc.append({"character": "???", "message": item})
            elif isinstance(item, dict) and "message" in item:
                fixed_npc.append(item)
    data["npc_dialogues"] = fixed_npc

    # dice_requests: 必須フィールド(type,skill,character)がなければスキップ
    raw_dice = data.get("dice_requests", [])
    fixed_dice: list[dict] = []
    if isinstance(raw_dice, list):
        for item in raw_dice:
            if (
                isinstance(item, dict)
                and "type" in item
                and "skill" in item
                and "character" in item
            ):
                fixed_dice.append(item)
    data["dice_requests"] = fixed_dice

    # stat_updates: 必須フィールド(target,field,delta,reason)がなければスキップ
    raw_stat = data.get("stat_updates", [])
    fixed_stat: list[dict] = []
    if isinstance(raw_stat, list):
        for item in raw_stat:
            if isinstance(item, dict) and all(
                k in item for k in ("target", "field", "delta", "reason")
            ):
                fixed_stat.append(item)
    data["stat_updates"] = fixed_stat

    # image: 必須フィールド(type,id)がなければ None に
    raw_img = data.get("image")
    if isinstance(raw_img, dict) and not ("type" in raw_img and "id" in raw_img):
        data["image"] = None

    # game_event: モデルの出力揺れを吸収して正規化
    _GAME_EVENT_ALIASES: dict[str, str] = {
        "sanity_check": "san_check",
        "sancheck": "san_check",
        "san": "san_check",
        "combat": "combat_start",
        "combat_begin": "combat_start",
        "end": "scenario_end",
        "scenario_complete": "scenario_end",
    }
    _VALID_GAME_EVENTS = {
        "none",
        "combat_start",
        "san_check",
        "skill_check",
        "scenario_end",
    }
    raw_event = data.get("game_event", "none")
    if raw_event not in _VALID_GAME_EVENTS:
        data["game_event"] = _GAME_EVENT_ALIASES.get(str(raw_event).lower(), "none")

    # choices: 文字列リスト以外は空に
    raw_choices = data.get("choices", [])
    if not isinstance(raw_choices, list):
        data["choices"] = []
    else:
        data["choices"] = [c for c in raw_choices if isinstance(c, str)]

    # dice_results: 必須フィールドチェック（フロントエンド表示用の実際のダイス結果）
    # この値はバックエンドが追加するため AI 出力には含まれない場合が多い
    raw_dice_results = data.get("dice_results", [])
    if not isinstance(raw_dice_results, list):
        data["dice_results"] = []
    else:
        fixed_dice_results: list[dict] = []
        for item in raw_dice_results:
            if isinstance(item, dict):
                fixed_dice_results.append(item)
        data["dice_results"] = fixed_dice_results

    # turn_summary / session_summary は dict 以外を無効化
    if not isinstance(data.get("turn_summary"), dict):
        data["turn_summary"] = None
    if not isinstance(data.get("session_summary"), dict):
        data["session_summary"] = None

    return AIResponse(**data)


def _parse_ai_response(raw: str) -> AIResponse:
    """
    AI の生出力を AIResponse にパースする。
    1. <think>タグを除去
    2. JSON パース
    3. Qwen3 が gm_narration 内に JSON を二重埋め込みした場合は再パース
    4. フィールドの型ずれを正規化
    5. 全失敗時はナレーションのみのフォールバック
    """
    cleaned = _strip_thinking(raw)
    try:
        data = json.loads(cleaned)

        # Qwen3 が gm_narration の中に本来の JSON を埋め込むケースを処理
        gm = data.get("gm_narration", "")
        if isinstance(gm, str) and gm.strip().startswith("{"):
            try:
                inner_data = json.loads(gm.strip())
                if "gm_narration" in inner_data:
                    logger.info(
                        "Detected nested JSON in gm_narration — re-parsing inner data"
                    )
                    return _coerce_data(inner_data)
            except (json.JSONDecodeError, Exception):
                pass

        return _coerce_data(data)

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(
            "AI response parse failed: %s — falling back to minimal response", e
        )
        narration = cleaned if cleaned else "（応答の解析に失敗しました）"
        return AIResponse(gm_narration=narration)


ToolHandler = Callable[[str, dict[str, Any]], Awaitable[Any]]


class GmClient:
    """Ollama GM クライアント。Tool Use ループを管理する。"""

    def __init__(self) -> None:
        self.client = AsyncClient(host=settings.ollama_base_url)
        self.model = settings.ollama_model

    async def chat(
        self,
        player_message: str,
        chat_history: list[dict[str, str]],
        character_summary: str,
        memories: list[str],
        tool_handler: ToolHandler,
        scenario: dict | None = None,
        npcs: list[dict] | None = None,
    ) -> AIResponse:
        """
        1. Ollama にメッセージ送信（Tool Use 有効、format=json）
        2. ツール呼び出しがあれば tool_handler で処理してループ
        3. 最終応答を AIResponse にパースして返す
        """
        messages: list[dict[str, Any]] = build_messages(  # type: ignore[assignment]
            chat_history, player_message, character_summary, memories, scenario, npcs
        )

        logger.info(
            "GmClient.chat: model=%s, history_len=%d", self.model, len(chat_history)
        )

        # tools + format="json" の同時指定は Qwen3 と相性問題があるため
        # format="json" のみで JSON 出力を強制する（ツール呼び出しは JSON フィールドで代替）
        response = await self.client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": 0.8},
        )

        raw = response.message.content or "{}"
        logger.debug("AI response (raw len=%d): %s", len(raw), raw[:200])
        return _parse_ai_response(raw)

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
        messages: list[dict] = list(previous_messages)
        # 第1応答をアシスタントのメッセージとして追加
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {"gm_narration": first_narration}, ensure_ascii=False
                ),
            }
        )
        # ダイス結果をユーザーメッセージとして追加
        messages.append(
            {
                "role": "user",
                "content": (
                    f"ダイスロール結果:\n{dice_results_text}\n\n"
                    "上記の結果を踏まえて、続きを語ってください。"
                    "成功・失敗・クリティカル・ファンブルに応じて劇的に描写を変えてください。"
                ),
            }
        )

        logger.info(
            "GmClient.chat_with_dice_result: model=%s, dice_text=%s",
            self.model,
            dice_results_text[:100],
        )
        response = await self.client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": 0.8},
        )
        raw = response.message.content or "{}"
        logger.debug("AI dice_result response (raw len=%d): %s", len(raw), raw[:200])
        return _parse_ai_response(raw)
