"""
モジュール名: api/characters.py
目的: キャラクター情報取得・更新 API エンドポイント

エンドポイント:
    GET    /api/characters                      - テンプレートキャラ一覧（is_template=True）
    POST   /api/characters                      - テンプレートキャラ作成
    GET    /api/characters/{character_id}       - キャラクター詳細
    PATCH  /api/characters/{character_id}       - キャラクター更新（スキル・パラメータ）
    DELETE /api/characters/{character_id}       - テンプレートキャラ削除（is_template=True のみ）

依存:
    - sqlalchemy
    - app.models.character.Character
    - app.database.get_db
    - app.game.rules.calc_derived_stats

注意:
    - PATCH は部分更新（提供されたフィールドのみ更新）
    - skills は JSON カラム全体を置き換える
    - DELETE は is_template=True のキャラクターのみ許可
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.game.rules import calc_derived_stats
from app.models.character import Character

logger = logging.getLogger(__name__)
router = APIRouter()


class CharacterPatch(BaseModel):
    name: str | None = None
    hp_current: int | None = None
    mp_current: int | None = None
    san_current: int | None = None
    skills: dict | None = None  # type: ignore[type-arg]


class CharacterCreate(BaseModel):
    """テンプレートキャラクター作成リクエストボディ"""

    name: str
    age: int = 25
    occupation: str | None = None
    backstory: str | None = None
    str_: int = 50
    con: int = 50
    siz: int = 50
    int_: int = 50
    dex: int = 50
    pow_: int = 50
    app: int = 50
    edu: int = 50
    luk: int = 50
    skills: dict | None = None  # type: ignore[type-arg]


def _character_to_dict(character: Character) -> dict:
    """Character モデルを辞書に変換する。"""
    return {
        "id": character.id,
        "session_id": character.session_id,
        "name": character.name,
        "is_pc": character.is_pc,
        "is_template": character.is_template,
        "image_id": character.image_id,
        "occupation": character.occupation,
        "backstory": character.backstory,
        "personality": character.personality,
        "str": character.str_,
        "con": character.con,
        "siz": character.siz,
        "int": character.int_,
        "dex": character.dex,
        "pow": character.pow_,
        "app": character.app,
        "edu": character.edu,
        "luk": character.luk,
        "hp_max": character.hp_max,
        "hp_current": character.hp_current,
        "mp_max": character.mp_max,
        "mp_current": character.mp_current,
        "san_max": character.san_max,
        "san_current": character.san_current,
        "san_indefinite": character.san_indefinite,
        "skills": character.skills,
    }


@router.get("")
async def list_template_characters(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """テンプレートキャラクター一覧を返す（is_template=True かつ session_id=None）。"""
    result = await db.execute(
        select(Character).where(
            Character.is_template == True,  # noqa: E712
            Character.session_id == None,  # noqa: E711
        )
    )
    characters = result.scalars().all()
    logger.info("list_template_characters: count=%d", len(characters))
    return [_character_to_dict(c) for c in characters]


@router.post("", status_code=201)
async def create_character(
    body: CharacterCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """テンプレートキャラクターを作成する。"""
    logger.info("create_character: name=%s, occupation=%s", body.name, body.occupation)

    stats = calc_derived_stats(
        str_=body.str_,
        con=body.con,
        siz=body.siz,
        pow_=body.pow_,
        dex=body.dex,
        age=body.age,
    )

    character = Character(
        id=str(uuid4()),
        session_id=None,
        name=body.name,
        is_pc=True,
        is_template=True,
        occupation=body.occupation,
        backstory=body.backstory,
        str_=body.str_,
        con=body.con,
        siz=body.siz,
        int_=body.int_,
        dex=body.dex,
        pow_=body.pow_,
        app=body.app,
        edu=body.edu,
        luk=body.luk,
        hp_max=stats["hp_max"],
        hp_current=stats["hp_max"],
        mp_max=stats["mp_max"],
        mp_current=stats["mp_max"],
        san_max=stats["san_max"],
        san_current=stats["san_max"],
        skills=body.skills or {},
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)

    logger.info("create_character done: id=%s", character.id)
    return _character_to_dict(character)


@router.get("/{character_id}")
async def get_character(
    character_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """キャラクター詳細を返す。"""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    return _character_to_dict(character)


@router.patch("/{character_id}")
async def patch_character(
    character_id: str,
    body: CharacterPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """キャラクターを部分更新する。"""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    if body.name is not None:
        character.name = body.name
    if body.hp_current is not None:
        character.hp_current = max(0, min(body.hp_current, character.hp_max))
    if body.mp_current is not None:
        character.mp_current = max(0, min(body.mp_current, character.mp_max))
    if body.san_current is not None:
        character.san_current = max(0, min(body.san_current, character.san_max))
    if body.skills is not None:
        character.skills = body.skills

    await db.commit()
    await db.refresh(character)
    logger.info("patch_character: id=%s", character_id)
    return {"id": character.id, "name": character.name}


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    character_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """テンプレートキャラクターを削除する（is_template=True のみ許可）。"""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    if not character.is_template:
        raise HTTPException(
            status_code=400, detail="Only template characters can be deleted"
        )

    await db.delete(character)
    await db.commit()
    logger.info("delete_character: id=%s", character_id)
