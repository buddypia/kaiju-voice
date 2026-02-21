'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import type { KaijuProfile, GameMode } from '@/features/battle/types/battle';
import { KAIJU_PRESETS, HERO_PRESETS, ELEMENT_NAMES } from '@/shared/constants/kaiju-data';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';
import { MESSAGES } from '@/shared/constants/messages';
import { KaijuCard } from '@/features/kaiju/components/KaijuCard';

interface SelectScreenProps {
  selectingPlayer: 0 | 1;
  gameMode: GameMode;
  onSelectKaiju: (player: 0 | 1, kaiju: KaijuProfile) => void;
}

/** 怪獣選択画面コンポーネント */
export function SelectScreen({ selectingPlayer, gameMode, onSelectKaiju }: SelectScreenProps) {
  const [selectedKaiju, setSelectedKaiju] = useState<KaijuProfile | null>(null);

  const handleConfirm = () => {
    if (!selectedKaiju) return;
    onSelectKaiju(selectingPlayer, selectedKaiju);
    setSelectedKaiju(null);
  };

  /** VS AI / ヒーロー VS 怪獣モード: P2はAIが自動選択 */
  useEffect(() => {
    if (selectingPlayer !== 1) return;
    if (gameMode !== 'vsai' && gameMode !== 'hero_vs_kaiju') return;

    const timer = setTimeout(() => {
      // hero_vs_kaiju はP2が怪獣、vsai はKAIJU_PRESETSからランダム選択
      const pool = KAIJU_PRESETS;
      const randomKaiju = pool[Math.floor(Math.random() * pool.length)];
      onSelectKaiju(1, randomKaiju);
    }, 1200);

    return () => clearTimeout(timer);
  }, [gameMode, selectingPlayer, onSelectKaiju]);

  /** ヘッダーテキスト: モードとプレイヤーに応じて切り替え */
  const headerText = (() => {
    if (gameMode === 'hero_vs_kaiju') {
      return selectingPlayer === 0 ? MESSAGES.select_hero_player : MESSAGES.select_ai;
    }
    return selectingPlayer === 0
      ? MESSAGES.select_player1
      : gameMode === 'vsai'
        ? MESSAGES.select_ai
        : MESSAGES.select_player2;
  })();

  /** タイトル: hero_vs_kaiju モードはP1/P2で切り替え、それ以外は共通タイトル */
  const titleText = (() => {
    if (gameMode === 'hero_vs_kaiju') {
      return selectingPlayer === 0 ? MESSAGES.select_title_hero : MESSAGES.select_title_kaiju;
    }
    return MESSAGES.select_title;
  })();

  /** アクセントカラー: hero_vs_kaiju P1=amber, P2=red; 通常 P1=cyan, P2=violet */
  const accentColor = (() => {
    if (gameMode === 'hero_vs_kaiju') {
      return selectingPlayer === 0 ? '#fbbf24' : '#ef4444';
    }
    return selectingPlayer === 0 ? '#22d3ee' : '#c4b5fd';
  })();

  const dataAccent = selectingPlayer === 0 ? 'primary' : 'secondary';

  return (
    <div
      className="relative min-h-screen flex flex-col items-center py-12 px-6 overflow-hidden bg-background"
      data-accent={dataAccent}
    >
      {/* 背景グロー */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-64 opacity-20"
          style={{
            background: `radial-gradient(ellipse, ${accentColor} 0%, transparent 70%)`,
            filter: 'blur(40px)',
          }}
        />
      </div>

      <div className="relative z-10 w-full max-w-6xl flex flex-col gap-8">
        {/* ヘッダー */}
        <div className="flex flex-col items-center gap-2">
          <h2 className="text-4xl font-bold tracking-wider text-[var(--color-accent)] text-glow">
            {headerText}
          </h2>
          <p className="text-lg text-muted-foreground">{titleText}</p>
        </div>

        {/* AI自動選択中 (vsai / hero_vs_kaiju のP2): ローディング表示 / 通常: カード一覧 */}
        {(gameMode === 'vsai' || gameMode === 'hero_vs_kaiju') && selectingPlayer === 1 ? (
          <div className="flex flex-col items-center gap-4 py-12">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 border-4 border-white/20 border-t-cyan-400 rounded-full"
            />
            <p className="text-lg text-white/60">{MESSAGES.select_ai_choosing}</p>
          </div>
        ) : (
          <>
            {/* カード一覧: hero_vs_kaiju P1はHERO_PRESETS、それ以外はKAIJU_PRESETS */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 justify-center">
              {(gameMode === 'hero_vs_kaiju' && selectingPlayer === 0
                ? HERO_PRESETS
                : KAIJU_PRESETS
              ).map((kaiju, i) => (
                <motion.div
                  key={kaiju.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                >
                  <KaijuCard
                    kaiju={kaiju}
                    isSelected={selectedKaiju?.id === kaiju.id}
                    onSelect={() => setSelectedKaiju(kaiju)}
                  />
                </motion.div>
              ))}
            </div>

            {/* 選択した怪獣の詳細パネル */}
            {selectedKaiju && (
              <div
                className="glass-panel p-6"
                style={{
                  borderColor: `${ELEMENT_STYLES[selectedKaiju.element].primary}60`,
                  boxShadow: `0 0 30px ${ELEMENT_STYLES[selectedKaiju.element].glow}`,
                }}
              >
                <div className="flex flex-col md:flex-row gap-6 items-center">
                  {/* 怪獣画像 */}
                  {selectedKaiju.imageUrl && (
                    <div className="w-32 h-32 rounded-xl overflow-hidden flex-shrink-0">
                      <Image
                        src={selectedKaiju.imageUrl}
                        alt={selectedKaiju.nameJa}
                        width={128}
                        height={128}
                        className="w-full h-full object-cover"
                        style={{
                          filter: `drop-shadow(0 0 12px ${ELEMENT_STYLES[selectedKaiju.element].glow})`,
                        }}
                      />
                    </div>
                  )}

                  {/* 怪獣名と属性 */}
                  <div className="flex flex-col gap-2 min-w-48">
                    <h3
                      className="text-3xl font-bold"
                      style={{
                        color: ELEMENT_STYLES[selectedKaiju.element].primary,
                        textShadow: `0 0 20px ${ELEMENT_STYLES[selectedKaiju.element].glow}`,
                      }}
                    >
                      {selectedKaiju.nameJa}
                    </h3>
                    <p className="text-sm font-medium text-subtle">{selectedKaiju.name}</p>
                    <span
                      className="inline-block px-3 py-1 rounded-full text-sm font-bold w-fit"
                      style={{
                        background: `${ELEMENT_STYLES[selectedKaiju.element].primary}30`,
                        color: ELEMENT_STYLES[selectedKaiju.element].primary,
                        border: `1px solid ${ELEMENT_STYLES[selectedKaiju.element].primary}60`,
                      }}
                    >
                      {ELEMENT_NAMES[selectedKaiju.element]}属性
                    </span>
                  </div>

                  {/* 説明 */}
                  <p className="flex-1 text-base text-foreground">{selectedKaiju.description}</p>

                  {/* ステータス */}
                  <div className="flex flex-col gap-3 min-w-40">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-subtle">攻撃力</span>
                        <span className="text-fire">{selectedKaiju.baseAttack}</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${(selectedKaiju.baseAttack / 20) * 100}%`,
                            background: 'linear-gradient(90deg, #ef4444, #f97316)',
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-subtle">防御力</span>
                        <span className="text-ice">{selectedKaiju.baseDefense}</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${(selectedKaiju.baseDefense / 20) * 100}%`,
                            background: 'linear-gradient(90deg, #22d3ee, #3b82f6)',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 確定ボタン */}
            <div className="flex justify-center">
              <button
                onClick={handleConfirm}
                disabled={!selectedKaiju}
                className={`px-12 py-4 text-xl font-bold rounded-xl text-white disabled:opacity-40 disabled:cursor-not-allowed btn-base ${selectedKaiju ? 'btn-gradient-border animate-glow-pulse-btn' : ''}`}
                style={
                  selectedKaiju
                    ? {
                        boxShadow: `0 0 40px ${accentColor}60, 0 0 80px ${accentColor}30`,
                      }
                    : {
                        background: 'rgba(255,255,255,0.1)',
                      }
                }
              >
                {MESSAGES.select_confirm}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
