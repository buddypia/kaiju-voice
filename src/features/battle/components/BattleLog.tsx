'use client';

import type { BattleLogEntry } from '@/features/battle/types/battle';
import { Star } from 'lucide-react';
import { MESSAGES } from '@/shared/constants/messages';

interface BattleLogProps {
  logs: BattleLogEntry[];
}

/**
 * バトルログコンポーネント
 * 直近5件のバトルログを最新順で表示する
 */
export function BattleLog({ logs }: BattleLogProps) {
  const recentLogs = [...logs].reverse().slice(0, 5);

  return (
    <div aria-live="polite" className="glass-panel p-3 w-full max-h-48 overflow-y-auto">
      <h3 className="text-xs font-bold text-muted-foreground mb-2 uppercase tracking-wider">
        {MESSAGES.battle_log}
      </h3>
      <div className="flex flex-col gap-2">
        {recentLogs.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">バトル開始を待っています...</p>
        ) : (
          recentLogs.map((entry, i) => (
            <div
              key={entry.timestamp}
              className={`text-xs font-mono px-2 py-2 rounded flex flex-col gap-1 ${
                i === 0 ? 'bg-white/10 text-foreground' : 'text-muted-foreground'
              }`}
            >
              <div className="flex justify-between items-center">
                <span>
                  <span className="text-muted-foreground mr-1">
                    R{entry.round}:P{entry.turn + 1}
                  </span>
                  <span className="font-bold">
                    {entry.attack.attackName}
                  </span>
                </span>
                <span
                  className={entry.attack.isCritical ? 'text-amber-400 font-bold text-sm' : 'text-red-400 font-bold'}
                >
                  {entry.attack.damage} dmg
                  {entry.attack.isCritical && (
                    <Star size={12} className="ml-1 text-amber-400 inline" aria-hidden="true" />
                  )}
                </span>
              </div>
              <div className="text-[10px] pl-1 border-l border-white/20 ml-1 opacity-80">
                <p>「{entry.attack.voiceAnalysis.transcript}」</p>
                <div className="flex gap-2 mt-0.5">
                  <span>迫力:{entry.attack.voiceAnalysis.intensity}</span>
                  <span>創造性:{entry.attack.voiceAnalysis.creativity}</span>
                  <span>感情:{entry.attack.voiceAnalysis.emotion}</span>
                  <span className="opacity-50">({entry.attack.voiceAnalysis.attackType})</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
