/**
 * CharacterCreator.tsx
 * 4ステップのキャラクター作成ウィザード
 *
 * 使い方:
 *   <CharacterCreator onBack={() => setView('characterManager')} onCreated={() => setView('characterManager')} />
 *
 * ステップ:
 *   Step1: 基本情報（名前・年齢・経歴）
 *   Step2: ステータスダイスロール（ランダム生成 + 微調整）
 *   Step3: 職業選択（スキルポイント計算）
 *   Step4: スキル割り振り
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import type { Occupation, RolledStats } from '../../types'
import styles from './CharacterCreator.module.css'

interface Props {
  onBack: () => void
  onCreated: () => void
}

// CoC標準スキル一覧（基本値）
const STANDARD_SKILLS: Record<string, number> = {
  '格闘（拳）': 25,
  '回避': 0,
  '射撃（拳銃）': 20,
  '射撃（ライフル）': 25,
  '目星': 25,
  '聞き耳': 20,
  '図書館': 20,
  '心理学': 10,
  '説得': 10,
  '言いくるめ': 5,
  '応急手当': 30,
  '医学': 1,
  '薬学': 1,
  '法律': 5,
  '会計': 5,
  'コンピューター': 5,
  '電気修理': 10,
  '機械修理': 10,
  '忍び歩き': 20,
  '隠す': 20,
  '変装': 5,
  '追跡': 10,
  '水泳': 20,
  '跳躍': 20,
  '登攀': 20,
  '乗馬': 5,
  '運転（自動車）': 20,
  '操縦（航空機）': 1,
  '航海': 1,
  '写真術': 5,
  '芸術/工芸': 5,
  '歴史': 5,
  '考古学': 1,
  '人類学': 1,
  'オカルト': 5,
  'クトゥルフ神話': 0,
  '言語（英語）': 1,
  '言語（ラテン語）': 1,
  '科学（生物学）': 1,
  '科学（化学）': 1,
  '科学（物理学）': 1,
  '科学（天文学）': 1,
}

interface BasicStats {
  str_: number
  con: number
  siz: number
  int_: number
  dex: number
  pow_: number
  app: number
  edu: number
  luk: number
}

function calcDerived(stats: BasicStats) {
  const hp = Math.floor((stats.con + stats.siz) / 10)
  const mp = Math.floor(stats.pow_ / 5)
  const san = stats.pow_ * 5
  return { hp, mp, san }
}

function calcSkillPoints(occupation: Occupation, stats: BasicStats): number {
  const formula = occupation.skill_points_formula
  // シンプルな計算: EDU×4, EDU×2+DEX×2 等をパース
  let points = 0
  const parts = formula.split('+').map((p) => p.trim())
  for (const part of parts) {
    const m = part.match(/(\w+)×(\d+)/i)
    if (m) {
      const stat = m[1].toUpperCase()
      const mult = parseInt(m[2])
      switch (stat) {
        case 'EDU': points += stats.edu * mult; break
        case 'DEX': points += stats.dex * mult; break
        case 'STR': points += stats.str_ * mult; break
        case 'INT': points += stats.int_ * mult; break
        case 'APP': points += stats.app * mult; break
        case 'POW': points += stats.pow_ * mult; break
      }
    }
  }
  return points
}

export default function CharacterCreator({ onBack, onCreated }: Props) {
  const [step, setStep] = useState(1)

  // Step1: 基本情報
  const [name, setName] = useState('')
  const [age, setAge] = useState(25)
  const [backstory, setBackstory] = useState('')

  // Step2: ステータス
  const [stats, setStats] = useState<BasicStats>({
    str_: 50, con: 50, siz: 55, int_: 55, dex: 50, pow_: 50, app: 50, edu: 60, luk: 50,
  })
  const [isRolling, setIsRolling] = useState(false)

  // Step3: 職業
  const [occupations, setOccupations] = useState<Occupation[]>([])
  const [selectedOccupation, setSelectedOccupation] = useState<Occupation | null>(null)
  const [occupationPoints, setOccupationPoints] = useState(0)
  const [hobbyPoints, setHobbyPoints] = useState(0)

  // Step4: スキル
  const [skillOccPoints, setSkillOccPoints] = useState<Record<string, number>>({})
  const [skillHobbyPoints, setSkillHobbyPoints] = useState<Record<string, number>>({})
  const [remainingOccPoints, setRemainingOccPoints] = useState(0)
  const [remainingHobbyPoints, setRemainingHobbyPoints] = useState(0)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.listOccupations().then(setOccupations).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedOccupation) {
      const occ = calcSkillPoints(selectedOccupation, stats)
      const hob = stats.int_ * 2
      setOccupationPoints(occ)
      setHobbyPoints(hob)
      setRemainingOccPoints(occ)
      setRemainingHobbyPoints(hob)
      setSkillOccPoints({})
      setSkillHobbyPoints({})
    }
  }, [selectedOccupation, stats])

  const handleRoll = useCallback(async () => {
    setIsRolling(true)
    try {
      const result: RolledStats = await api.rollStats()

      // ダイスアニメーション: 500ms間ランダム値でちらつかせる
      const startTime = Date.now()
      const animInterval = setInterval(() => {
        setStats({
          str_: Math.floor(Math.random() * 80) + 20,
          con: Math.floor(Math.random() * 80) + 20,
          siz: Math.floor(Math.random() * 80) + 30,
          int_: Math.floor(Math.random() * 80) + 30,
          dex: Math.floor(Math.random() * 80) + 20,
          pow_: Math.floor(Math.random() * 80) + 20,
          app: Math.floor(Math.random() * 80) + 20,
          edu: Math.floor(Math.random() * 80) + 30,
          luk: Math.floor(Math.random() * 80) + 20,
        })
        if (Date.now() - startTime >= 500) {
          clearInterval(animInterval)
          // 実際の結果をセット
          setStats({
            str_: result.str_,
            con: result.con,
            siz: result.siz,
            int_: result.int_,
            dex: result.dex,
            pow_: result.pow_,
            app: result.app,
            edu: result.edu,
            luk: result.luk,
          })
          setIsRolling(false)
        }
      }, 10)
    } catch {
      setIsRolling(false)
    }
  }, [])

  function adjustStat(key: keyof BasicStats, delta: number) {
    setStats((prev) => ({
      ...prev,
      [key]: Math.max(1, Math.min(100, prev[key] + delta)),
    }))
  }

  function addSkillOccPoints(skill: string, delta: number) {
    const base = STANDARD_SKILLS[skill] ?? 0
    const currentOcc = skillOccPoints[skill] ?? 0
    const currentHob = skillHobbyPoints[skill] ?? 0
    const total = base + currentOcc + currentHob

    if (delta > 0) {
      if (remainingOccPoints <= 0) return
      const newOcc = currentOcc + delta
      if (total + delta > 95) return // 上限95
      setSkillOccPoints((prev) => ({ ...prev, [skill]: newOcc }))
      setRemainingOccPoints((prev) => prev - delta)
    } else {
      if (currentOcc <= 0) return
      const newOcc = currentOcc + delta
      if (newOcc < 0) return
      setSkillOccPoints((prev) => ({ ...prev, [skill]: newOcc }))
      setRemainingOccPoints((prev) => prev - delta)
    }
  }

  function addSkillHobbyPoints(skill: string, delta: number) {
    const base = STANDARD_SKILLS[skill] ?? 0
    const currentOcc = skillOccPoints[skill] ?? 0
    const currentHob = skillHobbyPoints[skill] ?? 0
    const total = base + currentOcc + currentHob

    if (delta > 0) {
      if (remainingHobbyPoints <= 0) return
      if (total + delta > 95) return
      const newHob = currentHob + delta
      setSkillHobbyPoints((prev) => ({ ...prev, [skill]: newHob }))
      setRemainingHobbyPoints((prev) => prev - delta)
    } else {
      if (currentHob <= 0) return
      const newHob = currentHob + delta
      if (newHob < 0) return
      setSkillHobbyPoints((prev) => ({ ...prev, [skill]: newHob }))
      setRemainingHobbyPoints((prev) => prev - delta)
    }
  }

  async function handleSave() {
    if (!name.trim()) {
      setError('名前を入力してください')
      return
    }

    setSaving(true)
    setError(null)

    // スキルデータを構築
    const skills: Record<string, { base: number; current: number; growth: boolean }> = {}
    for (const [skillName, base] of Object.entries(STANDARD_SKILLS)) {
      const occ = skillOccPoints[skillName] ?? 0
      const hob = skillHobbyPoints[skillName] ?? 0
      if (occ > 0 || hob > 0) {
        skills[skillName] = {
          base,
          current: base + occ + hob,
          growth: false,
        }
      }
    }

    try {
      await api.createCharacter({
        name: name.trim(),
        age,
        occupation: selectedOccupation?.name ?? undefined,
        backstory: backstory.trim() || undefined,
        str_: stats.str_,
        con: stats.con,
        siz: stats.siz,
        int_: stats.int_,
        dex: stats.dex,
        pow_: stats.pow_,
        app: stats.app,
        edu: stats.edu,
        luk: stats.luk,
        skills,
      })
      onCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  const derived = calcDerived(stats)

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>
          ← 戻る
        </button>
        <h1 className={styles.title}>キャラクター作成</h1>
        <div className={styles.stepIndicator}>
          {[1, 2, 3, 4].map((s) => (
            <span
              key={s}
              className={`${styles.step} ${step === s ? styles.stepActive : ''} ${step > s ? styles.stepDone : ''}`}
            >
              {s}
            </span>
          ))}
        </div>
      </header>

      <main className={styles.main}>
        {error && <p className={styles.error}>{error}</p>}

        {step === 1 && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Step 1: 基本情報</h2>

            <div className={styles.field}>
              <label className={styles.label}>
                名前 <span className={styles.required}>*</span>
              </label>
              <input
                type="text"
                className={styles.input}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例: 田中一郎"
                autoFocus
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>年齢</label>
              <input
                type="number"
                className={styles.input}
                value={age}
                onChange={(e) => setAge(Math.max(15, Math.min(90, parseInt(e.target.value) || 25)))}
                min={15}
                max={90}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>経歴・背景（任意）</label>
              <textarea
                className={styles.textarea}
                value={backstory}
                onChange={(e) => setBackstory(e.target.value)}
                placeholder="例: 元刑事。3年前に妻を不審な事故で亡くし、真相を追っている。"
                rows={4}
              />
            </div>

            <div className={styles.navButtons}>
              <button
                className={styles.nextBtn}
                onClick={() => {
                  if (!name.trim()) {
                    setError('名前を入力してください')
                    return
                  }
                  setError(null)
                  setStep(2)
                }}
              >
                次へ →
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Step 2: ステータスロール</h2>

            <button
              className={styles.rollBtn}
              onClick={() => void handleRoll()}
              disabled={isRolling}
            >
              {isRolling ? 'ロール中...' : 'ダイスを振る'}
            </button>

            <div className={styles.statsGrid}>
              {(
                [
                  ['STR', 'str_'], ['CON', 'con'], ['SIZ', 'siz'],
                  ['INT', 'int_'], ['DEX', 'dex'], ['POW', 'pow_'],
                  ['APP', 'app'], ['EDU', 'edu'], ['LUK', 'luk'],
                ] as [string, keyof BasicStats][]
              ).map(([label, key]) => (
                <div key={key} className={`${styles.statRow} ${isRolling ? styles.rolling : ''}`}>
                  <span className={styles.statLabel}>{label}</span>
                  <button
                    className={styles.adjBtn}
                    onClick={() => adjustStat(key, -5)}
                    disabled={isRolling}
                  >
                    ▼
                  </button>
                  <span className={styles.statVal}>{stats[key]}</span>
                  <button
                    className={styles.adjBtn}
                    onClick={() => adjustStat(key, 5)}
                    disabled={isRolling}
                  >
                    ▲
                  </button>
                </div>
              ))}
            </div>

            <div className={styles.derived}>
              <span>HP: {derived.hp}</span>
              <span>MP: {derived.mp}</span>
              <span>SAN: {derived.san}</span>
            </div>

            <div className={styles.navButtons}>
              <button className={styles.prevBtn} onClick={() => setStep(1)}>
                ← 戻る
              </button>
              <button className={styles.nextBtn} onClick={() => setStep(3)}>
                次へ →
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Step 3: 職業選択</h2>

            <div className={styles.occupationGrid}>
              {occupations.map((occ) => (
                <button
                  key={occ.id}
                  className={`${styles.occBtn} ${selectedOccupation?.id === occ.id ? styles.occBtnSelected : ''}`}
                  onClick={() => setSelectedOccupation(occ)}
                >
                  {occ.name}
                </button>
              ))}
            </div>

            {selectedOccupation && (
              <div className={styles.occDetail}>
                <h3 className={styles.occName}>{selectedOccupation.name}</h3>
                <p className={styles.occDesc}>{selectedOccupation.description}</p>
                <div className={styles.occMeta}>
                  <span>スキルポイント: {selectedOccupation.skill_points_formula} = {occupationPoints}</span>
                  <span>趣味ポイント: INT({stats.int_})×2 = {hobbyPoints}</span>
                </div>
                <div className={styles.occSkills}>
                  <span className={styles.occSkillsLabel}>推奨スキル:</span>
                  {selectedOccupation.typical_skills.map((s) => (
                    <span key={s} className={styles.occSkillTag}>{s}</span>
                  ))}
                </div>
              </div>
            )}

            <div className={styles.navButtons}>
              <button className={styles.prevBtn} onClick={() => setStep(2)}>
                ← 戻る
              </button>
              <button
                className={styles.nextBtn}
                onClick={() => setStep(4)}
              >
                次へ →
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Step 4: スキル割り振り</h2>

            <div className={styles.pointsRemaining}>
              <span className={styles.pointsBadge}>
                職業SP残り: <strong>{remainingOccPoints}</strong>
              </span>
              <span className={styles.pointsBadge}>
                趣味SP残り: <strong>{remainingHobbyPoints}</strong>
              </span>
            </div>

            <div className={styles.skillTable}>
              <div className={styles.skillTableHeader}>
                <span>スキル名</span>
                <span>基本値</span>
                <span>職業SP</span>
                <span>趣味SP</span>
                <span>合計</span>
              </div>
              {Object.entries(STANDARD_SKILLS).map(([skill, base]) => {
                const occ = skillOccPoints[skill] ?? 0
                const hob = skillHobbyPoints[skill] ?? 0
                const total = base + occ + hob
                const isRecommended = selectedOccupation?.typical_skills.includes(skill)

                return (
                  <div
                    key={skill}
                    className={`${styles.skillRow} ${isRecommended ? styles.skillRowRecommended : ''}`}
                  >
                    <span className={styles.skillName}>
                      {skill}
                      {isRecommended && <span className={styles.recBadge}>推</span>}
                    </span>
                    <span className={styles.skillBase}>{base}</span>
                    <div className={styles.skillAdj}>
                      <button
                        className={styles.skillAdjBtn}
                        onClick={() => addSkillOccPoints(skill, -5)}
                      >
                        -
                      </button>
                      <span className={styles.skillPts}>{occ}</span>
                      <button
                        className={styles.skillAdjBtn}
                        onClick={() => addSkillOccPoints(skill, 5)}
                      >
                        +
                      </button>
                    </div>
                    <div className={styles.skillAdj}>
                      <button
                        className={styles.skillAdjBtn}
                        onClick={() => addSkillHobbyPoints(skill, -5)}
                      >
                        -
                      </button>
                      <span className={styles.skillPts}>{hob}</span>
                      <button
                        className={styles.skillAdjBtn}
                        onClick={() => addSkillHobbyPoints(skill, 5)}
                      >
                        +
                      </button>
                    </div>
                    <span className={`${styles.skillTotal} ${total >= 90 ? styles.skillTotalHigh : ''}`}>
                      {total}
                    </span>
                  </div>
                )
              })}
            </div>

            <div className={styles.navButtons}>
              <button className={styles.prevBtn} onClick={() => setStep(3)}>
                ← 戻る
              </button>
              <button
                className={styles.saveBtn}
                onClick={() => void handleSave()}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存して完成'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
