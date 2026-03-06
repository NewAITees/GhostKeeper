/**
 * CharacterPortrait.tsx
 * キャラクター立ち絵 / シーン背景表示コンポーネント
 *
 * 使い方:
 *   <CharacterPortrait imageRef={currentImage} />
 *
 * - type === 'character': /images/characters/{id}/{expression}.png を表示
 * - type === 'scene': /images/scenes/{id}.png を表示
 * - imageRef が null の場合はプレースホルダーを表示
 * - 表情切り替え時はフェードトランジション (CSS opacity 0.3s)
 * - 画像が存在しない場合 (404) は onError でプレースホルダーに切り替え
 */

import { useState, useRef, useEffect } from 'react'
import type { ImageRef } from '../../types'
import { api } from '../../api/client'
import styles from './CharacterPortrait.module.css'

interface Props {
  imageRef: ImageRef | null
}

function buildImageUrl(imageRef: ImageRef): string {
  if (imageRef.type === 'character') {
    return api.imageUrl(`characters/${imageRef.id}/${imageRef.expression}.png`)
  }
  return api.imageUrl(`scenes/${imageRef.id}.png`)
}

export default function CharacterPortrait({ imageRef }: Props) {
  const [displayRef, setDisplayRef] = useState<ImageRef | null>(imageRef)
  const [opacity, setOpacity] = useState(1)
  const [hasError, setHasError] = useState(false)
  const prevRefKey = useRef<string | null>(null)

  // imageRef が変わったときにフェードアウト → src切り替え → フェードイン
  const refKey = imageRef ? `${imageRef.type}/${imageRef.id}/${imageRef.expression}` : null

  useEffect(() => {
    if (refKey === prevRefKey.current) return
    prevRefKey.current = refKey

    // フェードアウト
    const el = document.getElementById('portrait-img-wrapper')
    if (el) el.style.opacity = '0'

    const timer = setTimeout(() => {
      setDisplayRef(imageRef)
      setHasError(false)
      setOpacity(1)
    }, 180)

    return () => clearTimeout(timer)
  }, [refKey, imageRef])

  if (!displayRef || hasError) {
    return (
      <div className={styles.placeholder}>
        <div className={styles.silhouette} />
        <p className={styles.placeholderText}>—</p>
      </div>
    )
  }

  const src = buildImageUrl(displayRef)
  const isScene = displayRef.type === 'scene'

  return (
    <div
      id="portrait-img-wrapper"
      className={`${styles.portrait} ${isScene ? styles.scene : ''}`}
      style={{ opacity, transition: 'opacity 0.3s ease' }}
    >
      <img
        src={src}
        alt={`${displayRef.id} - ${displayRef.expression}`}
        className={isScene ? styles.sceneImg : styles.characterImg}
        onError={() => setHasError(true)}
      />
    </div>
  )
}
