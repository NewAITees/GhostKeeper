/**
 * CharacterSheet.tsx
 * キャラクター名 + HP/SAN/MP バー表示コンポーネント
 *
 * 使い方:
 *   <CharacterSheet character={pc} />
 *
 * StatBar コンポーネントを使用してパラメータバーを表示する。
 */

import type { CharacterSummary } from '../../types'
import StatBar from '../common/StatBar'
import styles from './CharacterSheet.module.css'

interface Props {
  character: CharacterSummary
}

export default function CharacterSheet({ character }: Props) {
  return (
    <div className={styles.sheet}>
      <h3 className={styles.name}>{character.name}</h3>
      <div className={styles.stats}>
        <StatBar
          label="HP"
          current={character.hp_current}
          max={character.hp_max}
          color="var(--hp-color)"
        />
        <StatBar
          label="SAN"
          current={character.san_current}
          max={character.san_max}
          color="var(--san-color)"
        />
        <StatBar
          label="MP"
          current={character.mp_current}
          max={character.mp_max}
          color="var(--mp-color)"
        />
      </div>
    </div>
  )
}
