/**
 * hooks/useSession.ts
 * セッション一覧・作成・削除を管理するカスタムフック
 *
 * 使い方:
 *   const { sessions, loading, error, createSession, deleteSession, refresh } = useSession()
 *
 * - マウント時に自動でセッション一覧を取得
 * - refresh() で再取得
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { Session } from '../types'

interface UseSessionReturn {
  sessions: Session[]
  loading: boolean
  error: string | null
  createSession: (params: { name: string; mode: string; character_id: string; scenario_id?: string }) => Promise<Session>
  deleteSession: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

export function useSession(): UseSessionReturn {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.listSessions()
      setSessions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'セッション取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createSession = useCallback(
    async (params: { name: string; mode: string; character_id: string; scenario_id?: string }) => {
      const session = await api.createSession(params)
      return session
    },
    [],
  )

  const deleteSession = useCallback(async (id: string) => {
    await api.deleteSession(id)
    setSessions((prev) => prev.filter((s) => s.id !== id))
  }, [])

  return { sessions, loading, error, createSession, deleteSession, refresh }
}
