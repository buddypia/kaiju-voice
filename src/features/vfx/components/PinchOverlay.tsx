'use client';

import { AnimatePresence, motion } from 'framer-motion';
import type { Player } from '@/features/battle/types/battle';

interface PinchOverlayProps {
  players: [Player, Player];
}

const PINCH_THRESHOLD = 0.25;

/** HP比率を計算する */
function hpRatio(player: Player): number {
  return player.hp / player.maxHp;
}

/** ピンチ状態かどうか (HP > 0 かつ 25%以下) */
function isPinch(player: Player): boolean {
  return player.hp > 0 && hpRatio(player) <= PINCH_THRESHOLD;
}

/**
 * HP低下時のピンチ演出オーバーレイ。
 * HPがmaxHpの25%以下のプレイヤーがいる場合に赤いビネットと鼓動エフェクトを表示する。
 */
export function PinchOverlay({ players }: PinchOverlayProps) {
  const p1Pinch = isPinch(players[0]);
  const p2Pinch = isPinch(players[1]);
  const anyPinch = p1Pinch || p2Pinch;

  // prefers-reduced-motion 対応: 静的な薄い赤ビネットのみ表示
  const prefersReducedMotion =
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false;

  return (
    <AnimatePresence>
      {anyPinch && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 15,
            pointerEvents: 'none',
          }}
          aria-hidden="true"
        >
          {/* P1（左）ピンチ: 左端ビネット */}
          {p1Pinch && <LeftVignette reducedMotion={prefersReducedMotion} />}

          {/* P2（右）ピンチ: 右端ビネット */}
          {p2Pinch && <RightVignette reducedMotion={prefersReducedMotion} />}
        </div>
      )}
    </AnimatePresence>
  );
}

/** 左端の赤いビネット + 鼓動エフェクト */
function LeftVignette({ reducedMotion }: { reducedMotion: boolean }) {
  if (reducedMotion) {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          bottom: 0,
          width: '25%',
          background: 'linear-gradient(to right, rgba(239,68,68,0.3), transparent 40%)',
          borderLeft: '3px solid rgba(239, 68, 68, 0.6)',
        }}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0.3, 0.7, 0.3],
        scale: [1, 1.003, 1, 1.005, 1],
        scaleX: [1, 1.003, 1, 1.005, 1],
      }}
      transition={{
        opacity: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
        scale: {
          duration: 0.8,
          repeat: Infinity,
          times: [0, 0.15, 0.3, 0.45, 1],
          ease: 'easeInOut',
        },
      }}
      exit={{ opacity: 0 }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        bottom: 0,
        width: '25%',
        background: 'linear-gradient(to right, rgba(239,68,68,1), transparent 40%)',
        borderLeft: '3px solid rgba(239, 68, 68, 0.6)',
        transformOrigin: 'left center',
      }}
    />
  );
}

/** 右端の赤いビネット + 鼓動エフェクト */
function RightVignette({ reducedMotion }: { reducedMotion: boolean }) {
  if (reducedMotion) {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          bottom: 0,
          width: '25%',
          background: 'linear-gradient(to left, rgba(239,68,68,0.3), transparent 40%)',
          borderRight: '3px solid rgba(239, 68, 68, 0.6)',
        }}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0.3, 0.7, 0.3],
        scale: [1, 1.003, 1, 1.005, 1],
        scaleX: [1, 1.003, 1, 1.005, 1],
      }}
      transition={{
        opacity: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
        scale: {
          duration: 0.8,
          repeat: Infinity,
          times: [0, 0.15, 0.3, 0.45, 1],
          ease: 'easeInOut',
        },
      }}
      exit={{ opacity: 0 }}
      style={{
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        width: '25%',
        background: 'linear-gradient(to left, rgba(239,68,68,1), transparent 40%)',
        borderRight: '3px solid rgba(239, 68, 68, 0.6)',
        transformOrigin: 'right center',
      }}
    />
  );
}
