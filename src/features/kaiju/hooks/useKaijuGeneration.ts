'use client';

import type { KaijuProfile } from '@/features/battle/types/battle';

/** 怪獣画像生成フック */
export function useKaijuGeneration() {
  const generateImage = async (kaiju: KaijuProfile): Promise<string | null> => {
    try {
      /** カテゴリに応じてアクション・スタイルを切り替え */
      const isHero = kaiju.category === 'hero';
      const action = isHero ? 'heroic battle pose, standing tall' : 'epic battle pose, roaring';
      const style = isHero
        ? 'anime hero battle scene, dramatic lighting, golden aura, dark background'
        : 'anime kaiju battle scene, dramatic lighting, dark background';

      const res = await fetch('/api/kaiju/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kaijuName: kaiju.name,
          element: kaiju.element,
          category: kaiju.category ?? 'kaiju',
          action,
          style,
        }),
      });
      const data = await res.json();
      return data.imageUrl ?? null;
    } catch (err) {
      console.error('怪獣画像生成失敗:', err);
      return null;
    }
  };
  return { generateImage };
}
