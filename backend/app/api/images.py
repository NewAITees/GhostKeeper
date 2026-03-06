"""
モジュール名: api/images.py
目的: 画像一覧取得 API エンドポイント（フォルダスキャン）

エンドポイント:
    GET /api/images/characters  - キャラクター画像一覧
    GET /api/images/scenes      - シーン画像一覧

依存:
    - app.config.settings

注意:
    - images_dir 配下のサブフォルダをスキャンして返す
    - 存在しないフォルダの場合は空リストを返す
    - 画像本体は /images/* の静的配信で提供（main.py でマウント）
"""

import logging
import os

from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _scan_character_images(base_dir: str) -> list[dict[str, str | list[str]]]:
    """
    images/characters/ 配下のキャラクターフォルダをスキャンする。
    返り値: [{"id": str, "expressions": [str, ...]}]
    """
    char_dir = os.path.join(base_dir, "characters")
    if not os.path.isdir(char_dir):
        return []

    results: list[dict[str, str | list[str]]] = []
    for char_id in sorted(os.listdir(char_dir)):
        char_path = os.path.join(char_dir, char_id)
        if not os.path.isdir(char_path):
            continue
        expressions: list[str] = [
            os.path.splitext(f)[0]
            for f in sorted(os.listdir(char_path))
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
        results.append({"id": char_id, "expressions": expressions})
    return results


def _scan_scene_images(base_dir: str) -> list[dict[str, str]]:
    """
    images/scenes/ 配下のシーン画像をスキャンする。
    返り値: [{"id": str, "path": str}]
    """
    scene_dir = os.path.join(base_dir, "scenes")
    if not os.path.isdir(scene_dir):
        return []

    results = []
    for filename in sorted(os.listdir(scene_dir)):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            scene_id = os.path.splitext(filename)[0]
            results.append({"id": scene_id, "path": f"/images/scenes/{filename}"})
    return results


@router.get("/characters")
async def list_character_images() -> list[dict[str, str | list[str]]]:
    """キャラクター画像一覧を返す。"""
    base_dir = os.path.abspath(settings.images_dir)
    logger.debug("list_character_images: scanning %s", base_dir)
    return _scan_character_images(base_dir)


@router.get("/scenes")
async def list_scene_images() -> list[dict[str, str]]:
    """シーン画像一覧を返す。"""
    base_dir = os.path.abspath(settings.images_dir)
    logger.debug("list_scene_images: scanning %s", base_dir)
    return _scan_scene_images(base_dir)
