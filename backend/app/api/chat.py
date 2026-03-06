"""
モジュール名: api/chat.py
目的: チャット送受信 API エンドポイント（AI ツールハンドラー統合）

エンドポイント:
    GET  /api/sessions/{id}/chat  - 会話履歴取得
    POST /api/sessions/{id}/chat  - メッセージ送信（AI 応答を返す）

依存:
    - app.ai.client.GmClient
    - app.game.dice, rules, stats
    - app.models.*
    - app.database.get_db

注意:
    - [GAME_START] トリガー: プレイヤーメッセージは DB 保存せず、オープニングナレーションを返す
    - ツールハンドラーはクロージャで session_id と db を束縛
    - GmClient はリクエストごとにインスタンス化（スレッドセーフ）
    - Ollama 未起動時は ConnectionError / ConnectError を 503 として返す
    - 2段階ダイスフロー: AI→ダイス実行→AI（結果を受けて続き）
"""

import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.client import GmClient
from app.ai.prompts import build_messages
from app.ai.schemas import AIResponse, DiceResult, StatUpdate
from app.config import settings
from app.database import get_db
from app.game.dice import roll
from app.game.rules import san_check, skill_check
from app.game.stats import (
    apply_stat_delta,
    build_character_summary,
    get_stat_field,
    set_stat_field,
)
from app.models.character import Character
from app.models.chat import ChatHistory, MessageRole
from app.models.memory import Memory
from app.models.session import GameSession

logger = logging.getLogger(__name__)
router = APIRouter()

GAME_START_TRIGGER = "[GAME_START]"


class ChatSend(BaseModel):
    message: str


ToolHandler = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _make_tool_handler(session_id: str, db: AsyncSession) -> ToolHandler:
    """
    session_id と db を束縛したツールハンドラーを返す。
    """

    async def handle(tool_name: str, args: dict[str, Any]) -> Any:
        logger.info("tool_handler: %s args=%s", tool_name, args)

        if tool_name == "roll_dice":
            result = roll(args["notation"])
            return {
                "rolls": result.rolls,
                "total": result.total,
                "notation": result.notation,
            }

        elif tool_name == "skill_check":
            char_id: str = args["character_id"]
            skill_name: str = args["skill_name"]
            difficulty: str = args.get("difficulty", "normal")

            res = await db.execute(select(Character).where(Character.id == char_id))
            character = res.scalar_one_or_none()
            if character is None:
                return {"error": f"character not found: {char_id}"}

            skills: dict[str, Any] = character.skills or {}
            skill_data = skills.get(skill_name, {})
            if isinstance(skill_data, dict):
                raw_val = skill_data.get("current", skill_data.get("base", 25))
            else:
                raw_val = skill_data
            skill_value: int = int(raw_val) if raw_val is not None else 25

            detail = skill_check(skill_value, difficulty)
            return {
                "result": detail.result.value,
                "rolled": detail.rolled,
                "skill_value": detail.skill_value,
                "skill_name": skill_name,
            }

        elif tool_name == "get_character_stats":
            char_id = args["character_id"]
            res = await db.execute(select(Character).where(Character.id == char_id))
            character = res.scalar_one_or_none()
            if character is None:
                return {"error": f"character not found: {char_id}"}
            return {
                "id": character.id,
                "name": character.name,
                "hp": {"current": character.hp_current, "max": character.hp_max},
                "mp": {"current": character.mp_current, "max": character.mp_max},
                "san": {"current": character.san_current, "max": character.san_max},
                "skills": character.skills,
            }

        elif tool_name == "update_stats":
            char_id = args["character_id"]
            field: str = args["field"]
            delta: int = int(args["delta"])
            reason: str = args.get("reason", "")

            res = await db.execute(select(Character).where(Character.id == char_id))
            character = res.scalar_one_or_none()
            if character is None:
                return {"error": f"character not found: {char_id}"}

            current, max_val = get_stat_field(character, field)
            new_val = apply_stat_delta(current, delta, max_val)
            set_stat_field(character, field, new_val)
            await db.commit()
            logger.info(
                "update_stats: %s.%s %d -> %d (reason=%s)",
                char_id,
                field,
                current,
                new_val,
                reason,
            )
            return {
                "field": field,
                "before": current,
                "after": new_val,
                "reason": reason,
            }

        elif tool_name == "add_memory":
            event: str = args["event"]
            importance: int = int(args.get("importance", 1))
            memory = Memory(session_id=session_id, event=event, importance=importance)
            db.add(memory)
            await db.commit()
            logger.info("add_memory: session=%s, importance=%d", session_id, importance)
            return {"status": "ok", "event": event}

        elif tool_name == "search_memory":
            query: str = args["query"]
            mem_search_res = await db.execute(
                select(Memory)
                .where(Memory.session_id == session_id)
                .where(Memory.event.contains(query))
                .order_by(Memory.importance.desc(), Memory.created_at.desc())
                .limit(10)
            )
            found_memories: list[Memory] = list(mem_search_res.scalars().all())
            return {
                "memories": [
                    {"event": fm.event, "importance": fm.importance}
                    for fm in found_memories
                ]
            }

        elif tool_name == "get_image":
            img_type: str = args["type"]
            img_id: str = args["id"]
            expression: str = args.get("expression", "normal")
            base_dir = os.path.abspath(settings.images_dir)

            if img_type == "character":
                for ext in ("png", "jpg", "jpeg", "webp"):
                    rel_path = f"characters/{img_id}/{expression}.{ext}"
                    full_path = os.path.join(base_dir, rel_path)
                    if os.path.exists(full_path):
                        return {"url": f"/images/{rel_path}", "found": True}
            elif img_type == "scene":
                for ext in ("png", "jpg", "jpeg", "webp"):
                    rel_path = f"scenes/{img_id}.{ext}"
                    full_path = os.path.join(base_dir, rel_path)
                    if os.path.exists(full_path):
                        return {"url": f"/images/{rel_path}", "found": True}

            return {"url": None, "found": False}

        elif tool_name == "update_npc_memory":
            char_id = args["character_id"]
            event_text: str = args["event"]
            res = await db.execute(select(Character).where(Character.id == char_id))
            npc = res.scalar_one_or_none()
            if npc:
                mem: dict = npc.npc_memory or {"events": []}
                mem.setdefault("events", []).append(event_text)
                npc.npc_memory = mem
                await db.commit()
                logger.info("update_npc_memory: char=%s, event=%s", char_id, event_text)
            return {"status": "ok"}

        return {"error": f"unknown tool: {tool_name}"}

    return handle


def _result_to_ja(result: str) -> str:
    return {
        "critical": "クリティカル！",
        "extreme_success": "イクストリーム成功",
        "hard_success": "ハード成功",
        "success": "成功",
        "failure": "失敗",
        "fumble": "ファンブル！",
    }.get(result, result)


def _pc_stats_snapshot(pc: Character) -> dict[str, dict[str, int]]:
    return {
        "hp": {"current": pc.hp_current, "max": pc.hp_max},
        "san": {"current": pc.san_current, "max": pc.san_max},
        "mp": {"current": pc.mp_current, "max": pc.mp_max},
    }


def _extract_skill_value(
    character: Character, skill_name: str, default: int = 25
) -> int:
    skills: dict = character.skills or {}
    skill_data = skills.get(skill_name, {})
    if isinstance(skill_data, dict):
        raw_val = skill_data.get("current", skill_data.get("base", default))
    else:
        raw_val = skill_data
    return int(raw_val) if raw_val is not None else default


def _detect_combat_action(player_message: str) -> str | None:
    msg = player_message.strip()
    if any(k in msg for k in ("攻撃", "attack", "たたか", "殴")):
        return "attack"
    if any(k in msg for k in ("回避", "evade", "避け")):
        return "evade"
    if any(k in msg for k in ("組みつき", "grapple", "捕ま")):
        return "grapple"
    if any(k in msg for k in ("逃走", "逃げ", "run", "離脱")):
        return "escape"
    if any(k in msg for k in ("降伏", "surrender")):
        return "surrender"
    return None


def _apply_update(character: Character, field: str, delta: int) -> tuple[int, int]:
    current, max_val = get_stat_field(character, field)
    new_val = apply_stat_delta(current, delta, max_val)
    set_stat_field(character, field, new_val)
    return current, new_val


async def _execute_dice_requests(
    ai_response: AIResponse,
    pc: Character,
) -> tuple[list[DiceResult], str, list[StatUpdate]]:
    """
    AIのdice_requestsを実行してダイス結果と説明テキストを返す。
    併せて stat_updates を適用し、実際に反映した更新のみ返す。
    """
    results: list[DiceResult] = []
    lines: list[str] = []
    applied_updates: list[StatUpdate] = []

    for req in ai_response.dice_requests:
        if req.skill and req.character in ("pc", pc.name, pc.id):
            skill_val = _extract_skill_value(pc, req.skill)
            detail = skill_check(skill_val, req.difficulty)
            result_ja = _result_to_ja(detail.result.value)
            results.append(
                DiceResult(
                    skill=req.skill,
                    rolled=detail.rolled,
                    skill_value=skill_val,
                    result=detail.result.value,
                    result_ja=result_ja,
                )
            )
            lines.append(
                f"【{req.skill}判定】1d100={detail.rolled} vs {skill_val} → {result_ja}"
            )
            continue

        dice_result = roll(req.type or "1d6")
        results.append(
            DiceResult(
                type=req.type,
                rolls=dice_result.rolls,
                total=dice_result.total,
            )
        )
        lines.append(f"【{req.type}】= {dice_result.total}（{dice_result.rolls}）")

    for upd in ai_response.stat_updates:
        if upd.target in ("pc", pc.name, pc.id):
            before, after = _apply_update(pc, upd.field, upd.delta)
            applied_updates.append(
                StatUpdate(
                    target="pc",
                    field=upd.field,
                    delta=after - before,
                    reason=upd.reason,
                )
            )

    return results, "\n".join(lines), applied_updates


def _resolve_san_event(
    ai_response: AIResponse,
    pc: Character,
    npc_models: list[Character] | None = None,
) -> tuple[list[DiceResult], list[StatUpdate], str]:
    # デフォルト喪失値
    success_loss = "1"
    failure_loss = "1d6"

    # AIがdice_requests.typeに "成功値/失敗値" 形式で指定した場合は優先採用
    for req in ai_response.dice_requests:
        if req.skill.upper() == "SAN" and "/" in req.type:
            parts = req.type.split("/", 1)
            if len(parts) == 2:
                success_loss = parts[0].strip() or "1"
                failure_loss = parts[1].strip() or "1d6"
            break
    else:
        # AI未指定の場合: 現在のシーンにいるモンスターのnpc_memoryから取得
        if npc_models:
            for npc in npc_models:
                mem = npc.npc_memory or {}
                if mem.get("role") == "monster":
                    success_loss = mem.get("san_loss_success", "1")
                    failure_loss = mem.get("san_loss_failure", "1d6")
                    break

    san_value = pc.san_current
    detail = skill_check(san_value, "normal")
    loss = san_check(san_value, success_loss, failure_loss, detail.result)
    before, after = _apply_update(pc, "san", -loss)

    dice = DiceResult(
        skill="SAN",
        rolled=detail.rolled,
        skill_value=san_value,
        result=detail.result.value,
        result_ja=_result_to_ja(detail.result.value),
    )
    upd = StatUpdate(
        target="pc",
        field="san",
        delta=after - before,
        reason=f"SANチェック({success_loss}/{failure_loss})",
    )
    line = (
        f"【SANチェック】1d100={detail.rolled} vs {san_value} → {dice.result_ja} / "
        f"SAN{before}->{after}"
    )
    return [dice], [upd], line


def _resolve_skill_event(
    ai_response: AIResponse,
    pc: Character,
) -> tuple[list[DiceResult], str]:
    skill_name = "目星"
    difficulty = "normal"
    for req in ai_response.dice_requests:
        if req.character in ("pc", pc.name, pc.id) and req.skill:
            skill_name = req.skill
            difficulty = req.difficulty
            break

    skill_value = _extract_skill_value(pc, skill_name)
    detail = skill_check(skill_value, difficulty)
    dice = DiceResult(
        skill=skill_name,
        rolled=detail.rolled,
        skill_value=skill_value,
        result=detail.result.value,
        result_ja=_result_to_ja(detail.result.value),
    )
    line = (
        f"【技能判定:{skill_name}】1d100={detail.rolled} vs {skill_value}"
        f"({difficulty}) → {dice.result_ja}"
    )
    return [dice], line


def _resolve_combat_event(
    player_message: str,
    pc: Character,
    npcs: list[Character],
) -> tuple[list[DiceResult], list[StatUpdate], list[str], list[str]]:
    choices = ["攻撃する", "回避する", "組みつきを試みる", "逃走する", "降伏する"]
    if not npcs:
        return [], [], ["敵が存在しないため戦闘処理をスキップしました。"], choices

    target = npcs[0]
    order = sorted([pc, target], key=lambda c: c.dex, reverse=True)
    notes = [f"イニシアチブ順: {' → '.join(c.name for c in order)}"]
    dice_results: list[DiceResult] = []
    stat_updates: list[StatUpdate] = []

    action = _detect_combat_action(player_message)
    if action is None:
        notes.append(
            "行動未指定のため、次のターンで攻撃/回避/組みつき/逃走/降伏を選択してください。"
        )
        return dice_results, stat_updates, notes, choices

    if action in ("escape", "surrender"):
        notes.append("戦闘を終了しました。")
        return dice_results, stat_updates, notes, []

    if action == "attack":
        atk_skill = _extract_skill_value(pc, "格闘（拳）", 25)
        atk = skill_check(atk_skill, "normal")
        dice_results.append(
            DiceResult(
                skill="格闘（拳）",
                rolled=atk.rolled,
                skill_value=atk_skill,
                result=atk.result.value,
                result_ja=_result_to_ja(atk.result.value),
            )
        )
        if atk.result.value in {
            "critical",
            "extreme_success",
            "hard_success",
            "success",
        }:
            dmg = roll("1d3").total
            before, after = _apply_update(target, "hp", -dmg)
            stat_updates.append(
                StatUpdate(
                    target=target.name,
                    field="hp",
                    delta=after - before,
                    reason="PCの攻撃ダメージ",
                )
            )
            notes.append(f"{target.name}に{dmg}ダメージ（HP {before}->{after}）")
        else:
            notes.append("攻撃は失敗しました。")

    if action == "evade":
        evade_skill = _extract_skill_value(pc, "回避", 20)
        evade = skill_check(evade_skill, "normal")
        dice_results.append(
            DiceResult(
                skill="回避",
                rolled=evade.rolled,
                skill_value=evade_skill,
                result=evade.result.value,
                result_ja=_result_to_ja(evade.result.value),
            )
        )
        if evade.result.value in {
            "critical",
            "extreme_success",
            "hard_success",
            "success",
        }:
            notes.append("回避に成功しました。")
        else:
            dmg = roll("1d3").total
            before, after = _apply_update(pc, "hp", -dmg)
            stat_updates.append(
                StatUpdate(
                    target="pc",
                    field="hp",
                    delta=after - before,
                    reason="敵の攻撃ダメージ",
                )
            )
            notes.append(f"回避失敗、{dmg}ダメージ（HP {before}->{after}）")

    if action == "grapple":
        grap_skill = _extract_skill_value(pc, "組みつき", 25)
        grap = skill_check(grap_skill, "normal")
        dice_results.append(
            DiceResult(
                skill="組みつき",
                rolled=grap.rolled,
                skill_value=grap_skill,
                result=grap.result.value,
                result_ja=_result_to_ja(grap.result.value),
            )
        )
        if grap.result.value in {
            "critical",
            "extreme_success",
            "hard_success",
            "success",
        }:
            notes.append(f"{target.name}を拘束しました。")
        else:
            notes.append("組みつきに失敗しました。")

    if target.hp_current <= 0:
        notes.append(f"{target.name}のHPが0になり戦闘終了。")
        choices = []
    elif pc.hp_current <= 0:
        notes.append("探索者のHPが0になり戦闘不能。戦闘終了。")
        choices = []

    return dice_results, stat_updates, notes, choices


async def _build_full_session_summary(
    session_id: str, db: AsyncSession
) -> dict[str, Any]:
    chat_res = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    logs = list(chat_res.scalars().all())
    mem_res = await db.execute(
        select(Memory)
        .where(Memory.session_id == session_id)
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(20)
    )
    memories = list(mem_res.scalars().all())

    conversation_log = [
        {
            "role": r.role.value,
            "content": r.content,
            "created_at": r.created_at.isoformat(),
        }
        for r in logs
    ]

    stat_history: list[dict[str, Any]] = []
    important_events: list[str] = []
    turn = 0
    for row in logs:
        if not row.raw_ai_response:
            continue
        try:
            parsed = json.loads(row.raw_ai_response)
        except json.JSONDecodeError:
            continue
        turn += 1
        summary = parsed.get("turn_summary") or {}
        if isinstance(summary, dict) and isinstance(summary.get("current_stats"), dict):
            stat_history.append(
                {
                    "turn": turn,
                    "created_at": row.created_at.isoformat(),
                    "current_stats": summary.get("current_stats"),
                    "stat_delta": summary.get("stat_delta", {}),
                }
            )
        event = parsed.get("game_event", "none")
        if event and event != "none":
            important_events.append(f"{row.created_at.isoformat()} {event}")

    important_events.extend(
        f"{m.created_at.isoformat()} memory: {m.event}" for m in memories
    )

    return {
        "conversation_log": conversation_log,
        "stat_history": stat_history,
        "important_events": important_events,
    }


@router.get("/{session_id}/chat")
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """会話履歴を返す（古い順）。"""
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "role": r.role.value,
            "content": r.content,
            "created_at": r.created_at,
        }
        for r in records
    ]


@router.post("/{session_id}/chat")
async def send_chat(
    session_id: str,
    body: ChatSend,
    db: AsyncSession = Depends(get_db),
) -> AIResponse:
    """
    プレイヤーメッセージを受け取り、AI 応答を返す。

    処理フロー:
    1. セッション存在確認
    2. [GAME_START] トリガー判定
    3. キャラクター情報・記憶取得
    4. AI 呼び出し（第1回）
    5. dice_requests があれば実行して第2AI呼び出し
    6. 会話履歴保存
    7. AIResponse を返す
    """
    logger.info("send_chat: session=%s, message=%s", session_id, body.message[:50])

    is_game_start = body.message.strip() == GAME_START_TRIGGER

    # セッション存在確認
    res = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.characters))
    )
    session = res.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # キャラクターサマリー
    character_summary = "\n".join(
        build_character_summary(c) for c in session.characters
    )

    # NPC一覧（is_pc=False のキャラクター）
    npcs = [
        {
            "id": c.id,
            "name": c.name,
            "role": c.occupation or "",
            "personality": c.personality,
            "npc_memory": c.npc_memory or {},
        }
        for c in session.characters
        if not c.is_pc
    ]

    # 直近の記憶
    mem_res = await db.execute(
        select(Memory)
        .where(Memory.session_id == session_id)
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(settings.memory_context_limit)
    )
    memories = [m.event for m in mem_res.scalars().all()]

    # 会話履歴（直近 N 件）
    hist_res = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(settings.memory_context_limit)
    )
    recent_history = list(reversed(hist_res.scalars().all()))
    chat_history: list[dict[str, str]] = [
        {
            "role": "user" if r.role == MessageRole.player else "assistant",
            "content": r.content,
        }
        for r in recent_history
    ]

    # プレイヤーメッセージの処理
    if is_game_start:
        # GAME_START はDBに保存しない、特別なプロンプトに変換
        player_message_for_ai = (
            "ゲームを開始します。探索者が最初のシーンに登場する冒頭の描写を行ってください。"
            "探索者の状況、場所の雰囲気、最初の出来事を生き生きと描写し、"
            "探索者が最初に取るべき行動の選択肢を3つ提示してください。"
        )
        logger.info("send_chat: GAME_START trigger detected")
    else:
        player_message_for_ai = body.message
        # 通常メッセージは DB に保存
        player_msg = ChatHistory(
            session_id=session_id,
            role=MessageRole.player,
            content=body.message,
        )
        db.add(player_msg)
        await db.commit()

    # シナリオデータ取得（テンプレートモードの場合）
    scenario_data: dict | None = None
    if session.scenario_id:
        from app.api.scenarios import _load_scenarios  # noqa: PLC0415

        for s in _load_scenarios():
            if s["id"] == session.scenario_id:
                scenario_data = s
                break
        if scenario_data is None:
            logger.warning(
                "Scenario not found for session: scenario_id=%s", session.scenario_id
            )

    # AI 呼び出し（第1回）
    gm_client = GmClient()
    tool_handler = _make_tool_handler(session_id, db)

    try:
        ai_response = await gm_client.chat(
            player_message=player_message_for_ai,
            chat_history=chat_history,
            character_summary=character_summary,
            memories=memories,
            tool_handler=tool_handler,
            scenario=scenario_data,
            npcs=npcs if npcs else None,
        )
    except (httpx.ConnectError, ConnectionError, OSError) as e:
        logger.error("Ollama connection failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable. Please start Ollama server.",
        ) from e

    pc = next((c for c in session.characters if c.is_pc), None)
    if pc is None:
        raise HTTPException(status_code=400, detail="PC not found in session")
    npc_models = [c for c in session.characters if not c.is_pc]
    before_stats = _pc_stats_snapshot(pc)

    all_dice_results: list[DiceResult] = []
    all_updates: list[StatUpdate] = []
    dice_lines: list[str] = []
    event_names: list[str] = []

    # game_event ハンドラが処理するスキルを _execute_dice_requests から除外（二重ロール防止）
    _event_skip_skills: set[str] = set()
    if ai_response.game_event == "san_check":
        _event_skip_skills.add("SAN")
    elif ai_response.game_event == "skill_check":
        for _req in ai_response.dice_requests:
            if _req.character in ("pc", pc.name, pc.id) and _req.skill:
                _event_skip_skills.add(_req.skill.upper())
                break
    exec_response = (
        ai_response.model_copy(
            update={
                "dice_requests": [
                    r
                    for r in ai_response.dice_requests
                    if r.skill.upper() not in _event_skip_skills
                ]
            }
        )
        if _event_skip_skills
        else ai_response
    )

    # AI指定のダイス要求とステータス更新を先に処理
    if exec_response.dice_requests or exec_response.stat_updates:
        dice_results, dice_text, applied_updates = await _execute_dice_requests(
            exec_response, pc
        )
        all_dice_results.extend(dice_results)
        all_updates.extend(applied_updates)
        if dice_text:
            dice_lines.append(dice_text)

    # game_event に応じたバックエンド強制処理
    if ai_response.game_event != "none":
        event_names.append(ai_response.game_event)

    if ai_response.game_event == "san_check":
        event_dice, event_updates, event_line = _resolve_san_event(
            ai_response, pc, npc_models
        )
        all_dice_results.extend(event_dice)
        all_updates.extend(event_updates)
        dice_lines.append(event_line)
    elif ai_response.game_event == "skill_check":
        event_dice, event_line = _resolve_skill_event(ai_response, pc)
        all_dice_results.extend(event_dice)
        dice_lines.append(event_line)
    elif ai_response.game_event == "combat_start":
        combat_dice, combat_updates, combat_notes, combat_choices = (
            _resolve_combat_event(
                body.message,
                pc,
                npc_models,
            )
        )
        all_dice_results.extend(combat_dice)
        all_updates.extend(combat_updates)
        dice_lines.extend(f"【戦闘】{n}" for n in combat_notes)
        if not ai_response.choices:
            ai_response = ai_response.model_copy(update={"choices": combat_choices})
    elif ai_response.game_event == "scenario_end":
        event_names.append("session_end")

    # ダイスやイベント処理があれば第2AI呼び出し
    dice_text = "\n".join(line for line in dice_lines if line)
    if dice_text:
        first_messages: list[dict[str, str]] = build_messages(  # type: ignore[assignment]
            chat_history,
            player_message_for_ai,
            character_summary,
            memories,
            scenario_data,
            npcs if npcs else None,
        )
        try:
            second_response = await gm_client.chat_with_dice_result(
                previous_messages=first_messages,
                first_narration=ai_response.gm_narration,
                dice_results_text=dice_text,
            )
            ai_response = second_response.model_copy(
                update={
                    "dice_results": all_dice_results,
                    "stat_updates": all_updates,
                    "choices": second_response.choices or ai_response.choices,
                }
            )
        except (httpx.ConnectError, ConnectionError, OSError) as e:
            logger.error("Ollama connection failed (2nd call): %s", e)
            ai_response = ai_response.model_copy(
                update={"dice_results": all_dice_results, "stat_updates": all_updates}
            )
    else:
        ai_response = ai_response.model_copy(
            update={"dice_results": all_dice_results, "stat_updates": all_updates}
        )

    after_stats = _pc_stats_snapshot(pc)
    turn_summary = {
        "current_stats": after_stats,
        "stat_delta": {
            "hp": after_stats["hp"]["current"] - before_stats["hp"]["current"],
            "san": after_stats["san"]["current"] - before_stats["san"]["current"],
            "mp": after_stats["mp"]["current"] - before_stats["mp"]["current"],
        },
        "game_events": event_names,
        "dice_results": [r.model_dump() for r in all_dice_results],
    }
    ai_response = ai_response.model_copy(update={"turn_summary": turn_summary})

    is_manual_end = body.message.strip() == "[SESSION_END]"
    if ai_response.game_event == "scenario_end" or is_manual_end:
        full_summary = await _build_full_session_summary(session_id, db)
        ai_response = ai_response.model_copy(update={"session_summary": full_summary})

    # GM 応答を DB 保存
    gm_msg = ChatHistory(
        session_id=session_id,
        role=MessageRole.gm,
        content=ai_response.gm_narration,
        raw_ai_response=json.dumps(ai_response.model_dump(), ensure_ascii=False),
    )
    db.add(gm_msg)
    await db.commit()

    return ai_response
