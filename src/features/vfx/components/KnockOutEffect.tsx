'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface KnockOutEffectProps {
  /** エフェクト表示トリガー */
  isActive: boolean;
  /** 勝者の属性 */
  winnerElement: KaijuElement;
  /** 演出完了コールバック */
  onComplete: () => void;
}

/** ひび割れ線の1本分のデータ */
interface CrackLine {
  points: string;
}

/** ひび割れ線をマウント時に一度だけ生成する */
function generateCrackLines(): CrackLine[] {
  const lines: CrackLine[] = [];
  const cx = 50;
  const cy = 50;

  for (let i = 0; i < 12; i++) {
    const baseAngle = (i / 12) * Math.PI * 2 + (Math.random() * 0.3 - 0.15);
    const pointList: [number, number][] = [[cx, cy]];

    for (let seg = 0; seg < 3; seg++) {
      const prevX = pointList[pointList.length - 1][0];
      const prevY = pointList[pointList.length - 1][1];
      const distance = (seg + 1) * 20 + Math.random() * 10;
      const deviation = Math.random() * 16 - 8;
      const angle = baseAngle + deviation * 0.02;
      const x = prevX + Math.cos(angle) * (distance - seg * 15);
      const y = prevY + Math.sin(angle) * (distance - seg * 15);
      pointList.push([x, y]);
    }

    lines.push({
      points: pointList.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' '),
    });
  }

  return lines;
}

/**
 * KO時の劇的な演出コンポーネント
 * 3500ms で白フラッシュ → ひび割れ → K.O.テキスト → フェードアウト の順に演出する
 */
export function KnockOutEffect({ isActive, winnerElement, onComplete }: KnockOutEffectProps) {
  const style = ELEMENT_STYLES[winnerElement];
  const onCompleteRef = useRef(onComplete);

  // レンダー外 (useLayoutEffect) で ref を最新に保つ
  useLayoutEffect(() => {
    onCompleteRef.current = onComplete;
  });

  // ひび割れ線はマウント時に一度だけ生成（useState の lazy initializer を使用）
  const [crackLines] = useState<CrackLine[]>(() => generateCrackLines());

  // 3500ms 後に onComplete を呼ぶ
  useEffect(() => {
    if (!isActive) return;

    const timer = setTimeout(() => {
      onCompleteRef.current();
    }, 3500);

    return () => clearTimeout(timer);
  }, [isActive]);

  return (
    <>
      {/* prefers-reduced-motion 対応 */}
      <style>{`
        @media (prefers-reduced-motion: reduce) {
          .knockout-effect-layer {
            display: none !important;
          }
        }
      `}</style>

      <AnimatePresence>
        {isActive && (
          <motion.div
            key={`knockout-${winnerElement}`}
            className="knockout-effect-layer"
            aria-hidden="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 55,
              pointerEvents: 'none',
              overflow: 'hidden',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.5 } }}
          >
            {/* Phase 1: 白フラッシュ → 暗転 (0-500ms) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0.8, 0.3] }}
              transition={{ duration: 0.5, times: [0, 0.3, 1], ease: 'easeOut' }}
              style={{
                position: 'absolute',
                inset: 0,
                background:
                  'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.9) 100%)',
                backgroundColor: 'rgba(0,0,0,0.85)',
              }}
            />

            {/* 白フラッシュ層 */}
            <motion.div
              initial={{ opacity: 0.9 }}
              animate={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              style={{
                position: 'absolute',
                inset: 0,
                backgroundColor: '#ffffff',
              }}
            />

            {/* Phase 2: ひび割れ線 SVG (500-1200ms) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0, 1, 1] }}
              transition={{ duration: 1.2, times: [0, 0.4, 0.6, 1] }}
              style={{
                position: 'absolute',
                inset: 0,
              }}
            >
              <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
              >
                <defs>
                  <filter id="crack-glow">
                    <feGaussianBlur stdDeviation="0.8" result="blur" />
                    <feFlood floodColor={style.primary} floodOpacity="0.7" result="color" />
                    <feComposite in="color" in2="blur" operator="in" result="glow" />
                    <feMerge>
                      <feMergeNode in="glow" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {crackLines.map((line, i) => (
                  <motion.polyline
                    key={i}
                    points={line.points}
                    stroke="white"
                    strokeWidth="0.8"
                    fill="none"
                    filter="url(#crack-glow)"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{
                      duration: 0.4,
                      delay: 0.5 + i * 0.05,
                      ease: 'easeOut',
                    }}
                  />
                ))}
              </svg>
            </motion.div>

            {/* Phase 3: K.O. テキスト (1200-3000ms) */}
            <motion.div
              initial={{ opacity: 0, scale: 8 }}
              animate={{ opacity: [0, 0, 1, 1, 1], scale: [8, 8, 1.2, 1, 1] }}
              transition={{
                duration: 3.0,
                times: [0, 0.38, 0.5, 0.6, 1],
                ease: 'easeOut',
              }}
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '1rem',
              }}
            >
              {/* K.O. メインテキスト */}
              <div
                style={{
                  fontSize: 'clamp(8rem, 20vw, 16rem)',
                  fontWeight: 900,
                  color: '#ffffff',
                  lineHeight: 1,
                  letterSpacing: '-0.02em',
                  textShadow: [
                    '0 0 60px rgba(239,68,68,0.9)',
                    '0 0 120px rgba(239,68,68,0.5)',
                    '0 4px 0 #991b1b',
                  ].join(', '),
                  WebkitTextStroke: '3px rgba(255,255,255,0.3)',
                  fontFamily: 'inherit',
                  userSelect: 'none',
                }}
              >
                K.O.
              </div>

              {/* KNOCK OUT サブテキスト */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: [0, 0, 1], y: [20, 20, 0] }}
                transition={{
                  duration: 3.0,
                  times: [0, 0.55, 0.7],
                  ease: 'easeOut',
                }}
                style={{
                  fontSize: '1.5rem',
                  fontWeight: 700,
                  color: '#f87171',
                  letterSpacing: '0.5em',
                  textTransform: 'uppercase',
                  fontFamily: 'inherit',
                  userSelect: 'none',
                }}
              >
                KNOCK OUT
              </motion.div>
            </motion.div>

            {/* Phase 4: 全体フェードアウト (3000-3500ms) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0, 0, 0, 1] }}
              transition={{
                duration: 3.5,
                times: [0, 0.7, 0.8, 0.85, 1],
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
