"""
モジュール名: config.py
目的: アプリケーション設定管理（Pydantic Settings）

使い方:
    from app.config import settings

    print(settings.ollama_base_url)

依存:
    - pydantic_settings

注意:
    - 環境変数または .env ファイルで上書き可能
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:14b"
    database_url: str = "sqlite+aiosqlite:///./ghostkeeper.db"
    images_dir: str = "../images"
    scenarios_dir: str = "../scenarios"
    memory_context_limit: int = 20  # 会話履歴の最大保持件数

    model_config = {"env_file": ".env"}


settings = Settings()
