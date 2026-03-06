/**
 * SessionCard.tsx
 * 保存済みセッション1件を表示するカードコンポーネント
 *
 * 使い方:
 *   <SessionCard session={session} onEnter={handleEnter} onDelete={handleDelete} />
 */

import type { Session } from '../../types'
import styles from './SessionCard.module.css'

interface Props {
  session: Session
  onEnter: (id: string) => void
  onDelete: (id: string) => void
}

export default function SessionCard({ session, onEnter, onDelete }: Props) {
  const date = new Date(session.created_at).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const modeLabel = session.mode === 'free' ? 'フリーモード' : 'テンプレート'

  function handleDelete() {
    if (confirm(`「${session.name}」を削除しますか？`)) {
      onDelete(session.id)
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.info}>
        <span className={styles.name}>{session.name}</span>
        <span className={styles.meta}>
          {date} / {modeLabel}
        </span>
      </div>
      <div className={styles.actions}>
        <button
          className={styles.btnEnter}
          onClick={() => onEnter(session.id)}
        >
          再開
        </button>
        <button
          className={styles.btnDelete}
          onClick={handleDelete}
        >
          削除
        </button>
      </div>
    </div>
  )
}
