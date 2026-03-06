/**
 * ChatArea.tsx
 * スクロール可能なチャット履歴表示エリア
 *
 * 使い方:
 *   <ChatArea messages={displayMessages} isSending={isSending} />
 *
 * - メッセージが追加された際、最下部へ自動スクロール
 * - isSending=true の間は「GMが考えています...」インジケーターを表示
 */

import { useEffect, useRef } from 'react'
import type { DisplayMessage } from '../../types'
import ChatMessage from './ChatMessage'
import styles from './ChatArea.module.css'

interface Props {
  messages: DisplayMessage[]
  isSending: boolean
}

export default function ChatArea({ messages, isSending }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  return (
    <div className={styles.area}>
      {messages.length === 0 && !isSending && (
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            行動を入力するか、選択肢を選んでください
          </p>
        </div>
      )}

      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} />
      ))}

      {isSending && (
        <div className={styles.thinkingRow}>
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingText}>GMが考えています...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
