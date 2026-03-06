/**
 * App.tsx
 * アプリケーションルート - 画面切り替え（ルーターなし）
 *
 * ビュー:
 *   - sessionList:      セッション一覧ホーム画面
 *   - characterManager: キャラクター管理画面
 *   - characterCreator: キャラクター作成ウィザード
 *   - game:             ゲーム画面（sessionId を保持）
 */

import { useState } from 'react'
import SessionList from './components/session/SessionList'
import GameScreen from './components/game/GameScreen'
import CharacterManager from './components/character/CharacterManager'
import CharacterCreator from './components/character/CharacterCreator'

type View =
  | { screen: 'sessionList' }
  | { screen: 'characterManager' }
  | { screen: 'characterCreator' }
  | { screen: 'game'; sessionId: string }

export default function App() {
  const [view, setView] = useState<View>({ screen: 'sessionList' })

  if (view.screen === 'game') {
    return (
      <GameScreen
        sessionId={view.sessionId}
        onBack={() => setView({ screen: 'sessionList' })}
      />
    )
  }

  if (view.screen === 'characterManager') {
    return (
      <CharacterManager
        onBack={() => setView({ screen: 'sessionList' })}
        onCreateNew={() => setView({ screen: 'characterCreator' })}
      />
    )
  }

  if (view.screen === 'characterCreator') {
    return (
      <CharacterCreator
        onBack={() => setView({ screen: 'characterManager' })}
        onCreated={() => setView({ screen: 'characterManager' })}
      />
    )
  }

  return (
    <SessionList
      onEnterSession={(id) => setView({ screen: 'game', sessionId: id })}
      onGoToCharacterManager={() => setView({ screen: 'characterManager' })}
    />
  )
}
