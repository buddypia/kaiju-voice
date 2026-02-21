'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Volume2 } from 'lucide-react';
import { MESSAGES } from '@/shared/constants/messages';

/** CommentaryOverlay の Props */
interface CommentaryOverlayProps {
  text: string;
  isLoading: boolean;
  isSpeaking: boolean;
  /** Gemini Live API音声使用中 */
  isLiveVoice?: boolean;
}

/**
 * AI実況テキストオーバーレイコンポーネント
 * バトル画面下部に表示し、ストリーミングテキストをフェードイン表示する
 */
export function CommentaryOverlay({
  text,
  isLoading,
  isSpeaking,
  isLiveVoice,
}: CommentaryOverlayProps) {
  const isVisible = isLoading || text.length > 0;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="commentary-overlay"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="w-full glass-panel px-4 py-3"
        >
          {/* ヘッダー行: AI実況ラベル + スピーキングアイコン */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-cyan-400/70 font-mono uppercase tracking-widest">
              {MESSAGES.commentary_label}
            </span>
            {isSpeaking && (
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              >
                <Volume2 className="w-3 h-3 text-amber-400" />
              </motion.span>
            )}
            {isLiveVoice && (
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="px-1.5 py-0.5 text-[10px] font-bold tracking-wider bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded"
              >
                LIVE API
              </motion.span>
            )}
          </div>

          {/* 実況テキスト / ローディング */}
          <div className="min-h-[2.5rem] flex items-center">
            {isLoading && !text ? (
              <span className="text-amber-400 text-sm font-mono animate-typewriter-cursor">
                ...
              </span>
            ) : (
              <p className="text-amber-400 text-sm leading-snug line-clamp-2 font-medium">
                {text}
                {isSpeaking && (
                  <span className="inline-block ml-0.5 animate-typewriter-cursor text-amber-400">
                    |
                  </span>
                )}
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
