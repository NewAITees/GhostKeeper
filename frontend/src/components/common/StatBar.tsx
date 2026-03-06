/**
 * StatBar.tsx
 * HP/SAN/MP 共通バーコンポーネント
 *
 * 使い方:
 *   <StatBar label="HP" current={6} max={10} color="var(--hp-color)" />
 *
 * 残量が30%未満になると点滅アニメーションが有効になる。
 */

import styles from './StatBar.module.css'

interface Props {
  label: string
  current: number
  max: number
  color: string  // CSS変数名 or hex
}

export default function StatBar({ label, current, max, color }: Props) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (current / max) * 100)) : 0
  const isDanger = pct < 30

  return (
    <div className={styles.statBar}>
      <div className={styles.labelRow}>
        <span className={styles.label}>{label}</span>
        <span className={styles.values}>
          {current} / {max}
        </span>
      </div>
      <div className={styles.track}>
        <div
          className={`${styles.fill} ${isDanger ? styles.danger : ''}`}
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}
