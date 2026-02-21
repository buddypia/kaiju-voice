'use client';

import { useEffect, useRef, useLayoutEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface UltimateCutInProps {
  /** 演出表示トリガー */
  isActive: boolean;
  /** 怪獣の日本語名 */
  kaijuName: string;
  /** 必殺技名 */
  attackName: string;
  /** 攻撃属性 */
  element: KaijuElement;
  /** 怪獣画像URL */
  kaijuImageUrl: string | null;
  /** どちら側のプレイヤーか */
  side: 'left' | 'right';
  /** 演出完了コールバック */
  onComplete: () => void;
}

/**
 * 必殺技カットイン演出コンポーネント
 * 格闘ゲーム風の劇的なカットインを 2500ms で演出する
 */
export function UltimateCutIn({
  isActive,
  kaijuName,
  attackName,
  element,
  kaijuImageUrl,
  side,
  onComplete,
}: UltimateCutInProps) {
  const style = ELEMENT_STYLES[element];
  const onCompleteRef = useRef(onComplete);

  // レンダー外 (useLayoutEffect) で ref を最新に保つ
  useLayoutEffect(() => {
    onCompleteRef.current = onComplete;
  });

  // 2500ms 後に onComplete を呼ぶ
  useEffect(() => {
    if (!isActive) return;

    const timer = setTimeout(() => {
      onCompleteRef.current();
    }, 2500);

    return () => clearTimeout(timer);
  }, [isActive]);

  // 斜め線の始点・終点 (side により向きを変える)
  const lineCoords =
    side === 'left'
      ? { x1: '0%', y1: '0%', x2: '100%', y2: '100%' }
      : { x1: '100%', y1: '0%', x2: '0%', y2: '100%' };

  return (
    <>
      {/* prefers-reduced-motion 対応 */}
      <style>{`
        @media (prefers-reduced-motion: reduce) {
          .ultimate-cut-in-layer {
            display: none !important;
          }
        }
      `}</style>

      <AnimatePresence>
        {isActive && (
          <motion.div
            key={`ultimate-cut-in-${element}`}
            className="ultimate-cut-in-layer"
            aria-hidden="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 60,
              pointerEvents: 'none',
              overflow: 'hidden',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Phase 1: 背景オーバーレイ (0-300ms) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 1] }}
              transition={{ duration: 0.3, times: [0, 0.5, 1] }}
              style={{
                position: 'absolute',
                inset: 0,
                background: `radial-gradient(ellipse at center, ${style.glow.replace('0.4', '0.3')} 0%, rgba(0,0,0,0.85) 70%)`,
              }}
            />

            {/* Phase 1: 斜め光の線 SVG (0-300ms) */}
            <motion.div
              initial={{ opacity: 0, scaleX: 0 }}
              animate={{ opacity: [0, 1, 1, 0], scaleX: [0, 1, 1, 1] }}
              transition={{ duration: 0.6, times: [0, 0.25, 0.75, 1], delay: 0 }}
              style={{
                position: 'absolute',
                inset: 0,
                transformOrigin: side === 'left' ? 'left center' : 'right center',
              }}
            >
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{ position: 'absolute', inset: 0 }}
              >
                <defs>
                  <filter id="glow-line">
                    <feGaussianBlur stdDeviation="1.5" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>
                {/* 太い光の線 */}
                <line
                  {...lineCoords}
                  stroke={style.primary}
                  strokeWidth="6"
                  strokeOpacity="0.9"
                  filter="url(#glow-line)"
                />
                {/* 細い中心線 */}
                <line {...lineCoords} stroke="#ffffff" strokeWidth="2" strokeOpacity="0.8" />
                {/* 並行する補助線1 */}
                {side === 'left' ? (
                  <line
                    x1="0%"
                    y1="10%"
                    x2="90%"
                    y2="100%"
                    stroke={style.primary}
                    strokeWidth="3"
                    strokeOpacity="0.4"
                    filter="url(#glow-line)"
                  />
                ) : (
                  <line
                    x1="100%"
                    y1="10%"
                    x2="10%"
                    y2="100%"
                    stroke={style.primary}
                    strokeWidth="3"
                    strokeOpacity="0.4"
                    filter="url(#glow-line)"
                  />
                )}
              </svg>
            </motion.div>

            {/* Phase 2: 怪獣名 (200-1000ms) */}
            <motion.div
              initial={{ opacity: 0, scale: 0, y: -40 }}
              animate={{ opacity: [0, 1, 1], scale: [0, 1.2, 1], y: [-40, 0, 0] }}
              transition={{
                duration: 0.8,
                delay: 0.2,
                times: [0, 0.5, 1],
                ease: 'easeOut',
              }}
              style={{
                position: 'absolute',
                top: '15%',
                left: 0,
                right: 0,
                textAlign: 'center',
              }}
            >
              {kaijuImageUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={kaijuImageUrl}
                  alt={kaijuName}
                  style={{
                    display: 'inline-block',
                    height: '6rem',
                    width: 'auto',
                    objectFit: 'contain',
                    marginBottom: '0.5rem',
                    filter: `drop-shadow(0 0 12px ${style.primary})`,
                  }}
                />
              )}
              <div
                style={{
                  fontSize: '1.875rem',
                  fontWeight: 900,
                  color: style.primary,
                  letterSpacing: '0.1em',
                  textShadow: `0 0 20px ${style.glow}, 0 0 40px ${style.glow}`,
                  WebkitTextStroke: `1px ${style.primary}`,
                  fontFamily: 'inherit',
                }}
              >
                {kaijuName}
              </div>
            </motion.div>

            {/* Phase 3: 攻撃名 (800-2000ms) */}
            <motion.div
              initial={{ opacity: 0, scale: 5 }}
              animate={{ opacity: [0, 1, 1, 0], scale: [5, 1, 1, 1] }}
              transition={{
                duration: 1.2,
                delay: 0.8,
                times: [0, 0.25, 0.75, 1],
                ease: 'easeOut',
              }}
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div
                style={{
                  fontSize: 'clamp(4rem, 12vw, 8rem)',
                  fontWeight: 900,
                  color: '#ffffff',
                  letterSpacing: '0.05em',
                  textAlign: 'center',
                  lineHeight: 1,
                  textShadow: [
                    `0 0 30px ${style.primary}`,
                    `0 0 60px ${style.glow}`,
                    `0 0 100px ${style.glow}`,
                    `0 4px 0 rgba(0,0,0,0.8)`,
                  ].join(', '),
                  WebkitTextStroke: `2px ${style.primary}`,
                  fontFamily: 'inherit',
                  padding: '0 1rem',
                  wordBreak: 'keep-all',
                }}
              >
                {attackName}
              </div>
            </motion.div>

            {/* Phase 4: 全体フェードアウト (2000-2500ms) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0, 0, 0, 1] }}
              transition={{
                duration: 2.5,
                times: [0, 0.6, 0.75, 0.8, 1],
                ease: 'easeIn',
              }}
              style={{
                position: 'absolute',
                inset: 0,
                backgroundColor: 'rgba(0,0,0,1)',
                pointerEvents: 'none',
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
