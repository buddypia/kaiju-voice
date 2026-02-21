import type { KaijuProfile, KaijuElement } from '@/features/battle/types/battle';

/** 属性相性テーブル: ELEMENT_MATCHUP[攻撃][防御] = 倍率 */
export const ELEMENT_MATCHUP: Record<KaijuElement, Record<KaijuElement, number>> = {
  fire: { fire: 1.0, ice: 1.5, thunder: 0.8, earth: 1.0, void: 0.8, light: 0.8 },
  ice: { fire: 0.8, ice: 1.0, thunder: 1.5, earth: 0.8, void: 1.0, light: 1.0 },
  thunder: { fire: 1.0, ice: 0.8, thunder: 1.0, earth: 1.5, void: 0.8, light: 1.0 },
  earth: { fire: 1.0, ice: 1.0, thunder: 0.8, earth: 1.0, void: 1.5, light: 0.8 },
  void: { fire: 1.5, ice: 0.8, thunder: 1.0, earth: 0.8, void: 1.0, light: 1.5 },
  light: { fire: 1.5, ice: 1.0, thunder: 1.0, earth: 1.5, void: 0.8, light: 1.0 },
};

/** 怪獣プリセットデータ (5体) */
export const KAIJU_PRESETS: KaijuProfile[] = [
  {
    id: '01',
    name: 'Infernus',
    nameJa: 'インフェルヌス',
    element: 'fire',
    category: 'kaiju',
    description: '灼熱の怪獣。すべてを焼き尽くす',
    imageUrl: '/images/kaiju-infernus.png',
    baseAttack: 12,
    baseDefense: 8,
  },
  {
    id: '02',
    name: 'Glacius',
    nameJa: 'グレイシアス',
    element: 'ice',
    category: 'kaiju',
    description: '氷の怪獣。絶対零度の守護者',
    imageUrl: '/images/kaiju-glacius.png',
    baseAttack: 8,
    baseDefense: 12,
  },
  {
    id: '03',
    name: 'Voltarion',
    nameJa: 'ボルタリオン',
    element: 'thunder',
    category: 'kaiju',
    description: '雷の怪獣。稲妻を纏う破壊者',
    imageUrl: '/images/kaiju-voltarion.png',
    baseAttack: 11,
    baseDefense: 9,
  },
  {
    id: '04',
    name: 'Terradon',
    nameJa: 'テラドン',
    element: 'earth',
    category: 'kaiju',
    description: '大地の怪獣。揺るがぬ巨体',
    imageUrl: '/images/kaiju-terradon.png',
    baseAttack: 9,
    baseDefense: 11,
  },
  {
    id: '05',
    name: 'Nihilus',
    nameJa: 'ニヒルス',
    element: 'void',
    category: 'kaiju',
    description: '虚無の怪獣。全てを飲み込む',
    imageUrl: '/images/kaiju-nihilus.png',
    baseAttack: 10,
    baseDefense: 10,
  },
];

/** ヒーロープリセットデータ (5体) */
export const HERO_PRESETS: KaijuProfile[] = [
  {
    id: 'h01',
    name: 'Solaris',
    nameJa: 'ソラリス',
    element: 'light',
    category: 'hero',
    description: '太陽の戦士。正義の光で闇を切り裂く',
    imageUrl: '/images/hero-solaris.png',
    baseAttack: 11,
    baseDefense: 9,
  },
  {
    id: 'h02',
    name: 'Frostguard',
    nameJa: 'フロストガード',
    element: 'ice',
    category: 'hero',
    description: '氷結の守護者。冷気の盾で民を守る',
    imageUrl: '/images/hero-frostguard.png',
    baseAttack: 8,
    baseDefense: 12,
  },
  {
    id: 'h03',
    name: 'Stormbreaker',
    nameJa: 'ストームブレイカー',
    element: 'thunder',
    category: 'hero',
    description: '嵐の破壊者。雷を操る空の勇者',
    imageUrl: '/images/hero-stormbreaker.png',
    baseAttack: 12,
    baseDefense: 8,
  },
  {
    id: 'h04',
    name: 'Gaia Knight',
    nameJa: 'ガイアナイト',
    element: 'earth',
    category: 'hero',
    description: '大地の騎士。揺るがぬ信念と鉄壁の守り',
    imageUrl: '/images/hero-gaiaknight.png',
    baseAttack: 9,
    baseDefense: 11,
  },
  {
    id: 'h05',
    name: 'Shadow Hunter',
    nameJa: 'シャドウハンター',
    element: 'void',
    category: 'hero',
    description: '影の狩人。闇から闇へ、獲物を追い詰める',
    imageUrl: '/images/hero-shadowhunter.png',
    baseAttack: 10,
    baseDefense: 10,
  },
];

/** 属性の日本語名 */
export const ELEMENT_NAMES: Record<KaijuElement, string> = {
  fire: '火',
  ice: '氷',
  thunder: '雷',
  earth: '地',
  void: '虚',
  light: '光',
};

/** 初期HP */
export const INITIAL_HP = 200;

/** 録音時間 (ミリ秒) */
export const RECORDING_DURATION_MS = 5000;
