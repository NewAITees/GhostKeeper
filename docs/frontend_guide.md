# GhostKeeper フロントエンド実装ガイド（Phase 5）

## 前提

- 作業ディレクトリ: `/home/perso/analysis/GhostKeeper/frontend/`
- React 19 + Vite 7 + TypeScript 5（セットアップ済み）
- バックエンド: `http://localhost:8000`
- 画像配信: `http://localhost:8000/images/{path}`
- スタイル: CSS Modules（外部UIライブラリなし、ホラーテーマ）
- 状態管理: React hooks のみ（Redux/Zustand 不要）

実装前に必ず `tasks/todo.md` を確認し、完了タスクに `[x]` を付けること。

---

## 画面構成

### 画面1: セッション一覧（ホーム）

```
┌───────────────────────────────────────────┐
│  👻 GhostKeeper                            │
│  ─────────────────────────────────────    │
│                                           │
│  [＋ 新しいシナリオを始める]              │
│                                           │
│  ── 保存済みセッション ──                 │
│  ┌─────────────────────────────────────┐ │
│  │ 怪異の館                             │ │
│  │ 2026-02-27 / フリーモード           │ │
│  │                    [再開]  [削除]   │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │ ...                                  │ │
│  └─────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

### 画面2: ゲーム画面

```
┌──────────────────────────────────────────────────────────┐
│ ← セッション名                                            │
├──────────────────────────────────┬───────────────────────┤
│                                  │  [立ち絵エリア]        │
│  チャットエリア（スクロール）    │  ┌─────────────────┐  │
│                                  │  │                 │  │
│  [GM] 薄暗い図書館の奥に...     │  │   キャラ立ち絵  │  │
│                                  │  │                 │  │
│  [ハーディ]                     │  └─────────────────┘  │
│  「ここには何かあります...」     │                        │
│                                  │  探索者               │
│  🎲 図書館 (1d100=45)           │  HP  ████████░░ 8/10  │
│     ハード成功！                │  SAN █████████░ 40/50 │
│                                  │  MP  ████░░░░░░ 4/10  │
│  [あなた] 文献を調べる          │                        │
│                                  │                        │
├──────────────────────────────────┴───────────────────────┤
│  [書架を調べる]  [出口へ向かう]  [呪文書を持ち帰る]      │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐  [送信]    │
│  │  行動を入力...                           │            │
│  └─────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────┘
```

---

## ディレクトリ構成（作成すること）

```
frontend/src/
├── api/
│   └── client.ts          # APIクライアント（fetch wrapper）
├── components/
│   ├── session/
│   │   ├── SessionList.tsx
│   │   ├── SessionList.module.css
│   │   ├── SessionCard.tsx
│   │   ├── SessionCard.module.css
│   │   ├── SessionCreate.tsx  # 作成モーダル
│   │   └── SessionCreate.module.css
│   ├── game/
│   │   ├── GameScreen.tsx        # ゲーム画面全体
│   │   ├── GameScreen.module.css
│   │   ├── ChatArea.tsx          # チャット履歴エリア
│   │   ├── ChatArea.module.css
│   │   ├── ChatMessage.tsx       # 個別メッセージ（GM/NPC/Player/Dice）
│   │   ├── ChatMessage.module.css
│   │   ├── ChoiceButtons.tsx     # 選択肢ボタン群
│   │   ├── ChoiceButtons.module.css
│   │   ├── ChatInput.tsx         # テキスト入力+送信
│   │   ├── ChatInput.module.css
│   │   ├── CharacterPortrait.tsx # 立ち絵
│   │   ├── CharacterPortrait.module.css
│   │   ├── CharacterSheet.tsx    # HP/SAN/MPバー + スタッツ
│   │   └── CharacterSheet.module.css
│   └── common/
│       ├── StatBar.tsx           # HP/SAN/MP共通バーコンポーネント
│       └── StatBar.module.css
├── hooks/
│   ├── useSession.ts       # セッション一覧・作成・削除
│   ├── useGame.ts          # ゲーム状態（チャット・キャラ・画像）
│   └── useChat.ts          # チャット送受信
├── types/
│   └── index.ts            # TypeScript 型定義
├── App.tsx                 # ルーティング（セッション一覧 ↔ ゲーム画面）
├── App.module.css
├── main.tsx                # エントリポイント（変更不要）
└── index.css               # グローバルスタイル（ホラーテーマ）
```

---

## TypeScript 型定義（types/index.ts）

バックエンドのAPIレスポンスに合わせて定義する。

```typescript
// セッション
export interface Session {
  id: string
  name: string
  mode: 'template' | 'free'
  scenario_id: string | null
  created_at: string
  updated_at: string
}

export interface SessionDetail extends Session {
  characters: CharacterSummary[]
}

// キャラクター
export interface CharacterSummary {
  id: string
  name: string
  is_pc: boolean
  hp_current: number
  hp_max: number
  san_current: number
  san_max: number
  mp_current: number
  mp_max: number
}

// チャット
export type MessageRole = 'player' | 'gm' | 'system'

export interface ChatMessage {
  id: number
  role: MessageRole
  content: string
  created_at: string
}

// AI応答（POST /api/sessions/{id}/chat のレスポンス）
export interface NpcDialogue {
  character: string
  message: string
  emotion: 'normal' | 'scared' | 'angry' | 'dead'
}

export interface DiceRequest {
  type: string
  skill: string
  character: string
  difficulty: 'normal' | 'hard' | 'extreme'
}

export interface StatUpdate {
  target: string
  field: 'hp' | 'san' | 'mp'
  delta: number
  reason: string
}

export interface ImageRef {
  type: 'character' | 'scene'
  id: string
  expression: string
}

export interface AIResponse {
  thinking: string
  gm_narration: string
  npc_dialogues: NpcDialogue[]
  dice_requests: DiceRequest[]
  stat_updates: StatUpdate[]
  image: ImageRef | null
  choices: string[]
  game_event: 'none' | 'combat_start' | 'san_check' | 'skill_check' | 'scenario_end'
}

// フロント独自: 表示用メッセージ（DB保存済み + AI応答の付加情報）
export type DisplayMessageType = 'gm' | 'npc' | 'player' | 'dice' | 'system'

export interface DisplayMessage {
  id: string
  type: DisplayMessageType
  content: string
  characterName?: string   // NPC発言時
  emotion?: string         // NPC立ち絵の表情
  diceNotation?: string    // ダイス種別
  diceResult?: number      // ダイスの目
  skillResult?: string     // 成功/ハード成功 等
  timestamp: string
}

// 画像
export interface CharacterImages {
  [characterId: string]: string[]  // 表情ファイル名リスト
}
```

---

## APIクライアント（api/client.ts）

```typescript
const BASE = 'http://localhost:8000'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  // Sessions
  listSessions: () => req<Session[]>('/api/sessions'),
  createSession: (body: { name: string; mode: string; pc_name: string }) =>
    req<Session>('/api/sessions', { method: 'POST', body: JSON.stringify(body) }),
  getSession: (id: string) => req<SessionDetail>(`/api/sessions/${id}`),
  deleteSession: (id: string) =>
    req<void>(`/api/sessions/${id}`, { method: 'DELETE' }),

  // Chat
  getChatHistory: (sessionId: string) =>
    req<ChatMessage[]>(`/api/sessions/${sessionId}/chat`),
  sendChat: (sessionId: string, message: string) =>
    req<AIResponse>(`/api/sessions/${sessionId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  // Characters
  getCharacter: (id: string) => req<CharacterSummary>(`/api/characters/${id}`),

  // Images
  imageUrl: (path: string) => `${BASE}/images/${path}`,
  listCharacterImages: () =>
    req<{ characters: Record<string, string[]> }>('/api/images/characters'),
}
```

---

## グローバルスタイル（index.css）

ホラー・クトゥルフらしい暗いテーマ。

```css
:root {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-panel: #161620;
  --bg-card: #1a1a28;
  --accent: #7c4dff;        /* 紫 - 神秘・魔術 */
  --accent-dim: #4a2d99;
  --danger: #c62828;        /* 赤 - 危険・SAN喪失 */
  --warning: #f57c00;       /* オレンジ - 警告 */
  --success: #2e7d32;       /* 緑 - 成功 */
  --text-primary: #e8e0d0;  /* クリーム - 古い紙の色 */
  --text-secondary: #a09880;
  --text-muted: #6a6054;
  --border: #2a2a3a;
  --san-color: #7c4dff;     /* SAN = 紫 */
  --hp-color: #c62828;      /* HP = 赤 */
  --mp-color: #1565c0;      /* MP = 青 */

  font-family: 'Noto Serif JP', 'Georgia', serif;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  min-height: 100vh;
  background: var(--bg-primary);
  /* 微妙なノイズテクスチャ感を出す */
  background-image: radial-gradient(ellipse at top, #1a1a2e 0%, #0a0a0f 70%);
}

button {
  cursor: pointer;
  font-family: inherit;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
```

---

## 各コンポーネント仕様

### App.tsx

2つのビューを切り替える（ルーターなし）。

```tsx
type View =
  | { screen: 'sessionList' }
  | { screen: 'game'; sessionId: string }

export default function App() {
  const [view, setView] = useState<View>({ screen: 'sessionList' })

  if (view.screen === 'game') {
    return (
      <GameScreen
        sessionId={view.sessionId}
        onBack={() => setView({ screen: 'sessionList' })}
      />
    )
  }
  return (
    <SessionList
      onEnterSession={(id) => setView({ screen: 'game', sessionId: id })}
    />
  )
}
```

---

### SessionList.tsx

- セッション一覧を取得して表示
- 「新しいシナリオを始める」ボタンで `SessionCreate` モーダル表示

Props:
```typescript
interface Props {
  onEnterSession: (sessionId: string) => void
}
```

---

### SessionCreate.tsx（モーダル）

フォーム項目:
- **シナリオ名** (text input, 必須)
- **探索者の名前** (text input, デフォルト「探索者」)
- **モード**: フリー / テンプレート (radio)
- [開始する] ボタン → `api.createSession()` → 成功したら `onEnterSession(id)`

---

### GameScreen.tsx

ゲーム画面の全体レイアウトを管理するコンポーネント。

**状態:**
- `session: SessionDetail | null`
- `pc: CharacterSummary | null`
- `displayMessages: DisplayMessage[]`
- `choices: string[]`
- `currentImage: ImageRef | null`（現在表示中の画像）
- `isSending: boolean`

**処理フロー（チャット送信時）:**
1. プレイヤーメッセージを `displayMessages` に追加（楽観的更新）
2. `api.sendChat()` を呼ぶ
3. `AIResponse` を受け取ったら:
   - `gm_narration` → GM表示メッセージを追加
   - `npc_dialogues` → NPC表示メッセージを追加（各セリフごとに）
   - `dice_requests` → ダイス結果表示メッセージを追加
   - `stat_updates` → `pc` の HP/SAN/MP を更新
   - `image` → `currentImage` を更新
   - `choices` → `choices` を更新

```tsx
interface Props {
  sessionId: string
  onBack: () => void
}
```

**レイアウト（CSS Grid）:**
```css
/* GameScreen.module.css */
.layout {
  display: grid;
  grid-template-rows: 48px 1fr auto auto;
  grid-template-columns: 1fr 280px;
  height: 100dvh;
  overflow: hidden;
}
.header  { grid-column: 1 / -1; }
.chat    { grid-column: 1; grid-row: 2; overflow: hidden; }
.sidebar { grid-column: 2; grid-row: 2 / 5; }
.choices { grid-column: 1; grid-row: 3; }
.input   { grid-column: 1; grid-row: 4; }
```

---

### ChatArea.tsx

スクロール可能なメッセージリスト。新しいメッセージが追加されたら自動スクロール（`useEffect` + `ref.scrollIntoView()`）。

```tsx
interface Props {
  messages: DisplayMessage[]
  isSending: boolean
}
```

メッセージを `DisplayMessage.type` によって分岐して `ChatMessage` に渡す。

---

### ChatMessage.tsx

```tsx
interface Props {
  message: DisplayMessage
}
```

| type | 表示内容 |
|------|---------|
| `gm` | 🕯️ GMバッジ + 斜体テキスト（クリーム色） |
| `npc` | キャラ名バッジ（紫） + セリフ |
| `player` | 右寄せ + 「あなた」バッジ（暗いグレー） |
| `dice` | 🎲アイコン + ダイス記法 + 結果数値 + 判定結果 |
| `system` | 中央揃え + 薄いテキスト（区切り線風） |

---

### ChoiceButtons.tsx

```tsx
interface Props {
  choices: string[]
  onChoose: (choice: string) => void
  disabled: boolean
}
```

- 各選択肢をボタン表示
- `disabled=true` の時はグレーアウト（送信中）
- 選択後、そのテキストを `onChoose` に渡す（ChatInput と同じ送信処理）

---

### ChatInput.tsx

```tsx
interface Props {
  onSend: (message: string) => void
  disabled: boolean
}
```

- `<textarea>` + `Enter` で送信（Shift+Enter は改行）
- 送信中（`disabled`）は入力欄グレーアウト + ボタン無効化
- 送信後はテキストクリア

---

### CharacterPortrait.tsx

```tsx
interface Props {
  imageRef: ImageRef | null
}
```

- `imageRef.type === 'character'` の場合: `http://localhost:8000/images/characters/{id}/{expression}.png`（またはjpg/webp）
- `imageRef.type === 'scene'` の場合: 背景として表示（`CharacterSheet` の上に重ねる）
- 画像がない場合はプレースホルダー（暗い影のシルエット的なCSSで表現）
- 表情切り替え時はフェードトランジション（CSS `transition: opacity 0.3s`）

---

### CharacterSheet.tsx

```tsx
interface Props {
  character: CharacterSummary
}
```

表示内容:
- キャラクター名（テキスト）
- HP バー: `StatBar` を使用（赤）
- SAN バー: `StatBar` を使用（紫）
- MP バー: `StatBar` を使用（青）

---

### StatBar.tsx（共通）

```tsx
interface Props {
  label: string
  current: number
  max: number
  color: string  // CSS変数名 or hex
}
```

表示例:
```
HP  ██████░░░░  6 / 10
```

バーの幅: `width: ${(current/max) * 100}%`
HPが残り少ない（<30%）時は点滅アニメーション。

---

## カスタムフック仕様

### hooks/useSession.ts

```typescript
interface UseSessionReturn {
  sessions: Session[]
  loading: boolean
  error: string | null
  createSession: (params: { name: string; mode: string; pc_name: string }) => Promise<Session>
  deleteSession: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

export function useSession(): UseSessionReturn
```

### hooks/useGame.ts

```typescript
interface UseGameReturn {
  session: SessionDetail | null
  pc: CharacterSummary | null
  displayMessages: DisplayMessage[]
  choices: string[]
  currentImage: ImageRef | null
  isSending: boolean
  sendMessage: (message: string) => Promise<void>
  error: string | null
}

export function useGame(sessionId: string): UseGameReturn
```

`sendMessage` の内部処理:
1. プレイヤーメッセージを `displayMessages` に追加
2. `choices` をクリア
3. `isSending = true`
4. `api.sendChat()` 呼び出し
5. AIResponseを元に各種 `displayMessages` 追加
6. `stat_updates` を `pc` に反映（ローカル状態更新）
7. `image` を `currentImage` に反映
8. `choices` を更新
9. `isSending = false`

---

## vite.config.ts の修正

バックエンドへのプロキシを追加する（開発時のCORS回避）:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/images': 'http://localhost:8000',
    },
  },
})
```

プロキシ設定後、`api/client.ts` の BASE を `''`（空文字）に変更すること。

---

## 完了条件

- [ ] `npm run dev` でゲーム画面が表示される
- [ ] セッション作成 → ゲーム画面遷移が動作する
- [ ] チャット送信 → AI応答がチャットエリアに表示される（Ollama起動要）
- [ ] HP/SAN/MP バーがリアルタイムで更新される
- [ ] 選択肢ボタンがクリックで送信される
- [ ] `npm run build` がエラーなし
- [ ] `npm run lint` がエラーなし

---

## 注意事項

- `useEffect` の依存配列に漏れを作らないこと（eslint-plugin-react-hooks が警告する）
- 画像が存在しない場合（404）は `onError` で代替表示に切り替えること
- `isSending` が true の間は選択肢ボタン・送信ボタン両方を無効化すること
- Ollama が未起動の場合、503エラーを受け取る。「GMが応答しません。Ollamaを起動してください。」のエラーメッセージをチャットエリアに system メッセージとして表示する
- ゲーム履歴のロード（`getChatHistory`）は `useGame` の初期化時に行い、`ChatMessage[]` → `DisplayMessage[]` に変換して表示する。
  - roleが`gm`のものは `type: 'gm'`、roleが`player`のものは `type: 'player'` に変換する
