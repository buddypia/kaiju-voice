'use client';

import { Swords, Mic, Brain, Zap, Bot } from 'lucide-react';
import type { BattleSubPhase } from '@/features/battle/types/battle';
import { MESSAGES } from '@/shared/constants/messages';

interface TurnIndicatorProps {
  playerName: string;
  subPhase: BattleSubPhase;
}

/** サブフェーズに対応するアイコンを返す */
function getPhaseIcon(subPhase: BattleSubPhase) {
  switch (subPhase) {
    case 'ready':
      return <Swords size={20} />;
    case 'recording':
      return <Mic size={20} />;
    case 'analyzing':
      return <Brain size={20} />;
    case 'attacking':
      return <Zap size={20} />;
    case 'ai_thinking':
      return <Bot size={20} />;
    default:
      return <Swords size={20} />;
  }
}

/**
 * ターンインジケーターコンポーネント
 * 現在のターンプレイヤーとサブフェーズに応じたメッセージとアイコンを表示する
 */
export function TurnIndicator({ playerName, subPhase }: TurnIndicatorProps) {
  const getMessage = () => {
    switch (subPhase) {
      case 'ready':
        return MESSAGES.battle_yourTurn(playerName);
      case 'recording':
        return MESSAGES.battle_recording;
      case 'analyzing':
        return MESSAGES.battle_analyzing;
      case 'attacking':
        return '攻撃判定中...';
      case 'ai_thinking':
        return 'AI思考中...';
      default:
        return MESSAGES.battle_yourTurn(playerName);
    }
  };

  const isRecording = subPhase === 'recording';
  const isAnalyzing = subPhase === 'analyzing';
  const isAttacking = subPhase === 'attacking';
  const isAiThinking = subPhase === 'ai_thinking';

  const isReady = subPhase === 'ready';

  return (
    <div
      key={subPhase}
      role="status"
      aria-live="polite"
      className={`flex items-center justify-center px-8 py-3 rounded-xl border w-full max-w-md ${
        isReady
          ? 'border-cyan-400/40 bg-cyan-400/5 animate-slide-up-bounce'
          : isRecording
            ? 'border-red-500/50 bg-red-500/10 animate-glow-pulse'
            : isAnalyzing
              ? 'border-amber-500/50 bg-amber-500/10 animate-glow-pulse'
              : isAttacking
                ? 'border-blue-500/50 bg-blue-500/10'
                : isAiThinking
                  ? 'border-violet-500/50 bg-violet-500/10 animate-glow-pulse'
                  : 'border-cyan-400/40 bg-cyan-400/5'
      }`}
      style={
        !isRecording && !isAnalyzing && !isAttacking && !isAiThinking
          ? { boxShadow: '0 0 16px rgba(34, 211, 238, 0.15)' }
          : {}
      }
    >
      <div className="flex items-center justify-center gap-3">
        <span
          className={
            isRecording
              ? 'text-red-400'
              : isAnalyzing
                ? 'text-amber-400'
                : isAttacking
                  ? 'text-blue-400'
                  : isAiThinking
                    ? 'text-violet-400'
                    : 'text-cyan-400'
          }
        >
          {getPhaseIcon(subPhase)}
        </span>
        {(isRecording || isAnalyzing) && (
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
        )}
        <p
          className={`text-xl font-black text-center ${
            isRecording
              ? 'text-red-400'
              : isAnalyzing
                ? 'text-amber-400'
                : isAttacking
                  ? 'text-blue-400'
                  : isAiThinking
                    ? 'text-violet-400'
                    : 'text-foreground'
          }`}
        >
          {getMessage()}
        </p>
      </div>
    </div>
  );
}
