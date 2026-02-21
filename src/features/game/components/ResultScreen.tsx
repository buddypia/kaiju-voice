'use client';

import Image from 'next/image';
import { motion } from 'framer-motion';
import { Crown } from 'lucide-react';
import type { Player, BattleLogEntry } from '@/features/battle/types/battle';
import { MESSAGES } from '@/shared/constants/messages';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';
import { VictoryCelebration } from '@/features/vfx';

interface ResultScreenProps {
  winner: Player;
  loser: Player;
  battleLog: BattleLogEntry[];
  onPlayAgain: () => void;
  onBackToTitle: () => void;
}

/** 結果画面コンポーネント */
export function ResultScreen({
  winner,
  loser,
  battleLog,
  onPlayAgain,
  onBackToTitle,
}: ResultScreenProps) {
  const winnerColor = ELEMENT_STYLES[winner.kaiju.element];

  /** バトルサマリーの計算 */
  const totalRounds = battleLog.length > 0 ? Math.max(...battleLog.map((e) => e.round)) : 0;
  const maxDamageEntry = battleLog.reduce<BattleLogEntry | null>((max, entry) => {
    if (!max || entry.attack.damage > max.attack.damage) return entry;
    return max;
  }, null);
  const maxDamage = maxDamageEntry?.attack.damage ?? 0;
  const mvpAttackName = maxDamageEntry?.attack.attackName ?? '-';

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center py-12 px-6 overflow-hidden bg-background">
      {/* 勝利コンフェティエフェクト */}
      <VictoryCelebration isActive={true} winnerElement={winner.kaiju.element} />

      {/* 勝利グローエフェクト背景 */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] opacity-30"
          style={{
            background: `radial-gradient(ellipse, ${winnerColor.primary} 0%, transparent 70%)`,
            filter: 'blur(60px)',
          }}
        />
        <div
          className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-64 opacity-20"
          style={{
            background: 'radial-gradient(ellipse, #fbbf24 0%, transparent 70%)',
            filter: 'blur(50px)',
          }}
        />
      </div>

      <div className="relative z-10 w-full max-w-3xl flex flex-col items-center gap-8">
        {/* 勝者表示 */}
        <div className="flex flex-col items-center gap-4">
          {/* 怪獣画像または属性アイコン */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="w-48 h-48 rounded-full flex items-center justify-center text-8xl animate-winner-glow"
            style={
              {
                background: `radial-gradient(circle, ${winnerColor.primary}30 0%, transparent 70%)`,
                border: `3px solid ${winnerColor.primary}`,
                '--glow-color': winnerColor.glow,
              } as React.CSSProperties
            }
          >
            {winner.kaiju.imageUrl ? (
              <Image
                src={winner.kaiju.imageUrl}
                alt={winner.kaiju.nameJa}
                width={192}
                height={192}
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <Crown size={80} strokeWidth={1} className="text-amber-400" aria-hidden="true" />
            )}
          </motion.div>

          {/* 勝利テキスト */}
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="text-7xl font-black text-center text-shimmer"
          >
            {MESSAGES.result_winner(winner.kaiju.nameJa)}
          </motion.h1>

          {/* 勝者・敗者情報 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.3 }}
            className="flex items-center gap-6 text-lg"
          >
            <span className="text-foreground">
              <span className="text-subtle text-sm">勝者</span>{' '}
              <span className="font-bold" style={{ color: winnerColor.primary }}>
                {winner.name} ({winner.kaiju.nameJa})
              </span>
            </span>
            <span className="text-slate-600">vs</span>
            <span className="text-foreground">
              <span className="text-subtle text-sm">敗者</span>{' '}
              <span className="font-bold text-destructive">
                {loser.name} ({loser.kaiju.nameJa})
              </span>
            </span>
          </motion.div>
        </div>

        {/* バトルサマリー */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="glass-panel w-full p-6"
          style={{
            boxShadow: '0 0 30px rgba(59, 130, 246, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
          }}
        >
          <h2 className="text-xl font-bold mb-4 text-center text-foreground">
            {MESSAGES.result_summary}
          </h2>

          <div className="grid grid-cols-3 gap-4 text-center">
            {/* ラウンド数 */}
            <div className="flex flex-col gap-1 border border-white/5 rounded-lg p-3">
              <span className="text-sm text-subtle">{MESSAGES.result_rounds}</span>
              <span className="text-3xl font-bold text-ice">{totalRounds}</span>
            </div>

            {/* 最高ダメージ */}
            <div className="flex flex-col gap-1 border border-white/5 rounded-lg p-3">
              <span className="text-sm text-subtle">{MESSAGES.result_maxDamage}</span>
              <span className="text-3xl font-bold text-destructive">{maxDamage}</span>
            </div>

            {/* MVPの叫び */}
            <div className="flex flex-col gap-1 border border-white/5 rounded-lg p-3">
              <span className="text-sm text-subtle">{MESSAGES.result_mvpShout}</span>
              <span className="text-lg font-bold text-amber-400">{mvpAttackName}</span>
            </div>
          </div>
        </motion.div>

        {/* アクションボタン */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex gap-4"
        >
          <button
            onClick={onPlayAgain}
            className="btn-base btn-gradient-border px-10 py-4 text-lg font-bold rounded-xl"
          >
            {MESSAGES.result_playAgain}
          </button>
          <button
            onClick={onBackToTitle}
            className="btn-base btn-ghost px-10 py-4 text-lg font-bold rounded-xl"
          >
            {MESSAGES.result_backToTitle}
          </button>
        </motion.div>
      </div>
    </div>
  );
}
