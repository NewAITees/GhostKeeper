/**
 * types/index.ts
 * GhostKeeper フロントエンド TypeScript 型定義
 *
 * バックエンドAPIレスポンスに合わせた型定義一式。
 * フロント独自の表示用型（DisplayMessage）も含む。
 */

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

// キャラクター（テンプレート）
export interface Character {
  id: string
  session_id: string | null
  name: string
  is_pc: boolean
  is_template: boolean
  image_id: string | null
  occupation: string | null
  backstory: string | null
  personality: string | null
  str: number
  con: number
  siz: number
  int: number
  dex: number
  pow: number
  app: number
  edu: number
  luk: number
  hp_max: number
  hp_current: number
  mp_max: number
  mp_current: number
  san_max: number
  san_current: number
  san_indefinite: number
  skills: Record<string, { base: number; current: number; growth: boolean }>
}

// キャラクター作成リクエストボディ
export interface CharacterCreateBody {
  name: string
  age: number
  occupation?: string
  backstory?: string
  str_: number
  con: number
  siz: number
  int_: number
  dex: number
  pow_: number
  app: number
  edu: number
  luk: number
  skills?: Record<string, { base: number; current: number; growth: boolean }>
}

// 職業
export interface Occupation {
  id: string
  name: string
  description: string
  skill_points_formula: string
  credit_rating: string
  typical_skills: string[]
}

// ダイスロール結果（occupations/roll-stats）
export interface RolledStats {
  str_: number
  con: number
  siz: number
  int_: number
  dex: number
  pow_: number
  app: number
  edu: number
  luk: number
  roll_details: Record<string, number[]>
}

// ダイス結果（AIレスポンスの dice_results フィールド）
export interface DiceResult {
  skill?: string
  type?: string
  rolled?: number
  total?: number
  skill_value?: number
  result?: string
  result_ja?: string
  rolls?: number[]
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
  dice_results: DiceResult[]
  turn_summary?: Record<string, unknown> | null
  session_summary?: Record<string, unknown> | null
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
  skillValue?: number      // 技能値
  resultJa?: string        // 日本語結果（クリティカル！、成功 等）
  timestamp: string
}

// 画像
export interface CharacterImages {
  [characterId: string]: string[]  // 表情ファイル名リスト
}
