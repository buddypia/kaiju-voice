'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';
import type {
  Player,
  AttackResult,
  VoiceAnalysis,
  BattleLogEntry,
  BattleSubPhase,
  GameMode,
} from '@/features/battle/types/battle';
import { calculateDamage } from '@/features/battle/hooks/useBattleEngine';
import { BattleArena } from '@/features/battle/components/BattleArena';
import { AttackSequence } from '@/features/battle/components/AttackSequence';
import { useKaijuGeneration } from '@/features/kaiju/hooks/useKaijuGeneration';
import { useBattleBGM } from '@/features/music/hooks/useBattleBGM';
import { useCommentary } from '@/features/commentary';
import type { CommentaryEvent } from '@/features/commentary';
import { useAIOpponent } from '@/features/ai-opponent';
import { UltimateCutIn, KnockOutEffect } from '@/features/vfx';

interface BattleScreenProps {
  players: [Player, Player];
  currentTurn: 0 | 1;
  roundNumber: number;
  lastAttack: AttackResult | null;
  battleSubPhase: BattleSubPhase;
  battleLog: BattleLogEntry[];
  gameMode: GameMode;
  onStartRecording: () => void;
  onSetAnalyzing: () => void;
  onSetAIThinking: () => void;
  onApplyAttack: (attack: AttackResult) => void;
  onNextTurn: () => void;
  updateKaijuImage: (playerId: 0 | 1, imageUrl: string) => void;
}

/** バトル画面コンポーネント */
export function BattleScreen({
  players,
  currentTurn,
  roundNumber,
  lastAttack,
  battleSubPhase,
  battleLog,
  gameMode,
  onStartRecording,
  onSetAnalyzing,
  onSetAIThinking,
  onApplyAttack,
  onNextTurn,
  updateKaijuImage,
}: BattleScreenProps) {
  const { generateImage } = useKaijuGeneration();
  const { startBGM, stopBGM } = useBattleBGM();
  const { commentary, generateCommentary, stopSpeaking } = useCommentary();
  const { generateAIAttack, prefetchAIAttack, consumePrefetched, isPrefetched } = useAIOpponent();
  const bgmStartedRef = useRef(false);
  const imageGeneratedRef = useRef(false);
  const commentaryInitRef = useRef(false);
  const aiTurnProcessingRef = useRef(false);

  /** 攻撃シーケンス状態 */
  const [pendingAttack, setPendingAttack] = useState<AttackResult | null>(null);
  const [showSequence, setShowSequence] = useState(false);
  const [showCutIn, setShowCutIn] = useState(false);
  const [showKO, setShowKO] = useState(false);
  const pendingTurnRef = useRef<0 | 1>(0);
  const koWinnerElementRef = useRef(players[0].kaiju.element);

  /** 音声認識テキスト表示用 */
  const [shoutTranscript, setShoutTranscript] = useState<{ text: string; turn: 0 | 1 } | null>(
    null,
  );
  const shoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** バトル開始時にBGM・怪獣画像・開幕実況を非同期生成 */
  useEffect(() => {
    if (!bgmStartedRef.current) {
      bgmStartedRef.current = true;
      startBGM(players[0].kaiju.element, players[1].kaiju.element);
    }

    if (!imageGeneratedRef.current) {
      imageGeneratedRef.current = true;
      generateImage(players[0].kaiju).then((url) => {
        if (url) updateKaijuImage(0, url);
      });
      generateImage(players[1].kaiju).then((url) => {
        if (url) updateKaijuImage(1, url);
      });
    }

    if (!commentaryInitRef.current) {
      commentaryInitRef.current = true;
      generateCommentary({
        event: 'battle_start',
        attacker: players[0].kaiju.nameJa,
        defender: players[1].kaiju.nameJa,
        element1: players[0].kaiju.element,
        element2: players[1].kaiju.element,
      });
    }

    return () => {
      stopBGM();
      stopSpeaking();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** VS AI / ヒーロー VS 怪獣モード: プレイヤーの録音開始時にAI攻撃をプリフェッチ */
  useEffect(() => {
    if ((gameMode !== 'vsai' && gameMode !== 'hero_vs_kaiju') || currentTurn !== 0) return;
    if (battleSubPhase !== 'recording') return;

    const aiPlayer = players[1];
    const humanPlayer = players[0];

    prefetchAIAttack({
      aiKaiju: {
        name: aiPlayer.kaiju.name,
        nameJa: aiPlayer.kaiju.nameJa,
        element: aiPlayer.kaiju.element,
      },
      opponentKaiju: {
        name: humanPlayer.kaiju.name,
        nameJa: humanPlayer.kaiju.nameJa,
        element: humanPlayer.kaiju.element,
      },
      aiHp: aiPlayer.hp,
      opponentHp: humanPlayer.hp,
      maxHp: aiPlayer.maxHp,
      roundNumber: roundNumber + 1,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameMode, currentTurn, battleSubPhase]);

  /** VS AI / ヒーロー VS 怪獣モード: AIターンの自動攻撃（プリフェッチ優先）
   * NOTE: battleSubPhase を dependency から除外。
   * onSetAIThinking() が battleSubPhase を 'ai_thinking' に変更すると
   * useEffect が再実行され cleanup で setTimeout がキャンセルされるため。
   * NEXT_TURN は currentTurn と battleSubPhase を同時に更新するので
   * currentTurn === 1 時点で battleSubPhase === 'ready' は保証される。
   */
  useEffect(() => {
    if (
      (gameMode !== 'vsai' && gameMode !== 'hero_vs_kaiju') ||
      currentTurn !== 1 ||
      battleSubPhase !== 'ready'
    )
      return;
    if (aiTurnProcessingRef.current) return;

    aiTurnProcessingRef.current = true;
    onSetAIThinking();

    const aiPlayer = players[1];
    const humanPlayer = players[0];

    // プリフェッチ結果があるかチェック（消費はまだしない）
    const hasPrefetched = isPrefetched;
    // 構えアニメーション: プリフェッチ済みなら短め、なければ従来通り
    const delay = hasPrefetched ? 300 : 800;

    const timer = setTimeout(async () => {
      try {
        // プリフェッチ結果を優先使用、なければライブ生成
        const cached = consumePrefetched();
        const analysis =
          cached ??
          (await generateAIAttack({
            aiKaiju: {
              name: aiPlayer.kaiju.name,
              nameJa: aiPlayer.kaiju.nameJa,
              element: aiPlayer.kaiju.element,
            },
            opponentKaiju: {
              name: humanPlayer.kaiju.name,
              nameJa: humanPlayer.kaiju.nameJa,
              element: humanPlayer.kaiju.element,
            },
            aiHp: aiPlayer.hp,
            opponentHp: humanPlayer.hp,
            maxHp: aiPlayer.maxHp,
            roundNumber,
          }));

        // AI の叫びを吹き出し表示
        if (analysis.transcript) {
          if (shoutTimerRef.current) clearTimeout(shoutTimerRef.current);
          setShoutTranscript({ text: analysis.transcript, turn: 1 });
          shoutTimerRef.current = setTimeout(() => setShoutTranscript(null), 5000);
        }

        const attackResult = calculateDamage(analysis, aiPlayer, humanPlayer);

        pendingTurnRef.current = 1;
        setPendingAttack(attackResult);
        if (attackResult.voiceAnalysis.attackType === 'ultimate') {
          setShowCutIn(true);
        } else {
          setShowSequence(true);
        }
      } catch (err) {
        console.error('AIターン処理失敗:', err);
        onNextTurn();
      } finally {
        aiTurnProcessingRef.current = false;
      }
    }, delay);

    return () => {
      clearTimeout(timer);
      aiTurnProcessingRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameMode, currentTurn]);

  /** カットイン完了 → 攻撃シーケンスを表示 */
  const handleCutInComplete = useCallback(() => {
    setShowCutIn(false);
    setShowSequence(true);
  }, []);

  /** KO演出完了 → ターン進行 */
  const handleKOComplete = useCallback(() => {
    setShowKO(false);
    onNextTurn();
  }, [onNextTurn]);

  /** 攻撃シーケンス完了後: ダメージ適用 + 実況 + ターン進行 */
  const handleSequenceComplete = useCallback(() => {
    if (!pendingAttack) return;

    const turn = pendingTurnRef.current;
    const attacker = players[turn];
    const defender = players[turn === 0 ? 1 : 0];

    setShowSequence(false);
    onApplyAttack(pendingAttack);

    // AI実況を非同期で生成
    const defenderHpAfter = Math.max(0, defender.hp - pendingAttack.damage);
    const commentaryEvent: CommentaryEvent = {
      event: pendingAttack.isCritical ? 'critical' : 'attack',
      attacker: attacker.kaiju.nameJa,
      defender: defender.kaiju.nameJa,
      attackName: pendingAttack.attackName,
      damage: pendingAttack.damage,
      remainingHp: defenderHpAfter,
      maxHp: defender.maxHp,
    };
    generateCommentary(commentaryEvent);

    if (defenderHpAfter > 0 && defenderHpAfter / defender.maxHp <= 0.3) {
      generateCommentary({
        event: 'low_hp',
        defender: defender.kaiju.nameJa,
        remainingHp: defenderHpAfter,
        maxHp: defender.maxHp,
      });
    }

    if (defenderHpAfter <= 0) {
      generateCommentary({
        event: 'ko',
        winner: attacker.kaiju.nameJa,
        loser: defender.kaiju.nameJa,
        totalRounds: roundNumber,
      });
    }

    setPendingAttack(null);

    if (defenderHpAfter <= 0) {
      // KO演出をダメージアニメーション後に表示
      koWinnerElementRef.current = attacker.kaiju.element;
      setTimeout(() => {
        setShowKO(true);
      }, 1200);
    } else {
      setTimeout(() => {
        onNextTurn();
      }, 2500);
    }
  }, [pendingAttack, players, roundNumber, onApplyAttack, onNextTurn, generateCommentary]);

  /** 叫ぶアクション: 録音完了 → 分析 → スコア表示シーケンス → ダメージ */
  const handleShout = async (audioBlob: Blob) => {
    if (battleSubPhase !== 'recording' && battleSubPhase !== 'ready') return;

    onSetAnalyzing();

    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice.webm');

      const res = await fetch('/api/voice/analyze', {
        method: 'POST',
        body: formData,
      });

      const analysis: VoiceAnalysis = await res.json();

      // 認識テキストを吹き出し表示
      if (analysis.transcript) {
        if (shoutTimerRef.current) clearTimeout(shoutTimerRef.current);
        setShoutTranscript({ text: analysis.transcript, turn: currentTurn });
        shoutTimerRef.current = setTimeout(() => setShoutTranscript(null), 5000);
      }

      const attacker = players[currentTurn];
      const defender = players[currentTurn === 0 ? 1 : 0];
      const attackResult = calculateDamage(analysis, attacker, defender);

      // ダメージを即座に適用せず、攻撃シーケンスを先に表示
      pendingTurnRef.current = currentTurn;
      setPendingAttack(attackResult);
      if (attackResult.voiceAnalysis.attackType === 'ultimate') {
        setShowCutIn(true);
      } else {
        setShowSequence(true);
      }
    } catch (err) {
      console.error('叫び処理失敗:', err);
      onNextTurn();
    }
  };

  const sequenceElement = pendingAttack ? players[pendingAttack.player].kaiju.element : 'fire';

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-background">
      <BattleArena
        players={players}
        currentTurn={currentTurn}
        roundNumber={roundNumber}
        lastAttack={lastAttack}
        battleSubPhase={battleSubPhase}
        battleLog={battleLog}
        gameMode={gameMode}
        onStartRecording={onStartRecording}
        onShout={handleShout}
        commentaryText={commentary.text}
        commentaryIsLoading={commentary.isLoading}
        commentaryIsSpeaking={commentary.isSpeaking}
        commentaryIsLiveVoice={commentary.isLiveVoice}
        shoutTranscript={shoutTranscript}
      />

      {/* 必殺技カットイン演出 */}
      <UltimateCutIn
        isActive={showCutIn}
        kaijuName={pendingAttack ? players[pendingAttack.player].kaiju.nameJa : ''}
        attackName={pendingAttack?.attackName ?? ''}
        element={sequenceElement}
        kaijuImageUrl={pendingAttack ? players[pendingAttack.player].kaiju.imageUrl : null}
        side={pendingAttack?.player === 0 ? 'left' : 'right'}
        onComplete={handleCutInComplete}
      />

      {/* 攻撃分析スコア + 攻撃名表示シーケンス */}
      <AnimatePresence>
        {showSequence && pendingAttack && (
          <AttackSequence
            voiceAnalysis={pendingAttack.voiceAnalysis}
            attackName={pendingAttack.attackName}
            element={sequenceElement}
            isActive={showSequence}
            onSequenceComplete={handleSequenceComplete}
          />
        )}
      </AnimatePresence>

      {/* KO演出 */}
      <KnockOutEffect
        isActive={showKO}
        winnerElement={koWinnerElementRef.current}
        onComplete={handleKOComplete}
      />
    </div>
  );
}
