'use client';

import { useState } from 'react';
import Image from 'next/image';
import type { KaijuProfile } from '@/features/battle/types/battle';
import { ELEMENT_NAMES } from '@/shared/constants/kaiju-data';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';
import { Sword, Shield, Zap, Snowflake, Flame, Mountain, CircleDashed, Sun } from 'lucide-react';

interface KaijuCardProps {
  kaiju: KaijuProfile;
  isSelected: boolean;
  onSelect: () => void;
}

/** 属性アイコンを返す */
function ElementIcon({ element }: { element: KaijuProfile['element'] }) {
  const props = { size: 16, strokeWidth: 2 };
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
 * 怪獣カードコンポーネント (怪獣選択画面用)
 * 怪獣の名前・属性・ステータスを表示し、選択時にグロー効果を適用する
 */
export function KaijuCard({ kaiju, isSelected, onSelect }: KaijuCardProps) {
  const colors = ELEMENT_STYLES[kaiju.element];
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`relative flex flex-col gap-3 p-4 rounded-xl border transition-all duration-250 cursor-pointer min-h-[44px] w-full text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none ${
        isSelected
          ? 'border-white/40 bg-white/10'
          : 'border-white/10 bg-white/5 hover:bg-white/8 hover:border-white/20'
      }`}
      style={
        isSelected
          ? {
              borderColor: colors.primary,
              boxShadow: `0 0 20px ${colors.glow}`,
              ...(isHovered
                ? {
                    transform: 'perspective(800px) rotateY(5deg) rotateX(2deg) scale(1.03)',
                    transition: 'transform 0.3s ease',
                  }
                : { transition: 'transform 0.3s ease' }),
            }
          : isHovered
            ? {
                transform: 'perspective(800px) rotateY(5deg) rotateX(2deg) scale(1.03)',
                transition: 'transform 0.3s ease',
              }
            : { transition: 'transform 0.3s ease' }
      }
    >
      {isSelected && (
        <div
          className="absolute inset-0 rounded-xl opacity-10"
          style={{
            background: `radial-gradient(circle at center, ${colors.primary}, transparent)`,
          }}
        />
      )}

      {/* 怪獣サムネイル */}
      {kaiju.imageUrl && (
        <div className="relative w-full aspect-square rounded-lg overflow-hidden bg-black/30">
          {kaiju.imageUrl.startsWith('data:') ? (
            <img
              src={kaiju.imageUrl}
              alt={kaiju.nameJa}
              className="w-full h-full object-cover"
              style={{ filter: `drop-shadow(0 0 8px ${colors.glow})` }}
            />
          ) : (
            <Image
              src={kaiju.imageUrl}
              alt={kaiju.nameJa}
              width={256}
              height={256}
              className="w-full h-full object-cover"
              style={{ filter: `drop-shadow(0 0 8px ${colors.glow})` }}
            />
          )}
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-foreground">{kaiju.nameJa}</h3>
          <p className="text-xs text-muted-foreground">{kaiju.name}</p>
        </div>
        <div
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold"
          style={{
            color: colors.primary,
            backgroundColor: `${colors.glow}`,
            border: `1px solid ${colors.primary}40`,
          }}
        >
          <ElementIcon element={kaiju.element} />
          <span>{ELEMENT_NAMES[kaiju.element]}</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground line-clamp-2">{kaiju.description}</p>

      <div className="flex gap-4 mt-auto">
        <div className="flex items-center gap-1 text-xs">
          <Sword size={12} className="text-red-400" />
          <span className="text-foreground font-mono font-bold">{kaiju.baseAttack}</span>
          <span className="text-muted-foreground">ATK</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <Shield size={12} className="text-blue-400" />
          <span className="text-foreground font-mono font-bold">{kaiju.baseDefense}</span>
          <span className="text-muted-foreground">DEF</span>
        </div>
      </div>
    </button>
  );
}
