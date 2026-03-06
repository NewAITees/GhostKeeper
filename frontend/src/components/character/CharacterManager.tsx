/**
 * CharacterManager.tsx
 * テンプレートキャラクター管理画面
 *
 * 使い方:
 *   <CharacterManager
 *     onBack={() => setView('sessionList')}
 *     onCreateNew={() => setView('characterCreator')}
 *   />
 *
 * 機能:
 *   - テンプレートキャラクター一覧表示
 *   - キャラクター削除
 *   - 新規作成画面への遷移
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import type { Character } from '../../types'
import styles from './CharacterManager.module.css'

interface Props {
  onBack: () => void
  onCreateNew: () => void
}

export default function CharacterManager({ onBack, onCreateNew }: Props) {
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadCharacters = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await api.listTemplateCharacters()
      setCharacters(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : '読み込みに失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadCharacters()
  }, [loadCharacters])

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`「${name}」を削除しますか？`)) return
    setDeletingId(id)
    try {
      await api.deleteCharacter(id)
      setCharacters((prev) => prev.filter((c) => c.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : '削除に失敗しました')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>
          ← 戻る
        </button>
        <h1 className={styles.title}>キャラクター管理</h1>
        <button className={styles.createBtn} onClick={onCreateNew}>
          ＋ 新規作成
        </button>
      </header>

      <main className={styles.main}>
        {loading && <p className={styles.stateText}>読み込み中...</p>}

        {error && <p className={styles.errorText}>{error}</p>}

        {!loading && !error && characters.length === 0 && (
          <div className={styles.empty}>
            <p className={styles.emptyText}>キャラクターがいません</p>
            <p className={styles.emptyHint}>
              「新規作成」からキャラクターを作成してください
            </p>
            <button className={styles.createBtnLarge} onClick={onCreateNew}>
              ＋ 新しいキャラクターを作成
            </button>
          </div>
        )}

        <div className={styles.list}>
          {characters.map((char) => (
            <CharacterCard
              key={char.id}
              character={char}
              onDelete={handleDelete}
              isDeleting={deletingId === char.id}
            />
          ))}
        </div>
      </main>
    </div>
  )
}

interface CardProps {
  character: Character
  onDelete: (id: string, name: string) => void
  isDeleting: boolean
}

function CharacterCard({ character, onDelete, isDeleting }: CardProps) {
  const hp = character.hp_max
  const san = character.san_max
  const mp = character.mp_max

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardName}>{character.name}</div>
        {character.occupation && (
          <span className={styles.occupation}>{character.occupation}</span>
        )}
      </div>

      <div className={styles.stats}>
        <StatBadge label="HP" value={hp} />
        <StatBadge label="SAN" value={san} />
        <StatBadge label="MP" value={mp} />
        <StatBadge label="STR" value={character.str} />
        <StatBadge label="CON" value={character.con} />
        <StatBadge label="INT" value={character.int} />
        <StatBadge label="DEX" value={character.dex} />
        <StatBadge label="EDU" value={character.edu} />
      </div>

      {character.backstory && (
        <p className={styles.backstory}>{character.backstory}</p>
      )}

      <div className={styles.skillList}>
        {Object.entries(character.skills)
          .slice(0, 5)
          .map(([name, data]) => (
            <span key={name} className={styles.skill}>
              {name}: {data.current}
            </span>
          ))}
        {Object.keys(character.skills).length > 5 && (
          <span className={styles.skillMore}>
            +{Object.keys(character.skills).length - 5}
          </span>
        )}
      </div>

      <div className={styles.cardFooter}>
        <button
          className={styles.deleteBtn}
          onClick={() => onDelete(character.id, character.name)}
          disabled={isDeleting}
        >
          {isDeleting ? '削除中...' : '削除'}
        </button>
      </div>
    </div>
  )
}

function StatBadge({ label, value }: { label: string; value: number }) {
  return (
    <span className={styles.statBadge}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
    </span>
  )
}
