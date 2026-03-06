/**
 * SessionCreate.tsx
 * 新規セッション作成モーダルコンポーネント
 *
 * 使い方:
 *   <SessionCreate
 *     onCreate={async (params) => { const s = await api.createSession(params); ... }}
 *     onClose={() => setShowCreate(false)}
 *     onGoToCharacterManager={() => setView('characterManager')}
 *   />
 *
 * フォーム項目:
 *   - シナリオ名 (必須)
 *   - キャラクター選択 (必須)
 *   - モード: フリー / テンプレート
 */

import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { Character } from '../../types'
import styles from './SessionCreate.module.css'

interface ScenarioSummary {
  id: string
  title: string
  description: string
  era: string
  location: string
}

interface CreateParams {
  name: string
  mode: string
  character_id: string
  scenario_id?: string
}

interface Props {
  onCreate: (params: CreateParams) => Promise<void>
  onClose: () => void
  onGoToCharacterManager: () => void
}

export default function SessionCreate({ onCreate, onClose, onGoToCharacterManager }: Props) {
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'free' | 'template'>('free')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([])
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('')
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedCharacterId, setSelectedCharacterId] = useState<string>('')
  const [loadingChars, setLoadingChars] = useState(true)

  useEffect(() => {
    api.listScenarios().then((list) => {
      setScenarios(list)
      if (list.length > 0) {
        setSelectedScenarioId(list[0].id)
      }
    }).catch(() => {
      // シナリオ取得失敗は無視（フリーモードのみ使用可能になる）
    })

    api.listTemplateCharacters().then((list) => {
      setCharacters(list)
      if (list.length > 0) {
        setSelectedCharacterId(list[0].id)
      }
    }).catch(() => {
      setError('キャラクター一覧の取得に失敗しました')
    }).finally(() => {
      setLoadingChars(false)
    })
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('シナリオ名を入力してください')
      return
    }
    if (!selectedCharacterId) {
      setError('キャラクターを選択してください')
      return
    }
    if (mode === 'template' && !selectedScenarioId) {
      setError('シナリオを選択してください')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await onCreate({
        name: name.trim(),
        mode,
        character_id: selectedCharacterId,
        scenario_id: mode === 'template' ? selectedScenarioId : undefined,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '作成に失敗しました')
      setLoading(false)
    }
  }

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId)
  const selectedChar = characters.find((c) => c.id === selectedCharacterId)

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-modal-title"
      >
        <h2 id="create-modal-title" className={styles.title}>
          新しいシナリオを始める
        </h2>

        <form onSubmit={(e) => void handleSubmit(e)} className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="scenario-name" className={styles.label}>
              シナリオ名 <span className={styles.required}>*</span>
            </label>
            <input
              id="scenario-name"
              type="text"
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例: 怪異の館"
              autoFocus
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="character-select" className={styles.label}>
              キャラクター <span className={styles.required}>*</span>
            </label>
            {loadingChars ? (
              <p className={styles.loadingText}>読み込み中...</p>
            ) : characters.length === 0 ? (
              <div className={styles.noCharacters}>
                <p className={styles.error}>キャラクターがいません</p>
                <button
                  type="button"
                  className={styles.createCharBtn}
                  onClick={() => {
                    onClose()
                    onGoToCharacterManager()
                  }}
                >
                  キャラクターを作成する →
                </button>
              </div>
            ) : (
              <>
                <select
                  id="character-select"
                  className={styles.input}
                  value={selectedCharacterId}
                  onChange={(e) => setSelectedCharacterId(e.target.value)}
                >
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}{c.occupation ? ` (${c.occupation})` : ''}
                    </option>
                  ))}
                </select>
                {selectedChar && (
                  <div className={styles.charPreview}>
                    <span className={styles.charStat}>HP: {selectedChar.hp_max}</span>
                    <span className={styles.charStat}>SAN: {selectedChar.san_max}</span>
                    <span className={styles.charStat}>MP: {selectedChar.mp_max}</span>
                    {selectedChar.backstory && (
                      <p className={styles.charBackstory}>{selectedChar.backstory}</p>
                    )}
                  </div>
                )}
                <button
                  type="button"
                  className={styles.createCharLink}
                  onClick={() => {
                    onClose()
                    onGoToCharacterManager()
                  }}
                >
                  ＋ 新しいキャラクターを作成
                </button>
              </>
            )}
          </div>

          <div className={styles.field}>
            <span className={styles.label}>モード</span>
            <div className={styles.radioGroup}>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="mode"
                  value="free"
                  checked={mode === 'free'}
                  onChange={() => setMode('free')}
                  className={styles.radio}
                />
                フリーモード
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="mode"
                  value="template"
                  checked={mode === 'template'}
                  onChange={() => setMode('template')}
                  className={styles.radio}
                />
                テンプレート
              </label>
            </div>
          </div>

          {mode === 'template' && (
            <div className={styles.field}>
              <label htmlFor="scenario-select" className={styles.label}>
                シナリオを選択 <span className={styles.required}>*</span>
              </label>
              {scenarios.length === 0 ? (
                <p className={styles.error}>シナリオが見つかりません</p>
              ) : (
                <>
                  <select
                    id="scenario-select"
                    className={styles.input}
                    value={selectedScenarioId}
                    onChange={(e) => setSelectedScenarioId(e.target.value)}
                  >
                    {scenarios.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title}
                      </option>
                    ))}
                  </select>
                  {selectedScenario && (
                    <div className={styles.scenarioInfo}>
                      {selectedScenario.era && (
                        <p className={styles.scenarioMeta}>{selectedScenario.era} / {selectedScenario.location}</p>
                      )}
                      {selectedScenario.description && (
                        <p className={styles.scenarioDesc}>{selectedScenario.description}</p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.buttons}>
            <button
              type="button"
              className={styles.btnCancel}
              onClick={onClose}
              disabled={loading}
            >
              キャンセル
            </button>
            <button
              type="submit"
              className={styles.btnSubmit}
              disabled={loading || characters.length === 0}
            >
              {loading ? '作成中...' : '開始する'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
