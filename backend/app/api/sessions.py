"""
モジュール名: api/sessions.py
目的: ゲームセッション CRUD API エンドポイント

エンドポイント:
    GET    /api/sessions          - セッション一覧
    POST   /api/sessions          - セッション作成（テンプレートキャラをコピー）
    GET    /api/sessions/{id}     - セッション詳細取得
    DELETE /api/sessions/{id}     - セッション削除

依存:
    - sqlalchemy
    - app.models.session, character
    - app.game.rules (派生値計算)
    - app.database.get_db

注意:
    - id は uuid4 で生成
    - セッション作成時はテンプレートキャラクターをコピーして使用
    - 元のテンプレートキャラクターは変更しない
"""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.chat import ChatHistory, MessageRole
from app.models.character import Character
from app.models.session import GameSession, ScenarioMode

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionCreate(BaseModel):
    name: str
    mode: ScenarioMode = ScenarioMode.free
    scenario_id: str | None = None
    character_id: str  # テンプレートキャラクターのID


class SessionResponse(BaseModel):
    id: str
    name: str
    mode: str
    scenario_id: str | None
    initial_gm_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _build_opening_narration(
    mode: ScenarioMode,
    pc: Character,
    scenario: dict | None,
) -> str:
    if scenario:
        npc_lines = []
        for ch in scenario.get("characters", [])[:3]:
            npc_lines.append(f"- {ch.get('name', 'NPC')}（{ch.get('role', '関係者')}）")
        npc_text = "\n".join(npc_lines) if npc_lines else "- 重要NPCは現地で判明する"
        return (
            f"{scenario.get('era', '1920年代')}、{scenario.get('location', scenario.get('starting_location', '未知の場所'))}。\n"
            f"{pc.name}は{scenario.get('synopsis', '不可解な依頼')}をきっかけにこの地を訪れた。\n"
            f"導入: {scenario.get('objective', '事件の真相を探る')}\n"
            "現時点で関わる人物:\n"
            f"{npc_text}\n"
            "まずは周辺を観察し、会話と調査で手がかりを集めるべきだ。"
        )

    if mode == ScenarioMode.free:
        return (
            "時代は1920年代。霧の濃い夜、あなたは奇妙な噂の現場へ足を踏み入れる。\n"
            f"探索者 {pc.name} は、説明のつかない出来事の真相を確かめるためにここへ来た。\n"
            "現場にはあなたを警戒する住民と、何かを隠す関係者がいる。\n"
            "まずは周囲を観察し、誰に話を聞くか、どこを調べるかを決めるとよい。"
        )

    return (
        "探索が始まる。状況を把握し、登場人物の関係を見極めながら、"
        "何を優先して調べるべきかを判断せよ。"
    )


@router.get("")
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionResponse]:
    """セッション一覧を返す（新しい順）。"""
    result = await db.execute(
        select(GameSession).order_by(GameSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post("", status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    セッションを作成し、テンプレートキャラクターをコピーしてセッションに紐付ける。

    処理フロー:
    1. character_id でテンプレートキャラクターを取得（なければ 404）
    2. キャラクターをコピーして session_id を設定（is_template=False）
    3. 元のテンプレートは変更しない
    """
    logger.info(
        "create_session: name=%s, mode=%s, character_id=%s",
        body.name,
        body.mode,
        body.character_id,
    )

    # テンプレートキャラクターを取得
    char_result = await db.execute(
        select(Character).where(Character.id == body.character_id)
    )
    template_char = char_result.scalar_one_or_none()
    if template_char is None:
        raise HTTPException(status_code=404, detail="Character not found")

    session_id = str(uuid4())
    now = datetime.utcnow()
    session = GameSession(
        id=session_id,
        name=body.name,
        mode=body.mode,
        scenario_id=body.scenario_id,
        created_at=now,
        updated_at=now,
    )
    db.add(session)

    # テンプレートキャラクターをコピーしてセッションに紐付け
    pc = Character(
        id=str(uuid4()),
        session_id=session_id,
        name=template_char.name,
        is_pc=True,
        is_template=False,
        image_id=template_char.image_id,
        occupation=template_char.occupation,
        backstory=template_char.backstory,
        str_=template_char.str_,
        con=template_char.con,
        siz=template_char.siz,
        int_=template_char.int_,
        dex=template_char.dex,
        pow_=template_char.pow_,
        app=template_char.app,
        edu=template_char.edu,
        luk=template_char.luk,
        hp_max=template_char.hp_max,
        hp_current=template_char.hp_current,
        mp_max=template_char.mp_max,
        mp_current=template_char.mp_current,
        san_max=template_char.san_max,
        san_current=template_char.san_current,
        san_indefinite=template_char.san_indefinite,
        skills=dict(template_char.skills) if template_char.skills else {},
    )
    db.add(pc)

    # シナリオ情報を読み、ターン0開幕ナレーションを自動生成して保存
    scenario_data: dict | None = None
    if body.scenario_id:
        from app.api.scenarios import _load_scenarios  # noqa: PLC0415

        for s in _load_scenarios():
            if s.get("id") == body.scenario_id:
                scenario_data = s
                break
    opening = _build_opening_narration(body.mode, pc, scenario_data)
    db.add(
        ChatHistory(
            session_id=session_id,
            role=MessageRole.gm,
            content=opening,
        )
    )

    await db.commit()
    await db.refresh(session)
    logger.info("create_session done: id=%s, pc_id=%s", session_id, pc.id)
    return SessionResponse.model_validate(session).model_copy(
        update={"initial_gm_message": opening}
    )


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """セッション詳細とキャラクター一覧を返す。"""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.characters))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    characters = [
        {
            "id": c.id,
            "name": c.name,
            "is_pc": c.is_pc,
            "hp_current": c.hp_current,
            "hp_max": c.hp_max,
            "san_current": c.san_current,
            "san_max": c.san_max,
            "mp_current": c.mp_current,
            "mp_max": c.mp_max,
            "personality": c.personality,
            "npc_memory": c.npc_memory,
        }
        for c in session.characters
    ]

    return {
        "id": session.id,
        "name": session.name,
        "mode": session.mode,
        "scenario_id": session.scenario_id,
        "current_location": session.current_location,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "characters": characters,
    }


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """セッションを削除する（関連レコードも cascade 削除）。"""
    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()
    logger.info("delete_session: id=%s", session_id)
