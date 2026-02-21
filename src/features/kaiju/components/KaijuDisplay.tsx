'use client';

import Image from 'next/image';
import type { KaijuProfile } from '@/features/battle/types/battle';
import { ELEMENT_NAMES } from '@/shared/constants/kaiju-data';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';
import { Zap, Snowflake, Flame, Mountain, CircleDashed, Sun } from 'lucide-react';

interface KaijuDisplayProps {
  kaiju: KaijuProfile;
  side: 'left' | 'right';
  isAttacking: boolean;
}

/** 属性のSVGアイコン (大きめ表示) */
function ElementDisplayIcon({ element }: { element: KaijuProfile['element'] }) {
  const props = { size: 80, strokeWidth: 1.5 };
  switch (element) {
    case 'fire':
      return <Flame {...props} />;
    case 'ice':
      return <Snowflake {...props} />;
    case 'thunder':
      return <Zap {...props} />;
    case 'earth':
      return <Mountain {...props} />;
    case 'void':
      return <CircleDashed {...props} />;
    case 'light':
      return <Sun {...props} />;
  }
}

/**
 * 怪獣ディスプレイコンポーネント (バトル画面用)
 * 怪獣画像または属性SVGアイコンを表示し、攻撃時にアニメーションする
 * 外部オーラリング・二重グロー・属性バッジ付き
 */
export function KaijuDisplay({ kaiju, side, isAttacking }: KaijuDisplayProps) {
  const colors = ELEMENT_STYLES[kaiju.element];
  const attackTranslate = side === 'left' ? 'translate-x-8' : '-translate-x-8';

  return (
    <div
      className={`flex flex-col items-center gap-3 transition-transform duration-300 ease-out ${
        isAttacking ? attackTranslate : 'translate-x-0'
      }`}
    >
      {/* 外部オーラリング + メインキャラクター */}
      <div className="relative flex items-center justify-center">
        {/* 外側回転リング (時計回り) */}
        <svg
          className="absolute w-52 h-52 animate-spin"
          style={{ animationDuration: '20s' }}
          viewBox="0 0 200 200"
        >
          <circle
            cx="100"
            cy="100"
            r="95"
            fill="none"
            stroke={colors.primary}
            strokeWidth="1"
            strokeDasharray="8 12"
            opacity="0.4"
          />
        </svg>

        {/* 内側回転リング (反時計回り) */}
        <svg
          className="absolute w-48 h-48 animate-spin"
          style={{ animationDuration: '15s', animationDirection: 'reverse' }}
          viewBox="0 0 200 200"
        >
          <circle
            cx="100"
            cy="100"
            r="95"
            fill="none"
            stroke={colors.primary}
            strokeWidth="0.5"
            strokeDasharray="4 8"
            opacity="0.3"
          />
        </svg>

        {/* メインキャラクター円 */}
        <div
          className={`relative flex items-center justify-center w-44 h-44 rounded-full animate-float ${
            isAttacking ? 'animate-glow-pulse' : ''
          }`}
          style={{
            background: `radial-gradient(circle, ${colors.glow}, transparent 70%)`,
            boxShadow: `0 0 50px ${colors.glow}, 0 0 100px ${colors.glow}`,
          }}
        >
          {kaiju.imageUrl ? (
            kaiju.imageUrl.startsWith('data:') ? (
              <img
                src={kaiju.imageUrl}
                alt={kaiju.nameJa}
                className="w-40 h-40 object-contain rounded-full"
                style={{ filter: `drop-shadow(0 0 16px ${colors.primary})` }}
              />
            ) : (
              <Image
                src={kaiju.imageUrl}
                alt={kaiju.nameJa}
                width={160}
                height={160}
                className="w-40 h-40 object-contain rounded-full"
                style={{ filter: `drop-shadow(0 0 16px ${colors.primary})` }}
              />
            )
          ) : (
            <div style={{ color: colors.primary }}>
              <ElementDisplayIcon element={kaiju.element} />
            </div>
          )}

          {/* 攻撃時オーバーレイ */}
          {isAttacking && (
            <div
              className="absolute inset-0 rounded-full animate-critical-flash"
              style={{
                background: `radial-gradient(circle, ${colors.glow} 0%, ${colors.primary}40 40%, transparent 70%)`,
              }}
            />
          )}
        </div>
      </div>

      {/* 名前 */}
      <p className="text-lg font-bold text-foreground text-glow">{kaiju.nameJa}</p>

      {/* 属性バッジ */}
      <span
        className="px-3 py-0.5 rounded-full text-xs font-bold border"
        style={{
          color: colors.primary,
          borderColor: `${colors.primary}60`,
          background: `${colors.primary}15`,
          boxShadow: `0 0 10px ${colors.glow}`,
        }}
      >
        {ELEMENT_NAMES[kaiju.element]}属性
      </span>
    </div>
  );
}
