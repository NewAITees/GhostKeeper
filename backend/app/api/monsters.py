"""
モジュール名: api/monsters.py
目的: モンスターテンプレート CRUD API

エンドポイント:
    GET    /api/monsters               - テンプレート一覧
    POST   /api/monsters               - テンプレート作成
    GET    /api/monsters/{id}          - テンプレート取得
    DELETE /api/monsters/{id}          - テンプレート削除
    POST   /api/monsters/seed/{scenario_id} - シナリオJSONからテンプレートを一括登録

依存:
    - app.models.monster.MonsterTemplate
    - app.api.scenarios._load_scenarios
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monster import MonsterTemplate

logger = logging.getLogger(__name__)
router = APIRouter()


class MonsterTemplateCreate(BaseModel):
    id: str
    name: str
    description: str | None = None
    role: str = "monster"
    image_id: str | None = None
    personality: str | None = None
    secret: str | None = None
    str_: int = 50
    con: int = 50
    siz: int = 50
    int_: int = 50
    dex: int = 50
    pow_: int = 50
    hp_max: int = 10
    skills: dict = {}
    damage_bonus: str = "0"
    armor: int = 0
    san_loss_success: str = "0"
    san_loss_failure: str = "1d6"
    source_scenario: str | None = None


class MonsterTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    role: str
    image_id: str | None
    personality: str | None
    secret: str | None
    str_: int
    con: int
    siz: int
    int_: int
    dex: int
    pow_: int
    hp_max: int
    skills: dict
    damage_bonus: str
    armor: int
    san_loss_success: str
    san_loss_failure: str
    source_scenario: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("")
async def list_monsters(
    db: AsyncSession = Depends(get_db),
) -> list[MonsterTemplateResponse]:
    """モンスターテンプレート一覧を返す。"""
    result = await db.execute(
        select(MonsterTemplate).order_by(MonsterTemplate.created_at.asc())
    )
    return [MonsterTemplateResponse.model_validate(m) for m in result.scalars().all()]


@router.post("", status_code=201)
async def create_monster(
    body: MonsterTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> MonsterTemplateResponse:
    """モンスターテンプレートを作成する。同一IDは上書き（upsert）する。"""
    existing = await db.get(MonsterTemplate, body.id)
    if existing:
        for field, value in body.model_dump().items():
            col = "str_" if field == "str_" else ("int_" if field == "int_" else field)
            if hasattr(existing, col):
                setattr(existing, col, value)
        monster = existing
    else:
        monster = MonsterTemplate(
            id=body.id,
            name=body.name,
            description=body.description,
            role=body.role,
            image_id=body.image_id,
            personality=body.personality,
            secret=body.secret,
            str_=body.str_,
            con=body.con,
            siz=body.siz,
            int_=body.int_,
            dex=body.dex,
            pow_=body.pow_,
            hp_max=body.hp_max,
            skills=body.skills,
            damage_bonus=body.damage_bonus,
            armor=body.armor,
            san_loss_success=body.san_loss_success,
            san_loss_failure=body.san_loss_failure,
            source_scenario=body.source_scenario,
        )
        db.add(monster)

    await db.commit()
    await db.refresh(monster)
    logger.info("create_monster: id=%s", monster.id)
    return MonsterTemplateResponse.model_validate(monster)


@router.get("/{monster_id}")
async def get_monster(
    monster_id: str,
    db: AsyncSession = Depends(get_db),
) -> MonsterTemplateResponse:
    """モンスターテンプレートを1件取得する。"""
    monster = await db.get(MonsterTemplate, monster_id)
    if monster is None:
        raise HTTPException(status_code=404, detail="Monster template not found")
    return MonsterTemplateResponse.model_validate(monster)


@router.delete("/{monster_id}", status_code=204)
async def delete_monster(
    monster_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """モンスターテンプレートを削除する。"""
    monster = await db.get(MonsterTemplate, monster_id)
    if monster is None:
        raise HTTPException(status_code=404, detail="Monster template not found")
    await db.delete(monster)
    await db.commit()
    logger.info("delete_monster: id=%s", monster_id)


@router.post("/seed/{scenario_id}", status_code=201)
async def seed_from_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[MonsterTemplateResponse]:
    """
    シナリオJSONのキャラクター定義からモンスターテンプレートを一括登録する。
    既存IDは上書き（upsert）する。
    """
    from app.api.scenarios import _load_scenarios  # noqa: PLC0415

    scenario = next((s for s in _load_scenarios() if s.get("id") == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    created: list[MonsterTemplateResponse] = []
    for ch in scenario.get("characters", []):
        stats = ch.get("stats", {})
        hp_raw = stats.get("hp", stats.get("hp_max", 10))
        pow_raw = stats.get("pow", 50)

        # SAN喪失はシナリオ定義があれば使用、なければロール別デフォルト
        san_success = ch.get("san_loss_success", "0")
        san_failure = ch.get("san_loss_failure", "1d6")
        if ch.get("role") == "monster":
            san_success = ch.get("san_loss_success", "1")
            san_failure = ch.get("san_loss_failure", "1d6")

        existing = await db.get(MonsterTemplate, ch["id"])
        if existing:
            existing.name = ch.get("name", existing.name)
            existing.description = ch.get("description", existing.description)
            existing.role = ch.get("role", existing.role)
            existing.image_id = ch.get("image_id", existing.image_id)
            existing.personality = ch.get("description")
            existing.secret = ch.get("secret")
            existing.str_ = stats.get("str", 50)
            existing.con = stats.get("con", 50)
            existing.siz = stats.get("siz", 50)
            existing.int_ = stats.get("int", 50)
            existing.dex = stats.get("dex", 50)
            existing.pow_ = pow_raw
            existing.hp_max = hp_raw
            existing.skills = ch.get("skills", {})
            existing.san_loss_success = san_success
            existing.san_loss_failure = san_failure
            existing.source_scenario = scenario_id
            monster = existing
        else:
            monster = MonsterTemplate(
                id=ch["id"],
                name=ch.get("name", "Unknown"),
                description=ch.get("description"),
                role=ch.get("role", "neutral"),
                image_id=ch.get("image_id"),
                personality=ch.get("description"),
                secret=ch.get("secret"),
                str_=stats.get("str", 50),
                con=stats.get("con", 50),
                siz=stats.get("siz", 50),
                int_=stats.get("int", 50),
                dex=stats.get("dex", 50),
                pow_=pow_raw,
                hp_max=hp_raw,
                skills=ch.get("skills", {}),
                san_loss_success=san_success,
                san_loss_failure=san_failure,
                source_scenario=scenario_id,
            )
            db.add(monster)

        await db.flush()
        await db.refresh(monster)
        created.append(MonsterTemplateResponse.model_validate(monster))
        logger.info("seed_monster: id=%s scenario=%s", monster.id, scenario_id)

    await db.commit()
    return created
