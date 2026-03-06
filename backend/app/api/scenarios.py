"""
モジュール名: api/scenarios.py
目的: シナリオテンプレート一覧・詳細 API

エンドポイント:
    GET /api/scenarios       - シナリオ一覧
    GET /api/scenarios/{id}  - シナリオ詳細

使い方:
    from app.api.scenarios import router, _load_scenarios

    # ルーター登録
    app.include_router(router, prefix="/api/scenarios", tags=["scenarios"])

    # シナリオ読み込み（他モジュールからも使用可）
    scenarios = _load_scenarios()

依存:
    - app.config.settings（scenarios_dir パス解決）

注意:
    - scenarios_dir は backend/ からの相対パス（"../scenarios"）
    - schema.json で始まるファイルはスキップ
    - JSON パース失敗ファイルは無視してログ出力
"""

import json
import logging
import os

from fastapi import APIRouter, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_scenarios() -> list[dict]:
    """scenarios/ フォルダ内の全 JSON ファイルを読み込む。"""
    base = os.path.abspath(settings.scenarios_dir)
    results: list[dict] = []
    if not os.path.exists(base):
        logger.warning("scenarios_dir not found: %s", base)
        return results
    for fname in sorted(os.listdir(base)):
        if fname.endswith(".json") and not fname.startswith("schema"):
            fpath = os.path.join(base, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    results.append(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load scenario file %s: %s", fname, e)
    return results


@router.get("")
async def list_scenarios() -> list[dict]:
    """シナリオ一覧（id, title, description, era, location のみ）。"""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "description": s.get("description", ""),
            "era": s.get("era", ""),
            "location": s.get("location", ""),
        }
        for s in _load_scenarios()
    ]


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict:
    """シナリオ詳細を返す。"""
    for s in _load_scenarios():
        if s["id"] == scenario_id:
            return s
    raise HTTPException(status_code=404, detail="Scenario not found")
