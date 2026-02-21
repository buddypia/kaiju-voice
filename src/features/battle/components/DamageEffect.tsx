'use client';

import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface DamageEffectProps {
  damage: number;
  isCritical: boolean;
  position: 'left' | 'right';
  /** 攻撃者の属性（ダメージ色に使用） */
  element?: KaijuElement;
  /** 攻撃名 */
  attackName?: string;
}

/**
 * ダメージポップアップコンポーネント
 * ダメージ数値がポップアップして消えるアニメーション
 * 属性カラー対応 + 攻撃名表示
 */
export function DamageEffect({
  damage,
  isCritical,
  position,
  element,
  attackName,
}: DamageEffectProps) {
  const elementColor = element ? ELEMENT_STYLES[element].primary : '#ffffff';
  const glowColor = element ? ELEMENT_STYLES[element].glow : 'rgba(255, 255, 255, 0.6)';

  return (
    <div
      aria-live="assertive"
      role="alert"
      className={`absolute top-1/4 z-20 pointer-events-none ${
        position === 'left' ? 'left-1/4 -translate-x-1/2' : 'right-1/4 translate-x-1/2'
      }`}
    >
      <div className="flex flex-col items-center gap-1">
        {/* 攻撃名 */}
        {attackName && (
          <span
            className="text-base font-bold tracking-wider whitespace-nowrap animate-damage-pop-enhanced"
            style={{
              color: elementColor,
              textShadow: `0 0 15px ${glowColor}`,
              animationDuration: '0.6s',
            }}
          >
            {attackName}
          </span>
        )}

        {/* クリティカル表示 */}
        {isCritical && (
          <span
            className="text-4xl font-black tracking-widest animate-damage-pop-enhanced text-amber-400"
            style={{
              textShadow: '0 0 45px rgba(251, 191, 36, 0.9), 0 0 90px rgba(251, 191, 36, 0.5)',
              animationDelay: '0.05s',
            }}
          >
            CRITICAL!
          </span>
        )}

        {/* ダメージ数値 */}
        <span
          className={`animate-damage-pop-enhanced font-black drop-shadow-lg ${
            isCritical ? 'text-8xl' : 'text-6xl'
          }`}
          style={{
            display: 'inline-block',
            color: isCritical ? '#fbbf24' : elementColor,
            textShadow: isCritical
              ? '0 0 45px rgba(251, 191, 36, 0.9), 0 0 90px rgba(251, 191, 36, 0.5)'
              : `0 0 30px ${glowColor}, 0 0 60px ${glowColor}`,
            animationDelay: '0.1s',
          }}
        >
          -{damage}
        </span>
      </div>
    </div>
  );
}
