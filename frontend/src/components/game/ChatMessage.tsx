/**
 * ChatMessage.tsx
 * チャットエリア内の個別メッセージコンポーネント
 *
 * 使い方:
 *   <ChatMessage message={displayMessage} />
 *
 * type に応じた表示スタイル:
 *   gm     - 🕯️ GMバッジ + 斜体テキスト（クリーム色）
 *   npc    - キャラ名バッジ（紫）+ セリフ
 *   player - 右寄せ + 「あなた」バッジ（暗いグレー）
 *   dice   - 🎲 アイコン + ダイス記法 + 結果数値 + 判定結果
 *   system - 中央揃え + 薄いテキスト（区切り線風）
 */

import type { DisplayMessage } from '../../types'
import styles from './ChatMessage.module.css'

interface Props {
  message: DisplayMessage
}

function DiceResultBadge({ result }: { result: string }) {
  const lower = result.toLowerCase()
  let className = styles.diceResultNormal
  if (lower.includes('クリティカル') || lower.includes('イクストリーム')) {
    className = styles.diceResultCritical
  } else if (lower.includes('ハード')) {
    className = styles.diceResultHard
  } else if (lower.includes('ファンブル') || lower.includes('失敗')) {
    className = styles.diceResultFail
  } else if (lower.includes('成功')) {
    className = styles.diceResultSuccess
  }
  return <span className={className}>{result}</span>
}

export default function ChatMessage({ message }: Props) {
  switch (message.type) {
    case 'gm':
      return (
        <div className={styles.gmMessage}>
          <span className={styles.gmBadge}>🕯️ GM</span>
          <p className={styles.gmText}>{message.content}</p>
        </div>
      )

    case 'npc':
      return (
        <div className={styles.npcMessage}>
          <span className={styles.npcBadge}>{message.characterName ?? 'NPC'}</span>
          <p className={styles.npcText}>「{message.content}」</p>
        </div>
      )

    case 'player':
      return (
        <div className={styles.playerMessage}>
          <div className={styles.playerInner}>
            <span className={styles.playerBadge}>あなた</span>
            <p className={styles.playerText}>{message.content}</p>
          </div>
        </div>
      )

    case 'dice':
      return (
        <div className={styles.diceMessage}>
          <span className={styles.diceIcon}>🎲</span>
          <div className={styles.diceContent}>
            {message.content && (
              <span className={styles.diceDetail}>{message.content}</span>
            )}
            {message.diceNotation && (
              <span className={styles.diceNotation}>{message.diceNotation}</span>
            )}
            {message.diceResult !== undefined && (
              <span className={styles.diceResult}>= {message.diceResult}</span>
            )}
            {message.skillValue !== undefined && (
              <span className={styles.diceSkillVal}>技能値: {message.skillValue}</span>
            )}
            {message.resultJa ? (
              <DiceResultBadge result={message.resultJa} />
            ) : message.skillResult ? (
              <DiceResultBadge result={message.skillResult} />
            ) : null}
          </div>
        </div>
      )

    case 'system':
      return (
        <div className={styles.systemMessage}>
          <span className={styles.systemText}>{message.content}</span>
        </div>
      )

    default:
      return null
  }
}
