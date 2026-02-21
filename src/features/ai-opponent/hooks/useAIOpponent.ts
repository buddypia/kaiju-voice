'use client';

import { useCallback, useRef, useState } from 'react';
import type {
  AIAttackRequest,
  AIAttackResponse,
  VoiceAnalysis,
} from '@/features/battle/types/battle';

/** デフォルトのVoiceAnalysis（API失敗時のフォールバック） */
const DEFAULT_VOICE_ANALYSIS: VoiceAnalysis = {
  intensity: 60,
  creativity: 60,
  emotion: 60,
  language: 'ja',
  transcript: 'ガアアアアッ！',
  attackType: 'physical',
};

interface UseAIOpponentReturn {
  /** AI攻撃を生成してVoiceAnalysisとして返す */
  generateAIAttack: (request: AIAttackRequest) => Promise<VoiceAnalysis>;
  /** プレイヤーターン中にAI攻撃を事前生成する */
  prefetchAIAttack: (request: AIAttackRequest) => void;
  /** プリフェッチ済みの攻撃を取得して消費する（なければnull） */
  consumePrefetched: () => VoiceAnalysis | null;
  /** 生成中かどうか */
  isGenerating: boolean;
  /** プリフェッチが完了しているか */
  isPrefetched: boolean;
}

/** API呼び出し共通処理 */
async function fetchAIAttack(
  request: AIAttackRequest,
  signal?: AbortSignal,
): Promise<VoiceAnalysis> {
  const res = await fetch('/api/ai-opponent/attack', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok) {
    console.error(`AI攻撃生成APIエラー: status=${res.status}`);
    return DEFAULT_VOICE_ANALYSIS;
  }

  const response: AIAttackResponse = await res.json();
  console.log(`AI攻撃生成完了: shout="${response.shoutText}", type=${response.attackType}`);

  return {
    intensity: response.intensity,
    creativity: response.creativity,
    emotion: response.emotion,
    language: 'ja',
    transcript: response.shoutText,
    attackType: response.attackType,
  };
}

/**
 * AI対戦相手フック（ハイブリッド方式）
 * プレイヤーターン中にAI攻撃を事前生成し、AIターンで即座に使用する
 */
export function useAIOpponent(): UseAIOpponentReturn {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPrefetched, setIsPrefetched] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const prefetchedRef = useRef<VoiceAnalysis | null>(null);
  const prefetchAbortRef = useRef<AbortController | null>(null);

  /**
   * プレイヤーターン中にAI攻撃を事前生成（バックグラウンド）
   * 現在のHP状態を基に生成し、AIターン開始時に即座に使う
   */
  const prefetchAIAttack = useCallback((request: AIAttackRequest) => {
    // 既にプリフェッチ中なら中断して再開
    if (prefetchAbortRef.current) {
      prefetchAbortRef.current.abort();
    }
    prefetchedRef.current = null;
    setIsPrefetched(false);

    const controller = new AbortController();
    prefetchAbortRef.current = controller;

    console.log(
      `AI攻撃プリフェッチ開始: ${request.aiKaiju.nameJa}, ラウンド${request.roundNumber}`,
    );

    fetchAIAttack(request, controller.signal)
      .then((analysis) => {
        if (!controller.signal.aborted) {
          prefetchedRef.current = analysis;
          setIsPrefetched(true);
          console.log(`AI攻撃プリフェッチ完了: "${analysis.transcript}"`);
        }
      })
      .catch((e) => {
        if (e instanceof Error && e.name !== 'AbortError') {
          console.error('AI攻撃プリフェッチエラー:', e);
        }
      });
  }, []);

  /** プリフェッチ済みの攻撃を取得して消費する */
  const consumePrefetched = useCallback((): VoiceAnalysis | null => {
    const cached = prefetchedRef.current;
    prefetchedRef.current = null;
    setIsPrefetched(false);
    if (cached) {
      console.log('AI攻撃プリフェッチ結果を使用（即座に応答）');
    }
    return cached;
  }, []);

  /** AI攻撃を生成する（プリフェッチが間に合わなかった場合のフォールバック） */
  const generateAIAttack = useCallback(async (request: AIAttackRequest): Promise<VoiceAnalysis> => {
    console.log(
      `AI攻撃生成開始（ライブ）: ${request.aiKaiju.nameJa}, ラウンド${request.roundNumber}`,
    );
    setIsGenerating(true);

    abortControllerRef.current = new AbortController();

    try {
      return await fetchAIAttack(request, abortControllerRef.current.signal);
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        console.log('AI攻撃生成キャンセル');
      } else {
        console.error('AI攻撃生成エラー:', e);
      }
      return DEFAULT_VOICE_ANALYSIS;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  return { generateAIAttack, prefetchAIAttack, consumePrefetched, isGenerating, isPrefetched };
}
