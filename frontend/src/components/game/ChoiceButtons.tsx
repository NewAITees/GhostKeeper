/**
 * ChoiceButtons.tsx
 * AI提案の行動選択肢ボタン群
 *
 * 使い方:
 *   <ChoiceButtons
 *     choices={['書架を調べる', '出口へ向かう']}
 *     onChoose={(choice) => sendMessage(choice)}
 *     disabled={isSending}
 *   />
 *
 * - disabled=true の時はグレーアウト（送信中）
 * - 選択後、そのテキストを onChoose に渡す
 */

import styles from './ChoiceButtons.module.css'

interface Props {
  choices: string[]
  onChoose: (choice: string) => void
  disabled: boolean
}

export default function ChoiceButtons({ choices, onChoose, disabled }: Props) {
  if (choices.length === 0) return null

  return (
    <div className={styles.container}>
      {choices.map((choice, i) => (
        <button
          key={i}
          className={styles.choiceBtn}
          onClick={() => onChoose(choice)}
          disabled={disabled}
        >
          {choice}
        </button>
      ))}
    </div>
  )
}
