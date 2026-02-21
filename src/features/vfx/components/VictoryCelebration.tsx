'use client';

import { useEffect, useRef } from 'react';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface VictoryCelebrationProps {
  /** エフェクト発火トリガー */
  isActive: boolean;
  /** 勝者の属性 */
  winnerElement: KaijuElement;
}

/** コンフェティの内部状態 */
interface Confetti {
  x: number;
  y: number;
  vx: number;
  vy: number;
  rotation: number;
  rotationSpeed: number;
  width: number;
  height: number;
  color: string;
  gravity: number;
  swing: number;
  swingSpeed: number;
  swingOffset: number;
}

const CONFETTI_COLORS_EXTRA = ['#fbbf24', '#ffffff'];

/** コンフェティ1個を生成 */
function createConfetti(canvasWidth: number, elementColor: string): Confetti {
  const colors = [elementColor, ...CONFETTI_COLORS_EXTRA];
  return {
    x: Math.random() * canvasWidth,
    y: -20,
    vx: (Math.random() - 0.5) * 2,
    vy: 1 + Math.random() * 3,
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.15,
    width: 8 + Math.random() * 10,
    height: 4 + Math.random() * 6,
    color: colors[Math.floor(Math.random() * colors.length)],
    gravity: 0.05 + Math.random() * 0.05,
    swing: 0,
    swingSpeed: 0.02 + Math.random() * 0.03,
    swingOffset: Math.random() * Math.PI * 2,
  };
}

/**
 * 勝利時のコンフェティ祝福エフェクト
 * Canvas 2D API を使って勝者属性カラーのコンフェティを降らせる
 */
export function VictoryCelebration({ isActive, winnerElement }: VictoryCelebrationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const confettiRef = useRef<Confetti[]>([]);
  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);
  const emitIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isRunningRef = useRef<boolean>(false);
  // 最新のエレメントカラーをループから参照するための ref（effect 内で更新）
  const elementColorRef = useRef(ELEMENT_STYLES[winnerElement].primary);
  // アニメーションループ関数を ref で保持
  const loopRef = useRef<((timestamp: number) => void) | null>(null);

  // winnerElement 変化を effect 内で ref に同期
  useEffect(() => {
    elementColorRef.current = ELEMENT_STYLES[winnerElement].primary;
  }, [winnerElement]);

  // ループ関数を初期化（マウント時のみ）
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    const loop = (timestamp: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dt = Math.min((timestamp - lastTimeRef.current) / 1000, 0.05);
      lastTimeRef.current = timestamp;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // コンフェティ更新・描画
      confettiRef.current = confettiRef.current.filter((c) => {
        // 物理演算: 重力 + 横揺れ
        c.swing += c.swingSpeed;
        c.vx += Math.sin(c.swing + c.swingOffset) * 0.08;
        c.vy += c.gravity;
        c.x += c.vx;
        c.y += c.vy * (dt * 60);
        c.rotation += c.rotationSpeed;

        // 画面下端を超えたら削除
        if (c.y > canvas.height + 30) return false;

        ctx.save();
        ctx.translate(c.x, c.y);
        ctx.rotate(c.rotation);
        ctx.fillStyle = c.color;
        ctx.globalAlpha = 0.85;
        ctx.fillRect(-c.width / 2, -c.height / 2, c.width, c.height);
        ctx.restore();

        return true;
      });

      animFrameRef.current = requestAnimationFrame(loop);
    };

    loopRef.current = loop;
  }, []);

  // アニメーションループ開始・停止
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    if (isActive) {
      // アニメーションループ開始
      if (!isRunningRef.current && loopRef.current) {
        isRunningRef.current = true;
        lastTimeRef.current = performance.now();
        animFrameRef.current = requestAnimationFrame(loopRef.current);
      }

      // 0.5秒間隔でコンフェティを50個追加（最大200個）
      emitIntervalRef.current = setInterval(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        if (confettiRef.current.length >= 200) return;

        const toAdd = Math.min(50, 200 - confettiRef.current.length);
        for (let i = 0; i < toAdd; i++) {
          confettiRef.current.push(createConfetti(canvas.width, elementColorRef.current));
        }
      }, 500);
    } else {
      // 停止: インターバルをクリア（残コンフェティは降り切るまで継続）
      if (emitIntervalRef.current !== null) {
        clearInterval(emitIntervalRef.current);
        emitIntervalRef.current = null;
      }
    }

    return () => {
      if (emitIntervalRef.current !== null) {
        clearInterval(emitIntervalRef.current);
        emitIntervalRef.current = null;
      }
    };
  }, [isActive]);

  // コンポーネントアンマウント時のクリーンアップ
  useEffect(() => {
    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
      if (emitIntervalRef.current !== null) {
        clearInterval(emitIntervalRef.current);
      }
    };
  }, []);

  // キャンバスリサイズ対応
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 40,
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    />
  );
}
