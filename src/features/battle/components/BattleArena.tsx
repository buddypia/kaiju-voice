'use client';

import { useState, useEffect, useCallback, startTransition } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type {
  Player,
  AttackResult,
  BattleSubPhase,
  BattleLogEntry,
  GameMode,
} from '@/features/battle/types/battle';
import { MESSAGES } from '@/shared/constants/messages';
import { HPBar } from '@/features/battle/components/HPBar';
import { DamageEffect } from '@/features/battle/components/DamageEffect';
import { TurnIndicator } from '@/features/battle/components/TurnIndicator';
import { BattleLog } from '@/features/battle/components/BattleLog';
import { KaijuDisplay } from '@/features/kaiju/components/KaijuDisplay';
import { VoiceRecorder } from '@/features/voice/components/VoiceRecorder';
import { SpeechBubble } from '@/features/voice/components/SpeechBubble';
import { ParticleCanvas, ImpactFlash, VoiceVisualizer, PinchOverlay } from '@/features/vfx';

interface BattleArenaProps {
  players: [Player, Player];
  currentTurn: 0 | 1;
  roundNumber: number;
  lastAttack: AttackResult | null;
  battleSubPhase: BattleSubPhase;
  battleLog: BattleLogEntry[];
  gameMode: GameMode;
  onStartRecording: () => void;
  onShout: (blob: Blob) => void;
  shoutTranscript: { text: string; turn: 0 | 1 } | null;
}

/**
 * バトルアリーナ統合コンポーネント
 * 全バトルUIコンポーネント + VFXを統合してバトル画面を構成する
 */
export function BattleArena({
  players,
  currentTurn,
  roundNumber,
  lastAttack,
  battleSubPhase,
  battleLog,
  gameMode,
  onStartRecording,
  onShout,
  shoutTranscript,
}: BattleArenaProps) {
  const [showDamage, setShowDamage] = useState(false);
  const [isP0Attacking, setIsP0Attacking] = useState(false);
  const [isP1Attacking, setIsP1Attacking] = useState(false);
  const [showFlash, setShowFlash] = useState(false);
  const [showParticles, setShowParticles] = useState(false);
  const [voiceAnalyserData, setVoiceAnalyserData] = useState<Uint8Array | null>(null);

  const handleAnalyserUpdate = useCallback((data: Uint8Array | null) => {
    setVoiceAnalyserData(data);
  }, []);

  /** 攻撃演出のシェイク強度を計算 */
  const getShakeClass = (damage: number, isCritical: boolean): string => {
    if (isCritical) return 'animate-screen-shake-heavy';
    if (damage >= 40) return 'animate-screen-shake-heavy';
    return 'animate-screen-shake-light';
  };

  const [shakeClass, setShakeClass] = useState('');

  useEffect(() => {
    if (!lastAttack) return;

    startTransition(() => {
      if (lastAttack.player === 0) {
        setIsP0Attacking(true);
      } else {
        setIsP1Attacking(true);
      }
      setShowDamage(true);
      setShowFlash(true);
      setShowParticles(true);
      setShakeClass(getShakeClass(lastAttack.damage, lastAttack.isCritical));
    });

    const attackTimer = setTimeout(() => {
      startTransition(() => {
        setIsP0Attacking(false);
        setIsP1Attacking(false);
      });
    }, 400);

    const flashTimer = setTimeout(
      () => {
        startTransition(() => setShowFlash(false));
      },
      lastAttack.isCritical ? 500 : 300,
    );

    const particleTimer = setTimeout(() => {
      startTransition(() => setShowParticles(false));
    }, 900);

    const damageTimer = setTimeout(() => {
      startTransition(() => {
        setShowDamage(false);
        setShakeClass('');
      });
    }, 1100);

    return () => {
      clearTimeout(attackTimer);
      clearTimeout(flashTimer);
      clearTimeout(particleTimer);
      clearTimeout(damageTimer);
    };
  }, [lastAttack]);

  const isAITurn = (gameMode === 'vsai' || gameMode === 'hero_vs_kaiju') && currentTurn === 1;
  const canRecord = battleSubPhase === 'ready';

  // 攻撃属性（パーティクル / フラッシュ用）
  const attackElement = lastAttack ? players[lastAttack.player].kaiju.element : 'fire';
  // ダメージ受ける側の位置
  const defenderPosition = lastAttack?.player === 0 ? 'right' : 'left';

  return (
    <div
      className={`relative flex flex-col h-full overflow-hidden bg-background ${shakeClass}`}
      aria-live="polite"
    >
      {/* 全画面フラッシュエフェクト */}
      <ImpactFlash
        element={attackElement}
        isActive={showFlash}
        isCritical={lastAttack?.isCritical}
      />

      {/* ピンチ演出オーバーレイ (HP25%以下) */}
      <PinchOverlay players={players} />

      {/* === TOP ZONE: ラウンド + HPバー === */}
      <div className="relative z-10 flex flex-col gap-3 px-4 pt-4 pb-2">
        {/* ラウンド表示（中央） */}
        <div className="flex justify-center">
          <div className="px-6 py-2 rounded-full backdrop-blur-xl bg-white/5 border border-white/10 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
            <p className="text-base font-black text-white tracking-[0.3em] uppercase">
              {MESSAGES.battle_round(roundNumber)}
            </p>
          </div>
        </div>

        {/* HPバー横並び */}
        <div className="flex gap-6 items-start">
          <div className="flex-1">
            <HPBar
              hp={players[0].hp}
              maxHp={players[0].maxHp}
              playerName={players[0].name}
              element={players[0].kaiju.element}
              side="left"
            />
          </div>
          <div className="flex-1">
            <HPBar
              hp={players[1].hp}
              maxHp={players[1].maxHp}
              playerName={players[1].name}
              element={players[1].kaiju.element}
              side="right"
            />
          </div>
        </div>
      </div>

      {/* === ARENA ZONE: キャラクター + VS === */}
      <motion.div
        animate={lastAttack?.isCritical && showDamage ? { x: [0, -5, 5, -3, 3, 0] } : { x: 0 }}
        transition={{ duration: 0.3 }}
        className={`relative flex-1 flex items-center justify-center min-h-0 ${
          lastAttack?.isCritical && showDamage ? 'animate-critical-flash' : ''
        }`}
      >
        {/* 背景エネルギーエフェクト */}
        <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full animate-arena-energy"
            style={{
              background: 'radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%)',
            }}
          />
        </div>

        {/* アリーナグリッド */}
        <div className="absolute inset-0 arena-grid opacity-30 pointer-events-none" />

        {/* 声のビジュアライザー */}
        <VoiceVisualizer
          isActive={battleSubPhase === 'recording'}
          analyserData={voiceAnalyserData}
          element={players[currentTurn].kaiju.element}
        />

        {/* パーティクルキャンバス */}
        <ParticleCanvas
          element={attackElement}
          isActive={showParticles}
          intensity={lastAttack?.isCritical ? 3 : 2}
          position={defenderPosition as 'left' | 'right'}
        />

        {/* キャラクター配置 */}
        <div className="relative z-10 flex items-center justify-between w-full px-8 max-w-4xl">
          {/* P1 怪獣 */}
          <div className="relative">
            <AnimatePresence>
              {shoutTranscript && shoutTranscript.turn === 0 && (
                <SpeechBubble
                  text={shoutTranscript.text}
                  side="left"
                  playerName={players[0].name}
                />
              )}
            </AnimatePresence>
            <motion.div
              animate={
                isP0Attacking
                  ? { x: [0, 40, 0] }
                  : lastAttack?.player === 1 && showDamage
                    ? { x: [0, -5, 5, -3, 3, 0] }
                    : { x: 0 }
              }
              transition={
                isP0Attacking ? { duration: 0.4, ease: [0.16, 1, 0.3, 1] } : { duration: 0.3 }
              }
            >
              <KaijuDisplay kaiju={players[0].kaiju} side="left" isAttacking={isP0Attacking} />
            </motion.div>
          </div>

          {/* VS 劇的表示 */}
          <div className="flex flex-col items-center gap-2">
            {/* 上のエネルギーライン */}
            <div
              className="w-px h-16 bg-gradient-to-b from-transparent via-white/30 to-white/60 animate-center-line-energy"
              style={{ color: '#3b82f6' }}
            />
            {/* VS テキスト */}
            <p
              className="text-7xl font-black text-white animate-vs-pulse tracking-widest"
              style={{
                textShadow: '0 0 30px rgba(255,255,255,0.5), 0 0 60px rgba(59,130,246,0.3)',
              }}
            >
              {MESSAGES.battle_vs}
            </p>
            <p
              className="text-2xl font-bold text-white/40 tracking-[0.5em]"
              style={{ fontFamily: 'var(--font-noto-sans-jp)' }}
            >
              対
            </p>
            {/* 下のエネルギーライン */}
            <div
              className="w-px h-16 bg-gradient-to-t from-transparent via-white/30 to-white/60 animate-center-line-energy"
              style={{ color: '#3b82f6' }}
            />
          </div>

          {/* P2 怪獣 */}
          <div className="relative">
            <AnimatePresence>
              {shoutTranscript && shoutTranscript.turn === 1 && (
                <SpeechBubble
                  text={shoutTranscript.text}
                  side="right"
                  playerName={players[1].name}
                />
              )}
            </AnimatePresence>
            <motion.div
              animate={
                isP1Attacking
                  ? { x: [0, -40, 0] }
                  : lastAttack?.player === 0 && showDamage
                    ? { x: [0, -5, 5, -3, 3, 0] }
                    : { x: 0 }
              }
              transition={
                isP1Attacking ? { duration: 0.4, ease: [0.16, 1, 0.3, 1] } : { duration: 0.3 }
              }
            >
              <KaijuDisplay kaiju={players[1].kaiju} side="right" isAttacking={isP1Attacking} />
            </motion.div>
          </div>
        </div>

        {/* ダメージエフェクト */}
        {showDamage && lastAttack && (
          <DamageEffect
            damage={lastAttack.damage}
            isCritical={lastAttack.isCritical}
            position={lastAttack.player === 0 ? 'right' : 'left'}
            element={players[lastAttack.player].kaiju.element}
            attackName={lastAttack.attackName}
          />
        )}
      </motion.div>

      {/* === BOTTOM ZONE: アクション === */}
      <div className="relative z-10 flex flex-col items-center gap-3 px-4 pb-4 pt-2">
        {/* ターン表示 + 録音ボタン / AIインジケータ */}
        <TurnIndicator playerName={players[currentTurn].name} subPhase={battleSubPhase} />
        {isAITurn ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center gap-2 py-4"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-12 h-12 border-3 border-white/20 border-t-amber-400 rounded-full"
            />
            <p className="text-sm text-amber-400 font-mono animate-pulse">
              {MESSAGES.battle_aiThinking}
            </p>
          </motion.div>
        ) : (
          <VoiceRecorder
            onRecordingStart={onStartRecording}
            onRecordingComplete={onShout}
            isDisabled={!canRecord}
            onAnalyserUpdate={handleAnalyserUpdate}
          />
        )}

        {/* バトルログ */}
        <div className="w-full max-w-2xl">
          <BattleLog logs={battleLog} />
        </div>
      </div>
    </div>
  );
}
