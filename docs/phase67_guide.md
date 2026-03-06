# GhostKeeper 実装ガイド（Phase 6〜7）

## 前提

- 作業ディレクトリ: `/home/perso/analysis/GhostKeeper`
- Phase 1〜5 実装済み（backend API・frontend ともに動作確認済み）
- 実装前に `tasks/todo.md` を確認し、完了タスクに `[x]` を付けること
- 問題・学びは `tasks/lessons.md` に追記すること

---

## Phase 6: シナリオ管理

### 概要

- `scenarios/` フォルダに JSON ファイルを置くだけでシナリオが追加される
- バックエンドは `GET /api/scenarios` でシナリオ一覧を返す
- セッション作成時にシナリオを選択すると、そのシナリオ情報が AI の system プロンプトに注入される
- フリーモードの場合はシナリオ未選択（AI がインプロで進行）

---

### 6-1. シナリオ JSON スキーマ

`scenarios/schema.json`（参照用スキーマ定義）:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema",
  "type": "object",
  "required": ["id", "title", "synopsis", "starting_location", "objective", "locations", "gm_instructions"],
  "properties": {
    "id":          { "type": "string", "description": "URLセーフなID（ファイル名と一致させる）" },
    "title":       { "type": "string", "description": "シナリオタイトル" },
    "description": { "type": "string", "description": "短い説明（一覧表示用）" },
    "era":         { "type": "string", "description": "時代設定（例: '1920s'）" },
    "location":    { "type": "string", "description": "舞台地域" },
    "synopsis":    { "type": "string", "description": "GM向け全体あらすじ（プレイヤーには非公開）" },
    "starting_location": { "type": "string", "description": "開始ロケーションのID" },
    "objective":   { "type": "string", "description": "プレイヤーの目標（公開情報）" },
    "characters": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "description"],
        "properties": {
          "id":          { "type": "string" },
          "name":        { "type": "string" },
          "role":        { "type": "string", "enum": ["ally", "neutral", "enemy", "monster"] },
          "description": { "type": "string", "description": "GM向けキャラクター解説" },
          "secret":      { "type": "string", "description": "プレイヤーに隠された真実" },
          "image_id":    { "type": "string", "description": "images/characters/{image_id}/ のフォルダ名" },
          "stats": {
            "type": "object",
            "description": "CoC 7版パラメータ（省略可。省略時はAIが適切に設定）",
            "properties": {
              "str": { "type": "integer" }, "con": { "type": "integer" },
              "siz": { "type": "integer" }, "int": { "type": "integer" },
              "dex": { "type": "integer" }, "pow": { "type": "integer" },
              "hp":  { "type": "integer" }
            }
          }
        }
      }
    },
    "locations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "description"],
        "properties": {
          "id":          { "type": "string" },
          "name":        { "type": "string" },
          "description": { "type": "string", "description": "GM向けロケーション解説" },
          "atmosphere":  { "type": "string", "description": "雰囲気・情景描写のヒント" },
          "image_id":    { "type": "string", "description": "images/scenes/{image_id}.png のID" },
          "connections": { "type": "array", "items": { "type": "string" } },
          "clues":       { "type": "array", "items": { "type": "string" }, "description": "発見可能な手がかり" }
        }
      }
    },
    "climax": { "type": "string", "description": "クライマックス条件・クリア条件" },
    "gm_instructions": { "type": "string", "description": "AIへのGM追加指示（シナリオ固有ルール・雰囲気・禁止事項など）" }
  }
}
```

---

### 6-2. サンプルシナリオ

`scenarios/haunted_library.json` を作成する。
クトゥルフ神話らしい1920年代アーカムのシナリオ。

```json
{
  "id": "haunted_library",
  "title": "呪われた図書館",
  "description": "禁断の蔵書が眠るアーカム図書館で起こる怪事件。失踪した司書の謎を追え。",
  "era": "1924年、マサチューセッツ州アーカム",
  "location": "アーカム市立図書館",
  "synopsis": "アーカム市立図書館の老司書ウィリアム・モースが行方不明になった。彼は「ネクロノミコン」の写本を発見したと興奮気味に語っていたが、翌朝には忽然と姿を消した。探索者は依頼を受け調査に乗り出すが、図書館の地下には何世紀にもわたって封印されてきた存在が眠っていた。",
  "objective": "失踪した司書ウィリアム・モースの行方を調べ、図書館で起きている怪事件の真相を解明する。",
  "starting_location": "main_entrance",
  "characters": [
    {
      "id": "william_morse",
      "name": "ウィリアム・モース",
      "role": "neutral",
      "description": "65歳の老司書。30年間図書館に勤める。禁書を発見後、精神が不安定になっている。地下に引き寄せられている。",
      "secret": "すでに「声」に支配されはじめており、封印を解こうとしている。悪人ではなく被害者。",
      "image_id": "william_morse",
      "stats": { "str": 35, "con": 40, "siz": 50, "int": 75, "dex": 45, "pow": 60, "hp": 9 }
    },
    {
      "id": "young_assistant",
      "name": "エレン・チェイス",
      "role": "ally",
      "description": "図書館の若い助手（22歳）。モース失踪を最初に気づいた。探索者に協力的だが怖がっている。",
      "secret": "地下から聞こえる声を聞いており、夢でうなされている。",
      "image_id": "ellen_chase",
      "stats": { "str": 40, "con": 50, "siz": 45, "int": 65, "dex": 60, "pow": 55, "hp": 10 }
    },
    {
      "id": "the_presence",
      "name": "名状しがたい存在",
      "role": "monster",
      "description": "地下に封印された次元外の存在。直接の姿は持たず、本の文字や影を通じて現れる。SAN喪失の主因。",
      "secret": "完全な召喚には生贄が必要。モースを媒介として利用しようとしている。",
      "stats": { "pow": 95, "hp": 999 }
    }
  ],
  "locations": [
    {
      "id": "main_entrance",
      "name": "正面玄関・受付",
      "description": "重厚な木製扉、高い天井。受付にエレン・チェイスがいる。",
      "atmosphere": "昼間でも薄暗く、古い紙とカビの匂いが漂う。奥から時折、不可解な物音が聞こえる。",
      "image_id": "library_entrance",
      "connections": ["main_hall", "staff_room"],
      "clues": ["モースの日誌（机の引き出し）", "エレンの証言"]
    },
    {
      "id": "main_hall",
      "name": "大閲覧室",
      "description": "天井まで伸びる書架、古い木製テーブル。数名の利用者がいる。",
      "atmosphere": "蝋燭のような照明。本の影が奇妙な形を作っている気がする。",
      "image_id": "library_main_hall",
      "connections": ["main_entrance", "restricted_section", "basement_stairs"],
      "clues": ["書架の一冊が不自然に開いたまま（P.233に奇妙な図形）", "床に点々と続く足跡"]
    },
    {
      "id": "restricted_section",
      "name": "禁書室",
      "description": "鍵のかかった鉄柵の向こう。「関係者以外立入禁止」の札。",
      "atmosphere": "柵の向こうから異様な冷気が漂う。本の背表紙の文字が読み取りにくい。",
      "image_id": "library_restricted",
      "connections": ["main_hall"],
      "clues": ["ネクロノミコン写本の空の台座", "モースの落としたペン", "床に描かれた陣（書籍で隠されている）"]
    },
    {
      "id": "basement_stairs",
      "name": "地下への階段",
      "description": "大閲覧室の隅、本棚の陰に隠れた下り階段。",
      "atmosphere": "階段の下から冷たい空気と、かすかな呻き声のようなものが聞こえる。",
      "image_id": "library_stairs",
      "connections": ["main_hall", "basement"],
      "clues": []
    },
    {
      "id": "basement",
      "name": "地下貯蔵室",
      "description": "古い木箱と廃棄本が積まれた地下室。中央に奇妙な陣が描かれている。",
      "atmosphere": "完全な暗闇。空気が重く、呼吸がしにくい。壁が脈打つように見える。ここにモースがいる。",
      "image_id": "library_basement",
      "connections": ["basement_stairs"],
      "clues": ["陣の中心にいるモース（トランス状態）", "床に書き殴られた古代文字", "封印の石板（割れかけている）"]
    },
    {
      "id": "staff_room",
      "name": "職員室",
      "description": "館長室とスタッフ用の小部屋。モースのデスクがある。",
      "atmosphere": "散らかったメモ帳。壁にびっしりと書かれた計算式と図形。",
      "image_id": "library_staff_room",
      "connections": ["main_entrance"],
      "clues": ["モースの研究ノート（神話的知識を得る：知識(クトゥルフ神話)+5、SAN-1d3）", "図書館長への手紙（未送付）"]
    }
  ],
  "climax": "地下でトランス状態のモースを発見。封印の石板を修復（技巧ロールまたは知識(クトゥルフ神話)）するか、モースを地下から連れ出すことでエンディング。石板が完全に破壊されると「名状しがたい存在」が部分召喚され、即時SANチェック(1d6/1d20)が発生する。モース救出成功でグッドエンド。",
  "gm_instructions": "このシナリオでは謎解き要素を重視する。戦闘は最終手段であり、基本的に「名状しがたい存在」と直接戦うことはできない。探索者が地下に降りる前に充分な手がかりを集めさせること。恐怖の演出は段階的に強めていく（最初は違和感、次第に明確な異常へ）。モースは悪人ではなく被害者として扱う。SANチェックのタイミング：①禁書室の陣を発見（0/1）②地下の光景を目撃（0/1d3）③モースのトランス状態（1/1d4）④存在の気配を感じた時（1/1d6）。"
}
```

---

### 6-3. バックエンド: `GET /api/scenarios` エンドポイント

`backend/app/api/scenarios.py` を新規作成:

```python
"""
モジュール名: api/scenarios.py
目的: シナリオテンプレート一覧・詳細 API

エンドポイント:
    GET /api/scenarios       - シナリオ一覧
    GET /api/scenarios/{id}  - シナリオ詳細
"""
import json
import os
from fastapi import APIRouter, HTTPException
from app.config import settings

router = APIRouter()

def _load_scenarios() -> list[dict]:
    """scenarios/ フォルダ内の全 JSON ファイルを読み込む。"""
    base = os.path.abspath(settings.scenarios_dir)
    results = []
    if not os.path.exists(base):
        return results
    for fname in sorted(os.listdir(base)):
        if fname.endswith(".json") and not fname.startswith("schema"):
            fpath = os.path.join(base, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    results.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
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
```

`backend/app/main.py` に追加:

```python
from app.api import sessions, chat, characters, images, scenarios

app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])
```

---

### 6-4. バックエンド: シナリオ情報を AI プロンプトに注入

セッション作成時にシナリオを選択した場合、`send_chat` でシナリオ JSON を取得して `build_messages` に渡す。

**`backend/app/ai/prompts.py` の `build_messages` を修正:**

```python
def build_messages(
    chat_history: list[dict[str, str]],
    player_message: str,
    character_summary: str,
    memories: list[str],
    scenario: dict | None = None,   # ← 追加
) -> list[dict[str, str]]:
    system_content = SYSTEM_PROMPT + f"\n\n## 探索者情報\n{character_summary}"

    if scenario:
        system_content += f"""

## シナリオ情報
タイトル: {scenario['title']}
時代・舞台: {scenario.get('era', '')}
あらすじ: {scenario['synopsis']}
プレイヤーの目標: {scenario['objective']}
クライマックス条件: {scenario.get('climax', '')}

### 登場人物
"""
        for ch in scenario.get("characters", []):
            system_content += f"- {ch['name']}（{ch.get('role','')}）: {ch['description']}"
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

    if memories:
        system_content += "\n\n## 重要な記憶\n" + "\n".join(f"- {m}" for m in memories)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": player_message})
    return messages
```

**`backend/app/api/chat.py` の `send_chat` を修正:**

`send_chat` 内で `session.scenario_id` が存在する場合、`scenarios.py` の `_load_scenarios()` からシナリオを取得して `build_messages` に渡す。

```python
# send_chat 関数内に追加
scenario_data: dict | None = None
if session.scenario_id:
    from app.api.scenarios import _load_scenarios
    for s in _load_scenarios():
        if s["id"] == session.scenario_id:
            scenario_data = s
            break

# build_messages の呼び出しに scenario=scenario_data を追加
# （GmClient.chat() を呼ぶ前に、build_messages の引数を増やすか、
#  GmClient.chat() に scenario パラメータを追加する）
```

`GmClient.chat()` のシグネチャに `scenario: dict | None = None` を追加し、`build_messages` に渡す。

---

### 6-5. フロントエンド: セッション作成モーダルのシナリオ選択 UI

`SessionCreate.tsx` を修正して、シナリオ一覧を取得・表示する。

**api/client.ts に追加:**
```typescript
listScenarios: () =>
  req<Array<{ id: string; title: string; description: string; era: string; location: string }>>(
    '/api/scenarios'
  ),
```

**SessionCreate.tsx の修正内容:**
1. コンポーネント初期化時に `api.listScenarios()` を呼んでシナリオ一覧取得
2. モード選択で「テンプレート」を選ぶとシナリオ選択 `<select>` が出現
3. 選択したシナリオの `id` を `scenario_id` として `createSession` に渡す

UI イメージ:
```
モード: ○ フリーモード  ● テンプレート

シナリオを選択:
┌─────────────────────────────────────┐
│ ▼ 呪われた図書館                     │
│   1924年 / アーカム市立図書館        │
│   禁断の蔵書が眠るアーカム図書館...  │
└─────────────────────────────────────┘
```

---

## Phase 7: 品質・仕上げ

### 7-1. pre-commit 有効化（backend/）

`.pre-commit-config.yaml` は既に存在する。`backend/` で実行:

```bash
cd /home/perso/analysis/GhostKeeper/backend
uv run pre-commit install
uv run pre-commit run --all-files
```

エラーがあれば修正する。`tasks/lessons.md` にエラーと対処を記録する。

### 7-2. README.md 作成

`/home/perso/analysis/GhostKeeper/README.md` を作成:

以下の内容を含めること:
1. **プロジェクト概要**（クトゥルフTRPG AIチャット）
2. **必要環境**（Python 3.12, Node.js, Ollama）
3. **セットアップ手順**:
   - Ollama インストール・モデル取得: `ollama pull qwen3.5`
   - backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload`
   - frontend: `cd frontend && npm install && npm run dev`
4. **設定変更方法**:
   - Ollama モデルの切り替え（`backend/.env` に `OLLAMA_MODEL=モデル名`）
5. **画像の追加方法**:
   - `images/characters/{キャラクターID}/normal.png` に配置
   - `images/scenes/{シーンID}.png` に配置
6. **シナリオの追加方法**:
   - `scenarios/` に JSON ファイルを置く（スキーマは `scenarios/schema.json` 参照）
7. **ゲームの遊び方**（簡単な説明）

---

## 完了条件

### Phase 6
- [ ] `GET /api/scenarios` が `haunted_library.json` を返す
- [ ] テンプレートモードでセッション作成するとシナリオ情報が AI に渡る
- [ ] セッション作成モーダルでシナリオ選択 UI が動作する

### Phase 7
- [ ] `uv run pre-commit run --all-files` がエラーなし
- [ ] `README.md` が作成されている
- [ ] `tasks/todo.md` の Phase 6・7 チェックボックスを更新
