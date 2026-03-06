"""
モジュール名: api/occupations.py
目的: CoC 7版職業一覧 + ダイスロール API エンドポイント

エンドポイント:
    GET  /api/occupations            - 職業一覧を返す
    POST /api/occupations/roll-stats - キャラクター用ダイスロール実行

使い方:
    GET /api/occupations
    POST /api/occupations/roll-stats → 各ステータスのダイス結果を返す

依存:
    - app.game.dice

注意:
    - ダイスロール規則（CoC 7版）:
        STR / CON / DEX / APP / POW / LUK: 3d6 × 5
        SIZ / INT / EDU: (2d6 + 6) × 5
"""

import logging
import random

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

OCCUPATIONS = [
    {
        "id": "detective",
        "name": "探偵",
        "description": "謎を解くことを生業とする者。観察眼と推理力が武器。",
        "skill_points_formula": "EDU×2 + DEX×2",
        "credit_rating": "9-30",
        "typical_skills": [
            "図書館",
            "目星",
            "聞き耳",
            "心理学",
            "法律",
            "追跡",
            "写真術",
            "言いくるめ",
        ],
    },
    {
        "id": "doctor",
        "name": "医師",
        "description": "医療の専門家。人体と薬の知識を持つ。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "30-80",
        "typical_skills": [
            "医学",
            "心理学",
            "薬学",
            "図書館",
            "説得",
            "応急手当",
            "科学（生物学）",
        ],
    },
    {
        "id": "journalist",
        "name": "記者",
        "description": "真実を追い求める報道人。情報収集と人脈が強み。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "9-30",
        "typical_skills": [
            "図書館",
            "心理学",
            "歴史",
            "写真術",
            "説得",
            "聞き耳",
            "目星",
            "言いくるめ",
        ],
    },
    {
        "id": "professor",
        "name": "教授・研究者",
        "description": "大学で研究・教育に携わる学者。専門知識と文献調査が得意。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "20-70",
        "typical_skills": [
            "図書館",
            "歴史",
            "考古学",
            "言語（ラテン語）",
            "心理学",
            "オカルト",
        ],
    },
    {
        "id": "police",
        "name": "警察官",
        "description": "法の執行者。市民の安全を守る。",
        "skill_points_formula": "EDU×2 + STR×2",
        "credit_rating": "9-30",
        "typical_skills": [
            "目星",
            "聞き耳",
            "心理学",
            "法律",
            "格闘（拳）",
            "射撃（拳銃）",
            "追跡",
        ],
    },
    {
        "id": "soldier",
        "name": "軍人",
        "description": "戦闘訓練を受けた兵士。戦術と体力が武器。",
        "skill_points_formula": "EDU×2 + STR×2",
        "credit_rating": "9-30",
        "typical_skills": [
            "格闘（拳）",
            "射撃",
            "応急手当",
            "目星",
            "歴史",
            "電気修理",
        ],
    },
    {
        "id": "clergy",
        "name": "聖職者",
        "description": "宗教的指導者。信仰と人心掌握に長ける。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "9-60",
        "typical_skills": [
            "図書館",
            "歴史",
            "心理学",
            "説得",
            "言語（ラテン語）",
            "オカルト",
        ],
    },
    {
        "id": "antiquarian",
        "name": "古物研究家",
        "description": "骨董品・古書の収集家・研究者。謎めいた品々に詳しい。",
        "skill_points_formula": "EDU×4",
        "credit_rating": "30-70",
        "typical_skills": [
            "図書館",
            "歴史",
            "考古学",
            "芸術/工芸（鑑定）",
            "目星",
            "オカルト",
        ],
    },
]


def _roll_3d6_x5() -> tuple[int, list[int]]:
    """3d6 × 5 のダイスロール。CoC 7版でSTR/CON/DEX/APP/POW/LUKに使用。"""
    rolls = [random.randint(1, 6) for _ in range(3)]
    total = sum(rolls) * 5
    return total, rolls


def _roll_2d6p6_x5() -> tuple[int, list[int]]:
    """(2d6 + 6) × 5 のダイスロール。CoC 7版でSIZ/INT/EDUに使用。"""
    rolls = [random.randint(1, 6) for _ in range(2)]
    total = (sum(rolls) + 6) * 5
    return total, rolls


@router.get("")
async def list_occupations() -> list[dict]:
    """CoC 7版職業一覧を返す。"""
    logger.info("list_occupations called")
    return OCCUPATIONS


@router.post("/roll-stats")
async def roll_stats() -> dict:
    """
    CoC 7版のダイスルールでキャラクターステータスをロールして返す。

    STR/CON/DEX/APP/POW/LUK: 3d6 × 5
    SIZ/INT/EDU: (2d6 + 6) × 5
    """
    logger.info("roll_stats called")

    str_val, str_rolls = _roll_3d6_x5()
    con_val, con_rolls = _roll_3d6_x5()
    siz_val, siz_rolls = _roll_2d6p6_x5()
    int_val, int_rolls = _roll_2d6p6_x5()
    dex_val, dex_rolls = _roll_3d6_x5()
    pow_val, pow_rolls = _roll_3d6_x5()
    app_val, app_rolls = _roll_3d6_x5()
    edu_val, edu_rolls = _roll_2d6p6_x5()
    luk_val, luk_rolls = _roll_3d6_x5()

    result = {
        "str_": str_val,
        "con": con_val,
        "siz": siz_val,
        "int_": int_val,
        "dex": dex_val,
        "pow_": pow_val,
        "app": app_val,
        "edu": edu_val,
        "luk": luk_val,
        "roll_details": {
            "str_": str_rolls,
            "con": con_rolls,
            "siz": siz_rolls,
            "int_": int_rolls,
            "dex": dex_rolls,
            "pow_": pow_rolls,
            "app": app_rolls,
            "edu": edu_rolls,
            "luk": luk_rolls,
        },
    }
    logger.info("roll_stats result: str=%d, con=%d, siz=%d", str_val, con_val, siz_val)
    return result
