/**
 * hooks/useGame.ts
 * ゲーム状態（チャット・キャラ・画像）を管理するカスタムフック
 *
 * 使い方:
 *   const { session, pc, npcs, displayMessages, choices, currentImage, isSending, sendMessage, error } = useGame(sessionId)
 *
 * sendMessage の処理フロー:
 *   1. プレイヤーメッセージを displayMessages に追加（楽観的更新、GAME_START は除外）
 *   2. choices をクリア
 *   3. isSending = true
 *   4. api.sendChat() 呼び出し
 *   5. dice_results があれば dice メッセージとして追加
 *   6. AIResponse を元に各種 displayMessages 追加
 *   7. stat_updates を pc に反映
 *   8. image を currentImage に反映
 *   9. choices を更新
 *   10. isSending = false
 *
 * GAME_START 自動送信:
 *   - sessionId が設定されてチャット履歴が空なら自動で [GAME_START] を送信
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import type {
  SessionDetail,
  CharacterSummary,
  DisplayMessage,
  ImageRef,
  ChatMessage,
} from '../types'

interface NpcInfo {
  id: string
  name: string
  is_pc: boolean
  hp_current: number
  hp_max: number
  san_current: number
  san_max: number
  mp_current: number
  mp_max: number
  personality?: string | null
  npc_memory?: Record<string, unknown>
}

interface UseGameReturn {
  session: SessionDetail | null
  pc: CharacterSummary | null
  npcs: NpcInfo[]
  displayMessages: DisplayMessage[]
  choices: string[]
  currentImage: ImageRef | null
  isSending: boolean
  sendMessage: (message: string) => Promise<void>
  error: string | null
}

const GAME_START_TRIGGER = '[GAME_START]'

let idCounter = 0
function nextId(): string {
  idCounter += 1
  return `msg-${Date.now()}-${idCounter}`
}

function historyToDisplay(msg: ChatMessage): DisplayMessage {
  return {
    id: `hist-${msg.id}`,
    type: msg.role === 'player' ? 'player' : msg.role === 'gm' ? 'gm' : 'system',
    content: msg.content,
    timestamp: msg.created_at,
  }
}

export function useGame(sessionId: string): UseGameReturn {
  const [session, setSession] = useState<SessionDetail | null>(null)
  const [pc, setPc] = useState<CharacterSummary | null>(null)
  const [npcs, setNpcs] = useState<NpcInfo[]>([])
  const [displayMessages, setDisplayMessages] = useState<DisplayMessage[]>([])
  const [choices, setChoices] = useState<string[]>([])
  const [currentImage, setCurrentImage] = useState<ImageRef | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const gameStartSentRef = useRef(false)

  // 初期化: セッション情報・キャラ情報・チャット履歴を取得
  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        const [sessionData, history] = await Promise.all([
          api.getSession(sessionId),
          api.getChatHistory(sessionId),
        ])
        if (cancelled) return

        setSession(sessionData)

        // PCキャラを取得
        const pcChar = sessionData.characters.find((c) => c.is_pc)
        if (pcChar) {
          setPc(pcChar)
        }

        // NPCリストを更新
        const npcList = (sessionData.characters as NpcInfo[]).filter((c) => !c.is_pc)
        setNpcs(npcList)

        // 履歴を DisplayMessage に変換
        const converted = history.map(historyToDisplay)
        setDisplayMessages(converted)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '初期化に失敗しました')
        }
      }
    }

    void init()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const sendMessage = useCallback(
    async (message: string) => {
      const isGameStart = message === GAME_START_TRIGGER
      const now = new Date().toISOString()

      // GAME_START は楽観的追加しない
      if (!isGameStart) {
        const playerMsg: DisplayMessage = {
          id: nextId(),
          type: 'player',
          content: message,
          timestamp: now,
        }
        setDisplayMessages((prev) => [...prev, playerMsg])
      }

      // 選択肢クリア
      setChoices([])

      // 送信中フラグ
      setIsSending(true)
      setError(null)

      try {
        // API呼び出し
        const response = await api.sendChat(sessionId, message)

        // AIResponse → DisplayMessage 変換
        const newMessages: DisplayMessage[] = []
        const ts = new Date().toISOString()

        // ダイス結果（gm_narration より前に表示）
        for (const dice of response.dice_results ?? []) {
          newMessages.push({
            id: nextId(),
            type: 'dice',
            content: dice.skill ? `${dice.skill}判定` : (dice.type ?? 'ダイス'),
            diceNotation: dice.skill ? '1d100' : dice.type,
            diceResult: dice.rolled ?? dice.total,
            skillResult: dice.result,
            skillValue: dice.skill_value,
            resultJa: dice.result_ja,
            timestamp: ts,
          })
        }

        // GMナレーション
        if (response.gm_narration) {
          newMessages.push({
            id: nextId(),
            type: 'gm',
            content: response.gm_narration,
            timestamp: ts,
          })
        }

        // NPCセリフ
        for (const npc of response.npc_dialogues) {
          newMessages.push({
            id: nextId(),
            type: 'npc',
            content: npc.message,
            characterName: npc.character,
            emotion: npc.emotion,
            timestamp: ts,
          })
        }

        setDisplayMessages((prev) => [...prev, ...newMessages])

        // stat_updates を pc に反映
        if (response.stat_updates.length > 0) {
          setPc((prev) => {
            if (!prev) return prev
            let updated = { ...prev }
            for (const upd of response.stat_updates) {
              if (upd.target !== 'pc') continue
              if (upd.field === 'hp') {
                updated = {
                  ...updated,
                  hp_current: Math.max(0, Math.min(updated.hp_max, updated.hp_current + upd.delta)),
                }
              } else if (upd.field === 'san') {
                updated = {
                  ...updated,
                  san_current: Math.max(0, Math.min(updated.san_max, updated.san_current + upd.delta)),
                }
              } else if (upd.field === 'mp') {
                updated = {
                  ...updated,
                  mp_current: Math.max(0, Math.min(updated.mp_max, updated.mp_current + upd.delta)),
                }
              }
            }
            return updated
          })
        }

        // image を currentImage に反映
        if (response.image) {
          setCurrentImage(response.image)
        }

        // choices を更新
        setChoices(response.choices ?? [])

        // セッション情報（NPC）を更新
        try {
          const updatedSession = await api.getSession(sessionId)
          setSession(updatedSession)
          const updatedNpcs = (updatedSession.characters as NpcInfo[]).filter((c) => !c.is_pc)
          setNpcs(updatedNpcs)
        } catch {
          // セッション更新失敗は無視
        }
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'エラーが発生しました'
        const isOllamaDown =
          errMsg.includes('503') ||
          errMsg.toLowerCase().includes('service unavailable') ||
          errMsg.toLowerCase().includes('fetch')

        const systemMsg: DisplayMessage = {
          id: nextId(),
          type: 'system',
          content: isOllamaDown
            ? 'GMが応答しません。Ollamaを起動してください。'
            : `エラー: ${errMsg}`,
          timestamp: new Date().toISOString(),
        }
        setDisplayMessages((prev) => [...prev, systemMsg])
        setError(errMsg)
      } finally {
        // 送信中フラグを解除
        setIsSending(false)
      }
    },
    [sessionId],
  )

  // ゲーム画面に入った時、チャット履歴が空なら自動で GAME_START を送信
  useEffect(() => {
    if (
      sessionId &&
      displayMessages.length === 0 &&
      !isSending &&
      !gameStartSentRef.current &&
      session !== null  // セッション初期化完了後
    ) {
      gameStartSentRef.current = true
      void sendMessage(GAME_START_TRIGGER)
    }
  }, [sessionId, displayMessages.length, isSending, session, sendMessage])

  return {
    session,
    pc,
    npcs,
    displayMessages,
    choices,
    currentImage,
    isSending,
    sendMessage,
    error,
  }
}
