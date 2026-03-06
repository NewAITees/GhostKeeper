/**
 * GameScreen.tsx
 * ゲーム画面全体レイアウトを管理するコンポーネント
 *
 * 使い方:
 *   <GameScreen sessionId="abc123" onBack={() => setView('sessionList')} />
 *
 * レイアウト (CSS Grid):
 *   - header:  セッション名 + 戻るボタン
 *   - chat:    チャットエリア（スクロール）
 *   - sidebar: NAVパネル（現在地・NPC一覧）+ 立ち絵 + キャラクターシート
 *   - choices: 選択肢ボタン群
 *   - input:   テキスト入力 + 送信
 */

import { useGame } from '../../hooks/useGame'
import ChatArea from './ChatArea'
import ChatInput from './ChatInput'
import ChoiceButtons from './ChoiceButtons'
import CharacterPortrait from './CharacterPortrait'
import CharacterSheet from './CharacterSheet'
import styles from './GameScreen.module.css'

interface Props {
  sessionId: string
  onBack: () => void
}

export default function GameScreen({ sessionId, onBack }: Props) {
  const {
    session,
    pc,
    npcs,
    displayMessages,
    choices,
    currentImage,
    isSending,
    sendMessage,
  } = useGame(sessionId)

  const currentLocation = (session as { current_location?: string | null } | null)?.current_location

  return (
    <div className={styles.layout}>
      {/* ヘッダー */}
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>
          ← 一覧に戻る
        </button>
        <h1 className={styles.sessionName}>
          {session ? session.name : '読み込み中...'}
        </h1>
      </header>

      {/* チャットエリア */}
      <main className={styles.chat}>
        <ChatArea messages={displayMessages} isSending={isSending} />
      </main>

      {/* サイドパネル: NAVパネル + 立ち絵 + キャラシート */}
      <aside className={styles.sidebar}>
        {/* NAVパネル: 現在地・NPC一覧 */}
        <div className={styles.navPanel}>
          <div className={styles.navLocation}>
            <span className={styles.navLabel}>現在地</span>
            <span className={styles.navValue}>
              {currentLocation ?? '—'}
            </span>
          </div>

          {npcs.length > 0 && (
            <div className={styles.navNpcs}>
              <span className={styles.navLabel}>NPC</span>
              <div className={styles.npcList}>
                {npcs.map((npc) => (
                  <div key={npc.id} className={styles.npcItem}>
                    <span className={styles.npcIcon}>
                      {npc.hp_current <= 0 ? '💀' : '👤'}
                    </span>
                    <span className={styles.npcName}>{npc.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className={styles.portraitArea}>
          <CharacterPortrait imageRef={currentImage} />
        </div>
        {pc && (
          <CharacterSheet character={pc} />
        )}
      </aside>

      {/* 選択肢ボタン */}
      <div className={styles.choices}>
        <ChoiceButtons
          choices={choices}
          onChoose={sendMessage}
          disabled={isSending}
        />
      </div>

      {/* テキスト入力 */}
      <div className={styles.input}>
        <ChatInput onSend={sendMessage} disabled={isSending} />
      </div>
    </div>
  )
}
