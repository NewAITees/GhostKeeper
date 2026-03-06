/**
 * SessionList.tsx
 * セッション一覧ホーム画面コンポーネント
 *
 * 使い方:
 *   <SessionList
 *     onEnterSession={(id) => setView({ screen: 'game', sessionId: id })}
 *     onGoToCharacterManager={() => setView({ screen: 'characterManager' })}
 *   />
 *
 * - セッション一覧を取得して表示
 * - 「新しいシナリオを始める」ボタンで SessionCreate モーダル表示
 * - 「キャラクターを管理する」ボタンでキャラクター管理画面へ遷移
 */

import { useState } from 'react'
import { useSession } from '../../hooks/useSession'
import { api } from '../../api/client'
import SessionCard from './SessionCard'
import SessionCreate from './SessionCreate'
import styles from './SessionList.module.css'

interface Props {
  onEnterSession: (sessionId: string) => void
  onGoToCharacterManager: () => void
}

export default function SessionList({ onEnterSession, onGoToCharacterManager }: Props) {
  const { sessions, loading, error, refresh, deleteSession } = useSession()
  const [showCreate, setShowCreate] = useState(false)

  async function handleCreate(params: { name: string; mode: string; character_id: string; scenario_id?: string }) {
    const session = await api.createSession(params)
    await refresh()
    setShowCreate(false)
    onEnterSession(session.id)
  }

  async function handleDelete(id: string) {
    await deleteSession(id)
    await refresh()
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.logo}>GhostKeeper</h1>
        <p className={styles.tagline}>クトゥルフ神話 TRPG - AIマスター</p>
      </header>

      <main className={styles.main}>
        <div className={styles.actionButtons}>
          <button
            className={styles.btnNew}
            onClick={() => setShowCreate(true)}
          >
            ＋ 新しいシナリオを始める
          </button>
          <button
            className={styles.btnCharacter}
            onClick={onGoToCharacterManager}
          >
            キャラクターを管理する
          </button>
        </div>

        <section className={styles.sessionSection}>
          <h2 className={styles.sectionTitle}>── 保存済みセッション ──</h2>

          {loading && (
            <p className={styles.stateText}>読み込み中...</p>
          )}

          {error && (
            <p className={styles.errorText}>{error}</p>
          )}

          {!loading && !error && sessions.length === 0 && (
            <p className={styles.stateText}>
              保存済みセッションはありません
            </p>
          )}

          <div className={styles.list}>
            {sessions.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                onEnter={onEnterSession}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </section>
      </main>

      {showCreate && (
        <SessionCreate
          onCreate={handleCreate}
          onClose={() => setShowCreate(false)}
          onGoToCharacterManager={() => {
            setShowCreate(false)
            onGoToCharacterManager()
          }}
        />
      )}
    </div>
  )
}
