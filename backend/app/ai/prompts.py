"""
モジュール名: ai/prompts.py
目的: システムプロンプトと Ollama 送信メッセージ構築

使い方:
    from app.ai.prompts import build_messages

    messages = build_messages(
        chat_history=[{"role": "user", "content": "..."}],
        player_message="図書館へ向かう",
        character_summary="[PC] 田中...",
        memories=["怪物を目撃した"],
        scenario={"title": "呪われた図書館", ...},  # 省略可
    )

依存:
    なし

注意:
    - system ロールのメッセージに SYSTEM_PROMPT + キャラ情報 + シナリオ情報 + 記憶を統合
    - chat_history は直近 N 件に絞るのは呼び出し側の責務
    - scenario=None の場合はフリーモード（シナリオ情報なし）
"""

SYSTEM_PROMPT = """
あなたはクトゥルフ神話TRPGのゲームマスター（GM）です。
CoC 7版のルールに従い、1920年代の探索シナリオを進行します。

## 役割
- GMとして状況・場所・NPCの行動を描写する
- 必要に応じてNPCのセリフを演じる
- プレイヤーの行動に対してルールに従った判定を行う
- SANチェック・技能ロール・ダメージ計算を適切に実施する

## 出力形式
必ず以下のJSON形式で応答すること。自然言語の混在は禁止。

{
  "thinking": "内部推論（プレイヤーには表示しない）",
  "gm_narration": "GMの描写・ナレーション（日本語）",
  "npc_dialogues": [...],
  "dice_requests": [...],
  "stat_updates": [...],
  "image": null or {...},
  "choices": ["選択肢A", "選択肢B"],
  "game_event": "none"
}

## ゲームルール（CoC 7版）
- 技能判定: 1d100 ≤ 技能値で成功
- クリティカル: 1
- ファンブル: 96-100（技能値<50時）または100
- SAN喪失は神話的存在との遭遇・目撃で発生

## 注意事項
- 描写は日本語で行う
- 恐怖・狂気・不条理を適切に演出する
- プレイヤーに選択の余地を常に与える
- game_event が "san_check" の場合は `dice_requests` に SAN 判定情報を1件以上含める
  - 例: {"type":"1/1d6","skill":"SAN","character":"pc","difficulty":"normal"}
- game_event が "skill_check" の場合は対象技能を `dice_requests` に必ず1件含める
- game_event が "combat_start" の場合は choices に戦闘行動（攻撃/回避/組みつき等）を含める
"""


def build_messages(
    chat_history: list[dict[str, str]],
    player_message: str,
    character_summary: str,
    memories: list[str],
    scenario: dict | None = None,
    npcs: list[dict] | None = None,
) -> list[dict[str, str]]:
    """
    Ollama に渡すメッセージリストを構築する。

    - system: SYSTEM_PROMPT + キャラクター情報 + シナリオ情報（あれば） + 記憶 + NPC情報（あれば）
    - history: 直近N件の会話履歴
    - user: 今回のプレイヤーメッセージ
    """
    system_content = SYSTEM_PROMPT + f"\n\n## 探索者情報\n{character_summary}"

    if scenario:
        system_content += f"""

## シナリオ情報
タイトル: {scenario["title"]}
時代・舞台: {scenario.get("era", "")}
あらすじ: {scenario["synopsis"]}
プレイヤーの目標: {scenario["objective"]}
クライマックス条件: {scenario.get("climax", "")}

### 登場人物
"""
        for ch in scenario.get("characters", []):
            system_content += (
                f"- {ch['name']}（{ch.get('role', '')}）: {ch['description']}"
            )
            if ch.get("secret"):
                system_content += f" 【秘密】{ch['secret']}"
            system_content += "\n"

        system_content += "\n### 場所\n"
        for loc in scenario.get("locations", []):
            clues = "、".join(loc.get("clues", []))
            system_content += f"- {loc['name']}: {loc['description']}"
            if clues:
                system_content += f" 【手がかり】{clues}"
            system_content += "\n"

        if scenario.get("gm_instructions"):
            system_content += f"\n### GM追加指示\n{scenario['gm_instructions']}\n"

    if npcs:
        system_content += "\n\n## 現在のNPC状態\n"
        for npc in npcs:
            system_content += f"\n### {npc['name']}（{npc.get('role', '')}）\n"
            if npc.get("personality"):
                system_content += f"個性: {npc['personality']}\n"
            if npc.get("npc_memory"):
                mem_items = npc["npc_memory"].get("events", [])
                if mem_items:
                    system_content += "記憶:\n"
                    for ev in mem_items[-5:]:  # 直近5件
                        system_content += f"  - {ev}\n"

    if memories:
        system_content += "\n\n## 重要な記憶\n" + "\n".join(f"- {m}" for m in memories)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": player_message})
    return messages
