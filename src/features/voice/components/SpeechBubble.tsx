'use client';

import { motion } from 'framer-motion';

interface SpeechBubbleProps {
  text: string;
  side: 'left' | 'right';
  playerName: string;
}

/** 音声認識結果を吹き出しで表示するコンポーネント */
export function SpeechBubble({ text, side, playerName }: SpeechBubbleProps) {
  const isLeft = side === 'left';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: -10 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className={`absolute z-30 max-w-[260px] ${
        isLeft ? 'left-4 sm:left-12' : 'right-4 sm:right-12'
      } top-4`}
    >
      <div className="relative">
        {/* 吹き出し本体 */}
        <div className="relative px-4 py-3 rounded-2xl backdrop-blur-xl bg-white/10 border border-white/20 shadow-[0_0_20px_rgba(34,211,238,0.15)]">
          <p className="text-xs font-mono text-cyan-400/70 mb-1">{playerName}</p>
          <p className="text-sm font-bold text-white leading-snug break-all">{text}</p>
        </div>

        {/* 吹き出しのしっぽ */}
        <div
          className={`absolute -bottom-2 ${isLeft ? 'left-6' : 'right-6'} w-4 h-4 rotate-45 backdrop-blur-xl bg-white/10 border-b border-r border-white/20`}
        />
      </div>
    </motion.div>
  );
}
