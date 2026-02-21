import type { KaijuElement } from '@/features/battle/types/battle';

/** エレメント別スタイル定義 — CSS @theme と同期管理 */
export const ELEMENT_STYLES: Record<
  KaijuElement,
  { primary: string; glow: string; gradient: string }
> = {
  fire: { primary: '#ef4444', glow: 'rgba(239,68,68,0.4)', gradient: 'from-red-500 to-orange-500' },
  ice: {
    primary: '#22d3ee',
    glow: 'rgba(34,211,238,0.4)',
    gradient: 'from-cyan-400 to-blue-500',
  },
  thunder: {
    primary: '#eab308',
    glow: 'rgba(234,179,8,0.4)',
    gradient: 'from-yellow-400 to-amber-500',
  },
  earth: {
    primary: '#84cc16',
    glow: 'rgba(132,204,22,0.4)',
    gradient: 'from-lime-400 to-green-500',
  },
  void: {
    primary: '#a855f7',
    glow: 'rgba(168,85,247,0.4)',
    gradient: 'from-purple-400 to-violet-600',
  },
  light: {
    primary: '#fbbf24',
    glow: 'rgba(251,191,36,0.4)',
    gradient: 'from-amber-300 to-yellow-500',
  },
};

/** エレメント別グラデーション Tailwindクラス */
export const ELEMENT_GRADIENT: Record<KaijuElement, string> = {
  fire: 'from-red-500 to-orange-500',
  ice: 'from-cyan-400 to-blue-500',
  thunder: 'from-yellow-400 to-amber-500',
  earth: 'from-lime-400 to-green-500',
  void: 'from-purple-400 to-violet-600',
  light: 'from-amber-300 to-yellow-500',
};
