'use client';

import { AnimatePresence, motion } from 'framer-motion';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface ImpactFlashProps {
  /** フラッシュ色（攻撃属性） */
  element: KaijuElement;
  /** フラッシュトリガー */
  isActive: boolean;
  /** クリティカル時は強いフラッシュ */
  isCritical?: boolean;
}

/**
 * ダメージ時の全画面フラッシュエフェクト
 * framer-motion の AnimatePresence でマウント/アンマウントを管理
 */
export function ImpactFlash({ element, isActive, isCritical = false }: ImpactFlashProps) {
  const style = ELEMENT_STYLES[element];

  return (
    <>
      {/* prefers-reduced-motion 対応: style タグで上書き */}
      <style>{`
        @media (prefers-reduced-motion: reduce) {
          .impact-flash-layer {
            display: none !important;
          }
        }
      `}</style>

      <AnimatePresence>
        {isActive && (
          <>
            {/* 属性カラーフラッシュ */}
            <motion.div
              key={`flash-${element}-${isCritical ? 'crit' : 'normal'}`}
              className="impact-flash-layer"
              initial={{ opacity: isCritical ? 0.35 : 0.15 }}
              animate={{ opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{
                duration: isCritical ? 0.5 : 0.3,
                ease: 'easeOut',
              }}
              style={{
                position: 'fixed',
                inset: 0,
                zIndex: 50,
                pointerEvents: 'none',
                backgroundColor: style.primary,
              }}
              aria-hidden="true"
            />

            {/* クリティカル時の追加白フラッシュ */}
            {isCritical && (
              <motion.div
                key="flash-white-critical"
                className="impact-flash-layer"
                initial={{ opacity: 0.6 }}
                animate={{ opacity: 0 }}
                exit={{ opacity: 0 }}
                transition={{
                  duration: 0.2,
                  ease: 'easeOut',
                }}
                style={{
                  position: 'fixed',
                  inset: 0,
                  zIndex: 51,
                  pointerEvents: 'none',
                  backgroundColor: '#ffffff',
                }}
                aria-hidden="true"
              />
            )}
          </>
        )}
      </AnimatePresence>
    </>
  );
}
