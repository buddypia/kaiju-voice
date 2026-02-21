'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { Zap, Sparkles } from 'lucide-react';

import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';
import type { KaijuElement } from '@/features/battle/types/battle';

/** 攻撃シーケンスのフェーズ */
type SequencePhase = 'scores' | 'attack_name' | 'done';

/** 攻撃タイプの日本語ラベル */
const ATTACK_TYPE_LABEL: Record<'physical' | 'special' | 'ultimate', string> = {
  physical: '通常攻撃',
  special: '特殊技',
  ultimate: '超必殺技',
};

interface AttackSequenceProps {
  voiceAnalysis: {
    intensity: number;
    creativity: number;
    emotion: number;
    attackType: 'physical' | 'special' | 'ultimate';
    transcript: string;
  };
  attackName: string;
  element: KaijuElement;
  isActive: boolean;
  onSequenceComplete: () => void;
}

/**
 * スコアバーの1本分を表示するコンポーネント
 * @param label - ラベルテキスト
 * @param value - スコア値 (0-100)
 * @param color - バーの色 (hex)
 * @param delay - アニメーション開始ディレイ (ms)
 */
function ScoreBar({
  label,
  value,
  color,
  delay,
}: {
  label: string;
  value: number;
  color: string;
  delay: number;
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const DURATION = 800;

  useEffect(() => {
    const startDelay = setTimeout(() => {
      const animate = (timestamp: number) => {
        if (startTimeRef.current === null) startTimeRef.current = timestamp;
        const elapsed = timestamp - startTimeRef.current;
        const progress = Math.min(elapsed / DURATION, 1);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplayValue(Math.round(eased * value));
        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        }
      };
      rafRef.current = requestAnimationFrame(animate);
    }, delay);

    return () => {
      clearTimeout(startDelay);
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [value, delay]);

  return (
    <div className="flex items-center gap-3">
      <span className="w-14 text-sm font-medium text-slate-300 shrink-0">{label}</span>
      <div className="flex-1 h-4 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full animate-score-bar-fill"
          style={
            {
              '--bar-width': `${value}%`,
              backgroundColor: color,
              boxShadow: `0 0 8px ${color}`,
              animationDelay: `${delay}ms`,
            } as React.CSSProperties
          }
        />
      </div>
      <span className="w-8 text-right text-sm font-bold tabular-nums" style={{ color }}>
        {displayValue}
      </span>
    </div>
  );
}

/**
 * 攻撃シーケンスをドラマチックに表示するコンポーネント
 * Phase 1: AI VOICE JUDGE スコア表示 (0ms-1500ms)
 * Phase 2: 攻撃名ズームイン表示 (1500ms-2500ms)
 * Phase 3: 完了コールバック呼び出し
 */
export function AttackSequence({
  voiceAnalysis,
  attackName,
  element,
  isActive,
  onSequenceComplete,
}: AttackSequenceProps) {
  const [phase, setPhase] = useState<SequencePhase>('scores');
  const elementStyle = ELEMENT_STYLES[element];
  const onCompleteRef = useRef(onSequenceComplete);
  useEffect(() => {
    onCompleteRef.current = onSequenceComplete;
  }, [onSequenceComplete]);

  useEffect(() => {
    if (!isActive) return;

    const toAttackName = setTimeout(() => {
      setPhase('attack_name');
    }, 1500);

    const toDone = setTimeout(() => {
      setPhase('done');
      onCompleteRef.current();
    }, 2500);

    return () => {
      clearTimeout(toAttackName);
      clearTimeout(toDone);
    };
  }, [isActive]);

  if (!isActive) return null;

  const isUltimate = voiceAnalysis.attackType === 'ultimate';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
      <AnimatePresence mode="wait">
        {phase === 'scores' && (
          <motion.div
            key="scores"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="glass-panel p-6 w-full max-w-sm mx-4"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))',
            }}
          >
            {/* ヘッダー */}
            <div className="text-center mb-5">
              <div className="flex items-center justify-center gap-2">
                <Zap size={20} className="text-amber-400" />
                <p className="text-xl font-black tracking-widest text-amber-400 animate-judge-header-pulse">
                  AI VOICE JUDGE
                </p>
                <Zap size={20} className="text-amber-400" />
              </div>
            </div>

            {/* スコアバー群 */}
            <div className="space-y-3 mb-5">
              <ScoreBar label="迫力" value={voiceAnalysis.intensity} color="#ef4444" delay={100} />
              <ScoreBar
                label="創造性"
                value={voiceAnalysis.creativity}
                color="#a855f7"
                delay={300}
              />
              <ScoreBar label="感情" value={voiceAnalysis.emotion} color="#3b82f6" delay={500} />
            </div>

            {/* 攻撃タイプ */}
            <div className="text-center border-t border-white/10 pt-3 mt-2">
              {isUltimate ? (
                <div className="flex items-center justify-center gap-2">
                  <Sparkles size={18} className="text-amber-400" />
                  <p className="text-base font-bold text-amber-400 text-glow-strong">
                    {ATTACK_TYPE_LABEL[voiceAnalysis.attackType]}
                  </p>
                  <Sparkles size={18} className="text-amber-400" />
                </div>
              ) : (
                <p className="text-base font-semibold text-slate-300">
                  {ATTACK_TYPE_LABEL[voiceAnalysis.attackType]}
                </p>
              )}
            </div>
          </motion.div>
        )}

        {phase === 'attack_name' && (
          <motion.div
            key="attack_name"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="text-center px-4"
          >
            <p
              className="text-8xl font-black animate-attack-name-zoom"
              style={{
                color: elementStyle.primary,
                textShadow: `0 0 30px ${elementStyle.glow}, 0 0 60px ${elementStyle.glow}`,
              }}
            >
              {attackName}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
