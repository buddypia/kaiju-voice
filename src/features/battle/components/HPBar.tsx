'use client';

import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface HPBarProps {
  hp: number;
  maxHp: number;
  playerName: string;
  element: KaijuElement;
  side: 'left' | 'right';
}

/**
 * HPバーコンポーネント
 * 属性色のグラデーションでHPを表示し、20%以下で赤く脈動する
 * 格闘ゲーム風のセグメントマーカー・内部光沢・グローエフェクト付き
 */
export function HPBar({ hp, maxHp, playerName, element, side }: HPBarProps) {
  const percentage = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  const isDanger = percentage <= 20;
  const colors = ELEMENT_STYLES[element];

  return (
    <div
      className={`flex flex-col gap-1.5 w-full ${side === 'right' ? 'items-end' : 'items-start'}`}
    >
      {/* プレイヤー名行: ドット + 名前 + HP数値 */}
      <div
        className={`flex items-center gap-2 ${side === 'right' ? 'flex-row-reverse' : 'flex-row'}`}
      >
        {/* 属性カラードット */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{
            background: colors.primary,
            boxShadow: `0 0 8px ${colors.glow}`,
          }}
        />
        <span className="text-base font-bold text-foreground">{playerName}</span>
        <span
          className={`text-sm font-mono font-bold ${isDanger ? 'text-red-400 animate-glow-pulse' : 'text-muted-foreground'}`}
        >
          {hp}/{maxHp}
        </span>
      </div>

      {/* HPバー本体 */}
      <div className="w-full h-6 bg-black/40 rounded-md overflow-hidden border border-white/15 relative">
        {/* HPフィル */}
        <div
          role="progressbar"
          aria-valuenow={hp}
          aria-valuemin={0}
          aria-valuemax={maxHp}
          aria-label={`${playerName}のHP`}
          className={`h-full bg-gradient-to-r ${colors.gradient} transition-all duration-500 ease-out relative ${isDanger ? 'animate-glow-pulse' : ''}`}
          style={{
            width: `${percentage}%`,
            boxShadow: isDanger
              ? '0 0 25px rgba(239, 68, 68, 0.8), 0 0 50px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255,255,255,0.3)'
              : `0 0 25px ${colors.glow}, 0 0 50px ${colors.glow}40, inset 0 1px 0 rgba(255,255,255,0.3)`,
          }}
        >
          {/* 内部光沢オーバーレイ */}
          <div className="absolute inset-0 bg-gradient-to-b from-white/25 via-transparent to-black/20 rounded-md" />
        </div>

        {/* セグメントマーカー (20%刻み) */}
        {[20, 40, 60, 80].map((pos) => (
          <div
            key={pos}
            className="absolute top-0 h-full w-px bg-white/20"
            style={{ left: `${pos}%` }}
          />
        ))}
      </div>
    </div>
  );
}
