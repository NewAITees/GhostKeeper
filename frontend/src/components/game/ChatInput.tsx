/**
 * ChatInput.tsx
 * チャット入力欄 + 送信ボタンコンポーネント
 *
 * 使い方:
 *   <ChatInput onSend={(msg) => sendMessage(msg)} disabled={isSending} />
 *
 * - textarea + Enter で送信（Shift+Enter は改行）
 * - disabled=true 時は入力欄グレーアウト + ボタン無効化
 * - 送信後はテキストクリア
 */

import { useState, useRef } from 'react'
import styles from './ChatInput.module.css'

interface Props {
  onSend: (message: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    textareaRef.current?.focus()
  }

  return (
    <div className={styles.container}>
      <textarea
        ref={textareaRef}
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="行動を入力... (Enter で送信、Shift+Enter で改行)"
        disabled={disabled}
        rows={2}
      />
      <button
        className={styles.sendBtn}
        onClick={handleSend}
        disabled={disabled || !text.trim()}
      >
        送信
      </button>
    </div>
  )
}
