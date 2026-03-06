"""
モジュール名: app/main.py
目的: FastAPI アプリケーション本体（CORS・静的配信・ルーター登録）

起動方法:
    cd backend
    uv run uvicorn app.main:app --reload --port 8000

依存:
    - fastapi
    - app.database.init_db
    - app.api.*

注意:
    - lifespan で DB 初期化（テーブル作成）
    - images フォルダが存在する場合のみ静的配信をマウント
    - Ollama 未起動でもサーバーは起動できる（接続エラーは API 呼び出し時のみ）
"""

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import characters, chat, images, monsters, occupations, scenarios, sessions
from app.config import settings
from app.database import init_db

# モデルをインポートして Base.metadata に登録する
from app.models import character as _char_model  # noqa: F401
from app.models import chat as _chat_model  # noqa: F401
from app.models import memory as _memory_model  # noqa: F401
from app.models import monster as _monster_model  # noqa: F401
from app.models import session as _session_model  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup: initializing database")
    await init_db()
    logger.info("startup: complete")
    yield
    logger.info("shutdown: complete")


app = FastAPI(title="GhostKeeper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 画像フォルダを静的配信（存在する場合のみ）
images_path = os.path.abspath(settings.images_dir)
if os.path.exists(images_path):
    app.mount("/images", StaticFiles(directory=images_path), name="images")
    logger.info("Mounted static images from: %s", images_path)

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])
app.include_router(characters.router, prefix="/api/characters", tags=["characters"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(occupations.router, prefix="/api/occupations", tags=["occupations"])
app.include_router(monsters.router, prefix="/api/monsters", tags=["monsters"])


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
