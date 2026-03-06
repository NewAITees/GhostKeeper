/**
 * hooks/useChat.ts
 * チャット送受信の薄いラッパーフック
 *
 * 使い方:
 *   const { send, loading } = useChat(sessionId)
 *   await send('図書館を調べる')
 *
 * 注意:
 *   ゲーム状態の管理は useGame.ts が担うため、
 *   このフックは単体でのチャット操作用に提供している。
 */

import { useState, useCallback } from 'react'
import { api } from '../api/client'
import type { AIResponse } from '../types'

interface UseChatReturn {
  send: (sessionId: string, message: string) => Promise<AIResponse | null>
  loading: boolean
  error: string | null
}

export function useChat(): UseChatReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = useCallback(async (sessionId: string, message: string): Promise<AIResponse | null> => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.sendChat(sessionId, message)
      return response
    } catch (err) {
      const msg = err instanceof Error ? err.message : '送信エラー'
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { send, loading, error }
}
