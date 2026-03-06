/**
 * api/client.ts
 * GhostKeeper APIクライアント（fetch wrapper）
 *
 * 使い方:
 *   import { api } from '../api/client'
 *   const sessions = await api.listSessions()
 *   await api.sendChat(sessionId, 'テキスト')
 *
 * 依存:
 *   - ../types/index.ts （型定義）
 *
 * 注意:
 *   - BASE は '' (空文字) → Viteプロキシ経由でバックエンドへ転送
 *   - /api, /images は vite.config.ts で localhost:18000 にプロキシ設定済み
 *   - HTTPエラー時は Error をthrow する
 *   - 204 No Content は undefined を返す
 */

import type {
  Session,
  SessionDetail,
  ChatMessage,
  AIResponse,
  CharacterSummary,
  Character,
  CharacterCreateBody,
  Occupation,
  RolledStats,
} from '../types'

const BASE = ''

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // Sessions
  listSessions: () => req<Session[]>('/api/sessions'),
  createSession: (body: { name: string; mode: string; character_id: string; scenario_id?: string }) =>
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

  // Characters (templates)
  listTemplateCharacters: () => req<Character[]>('/api/characters'),
  createCharacter: (body: CharacterCreateBody) =>
    req<Character>('/api/characters', { method: 'POST', body: JSON.stringify(body) }),
  getCharacter: (id: string) => req<CharacterSummary>(`/api/characters/${id}`),
  deleteCharacter: (id: string) =>
    req<void>(`/api/characters/${id}`, { method: 'DELETE' }),

  // Occupations
  listOccupations: () => req<Occupation[]>('/api/occupations'),
  rollStats: () =>
    req<RolledStats>('/api/occupations/roll-stats', { method: 'POST' }),

  // Images
  imageUrl: (path: string) => `/images/${path}`,
  listCharacterImages: () =>
    req<{ characters: Record<string, string[]> }>('/api/images/characters'),

  // Scenarios
  listScenarios: () =>
    req<Array<{ id: string; title: string; description: string; era: string; location: string }>>(
      '/api/scenarios'
    ),
}
