"""
モジュール名: ai/tools.py
目的: Ollama Tool Use 定義一覧

使い方:
    from app.ai.tools import TOOLS

    # Ollama client.chat() に渡す
    response = await client.chat(model=..., messages=..., tools=TOOLS)

依存:
    なし（純粋なデータ定義）

注意:
    - TOOLS の各要素は Ollama の tool calling 形式
    - ツール実装は app/api/chat.py のツールハンドラーで行う
"""

from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "指定したダイスを振る。例: 1d100, 2d6+3",
            "parameters": {
                "type": "object",
                "properties": {
                    "notation": {
                        "type": "string",
                        "description": "ダイス記法 (例: '1d100', '2d6')",
                    },
                },
                "required": ["notation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_check",
            "description": "キャラクターの技能判定を行う",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "skill_name": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["normal", "hard", "extreme"],
                    },
                },
                "required": ["character_id", "skill_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_character_stats",
            "description": "キャラクターのパラメータを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                },
                "required": ["character_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_stats",
            "description": "キャラクターのHP/SAN/MPを増減させる",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "field": {
                        "type": "string",
                        "enum": ["hp", "san", "mp"],
                    },
                    "delta": {
                        "type": "integer",
                        "description": "変化量（負=減少）",
                    },
                    "reason": {"type": "string"},
                },
                "required": ["character_id", "field", "delta", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_memory",
            "description": "重要なイベントをセッション記憶に追加する",
            "parameters": {
                "type": "object",
                "properties": {
                    "event": {"type": "string"},
                    "importance": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["event"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "過去の記憶イベントをキーワード検索する",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_image",
            "description": "キャラクターまたはシーンの画像パスを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["character", "scene"],
                    },
                    "id": {"type": "string"},
                    "expression": {
                        "type": "string",
                        "enum": ["normal", "scared", "angry", "dead"],
                    },
                },
                "required": ["type", "id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_npc_memory",
            "description": "NPCの個別記憶にイベントを追加する",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "event": {"type": "string"},
                },
                "required": ["character_id", "event"],
            },
        },
    },
]
