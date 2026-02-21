'use client';

import { useEffect, useRef } from 'react';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface VoiceVisualizerProps {
  /** 録音中かどうか */
  isActive: boolean;
  /** Web Audio API の AnalyserNode の周波数データ (Uint8Array) */
  analyserData: Uint8Array | null;
  /** 現在のプレイヤーの属性（色に使用） */
  element: KaijuElement;
}

/**
 * 録音中の声をリアルタイムで可視化する全画面キャンバスエフェクト。
 * Canvas 2D API と requestAnimationFrame でループ描画する。
 */
export function VoiceVisualizer({ isActive, analyserData, element }: VoiceVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number | null>(null);
  const isRunningRef = useRef<boolean>(false);
  const loopRef = useRef<(() => void) | null>(null);

  // 最新 props をループから参照するための ref
  const isActiveRef = useRef(isActive);
  const analyserDataRef = useRef(analyserData);
  const elementRef = useRef(element);

  // props 変化を ref に同期
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  useEffect(() => {
    analyserDataRef.current = analyserData;
  }, [analyserData]);

  useEffect(() => {
    elementRef.current = element;
  }, [element]);

  // ループ関数をマウント時に一度だけ初期化
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    const loop = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const el = elementRef.current;
      const data = analyserDataRef.current;
      const style = ELEMENT_STYLES[el];

      const w = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      if (data && data.length > 0) {
        // 平均音量を計算
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          sum += data[i];
        }
        const averageVolume = sum / data.length;

        // --- 1. 画面端のグロー脈動 ---
        const edgeAlpha = (averageVolume / 255) * 0.25;
        const edgeWidth = w * 0.15;
        const edgeHeight = h * 0.15;

        // 左端グロー
        const leftGrad = ctx.createLinearGradient(0, 0, edgeWidth, 0);
        leftGrad.addColorStop(0, colorWithAlpha(style.primary, edgeAlpha));
        leftGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = leftGrad;
        ctx.fillRect(0, 0, edgeWidth, h);

        // 右端グロー
        const rightGrad = ctx.createLinearGradient(w, 0, w - edgeWidth, 0);
        rightGrad.addColorStop(0, colorWithAlpha(style.primary, edgeAlpha));
        rightGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = rightGrad;
        ctx.fillRect(w - edgeWidth, 0, edgeWidth, h);

        // 上端グロー
        const topGrad = ctx.createLinearGradient(0, 0, 0, edgeHeight);
        topGrad.addColorStop(0, colorWithAlpha(style.primary, edgeAlpha));
        topGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = topGrad;
        ctx.fillRect(0, 0, w, edgeHeight);

        // 下端グロー
        const bottomGrad = ctx.createLinearGradient(0, h, 0, h - edgeHeight);
        bottomGrad.addColorStop(0, colorWithAlpha(style.primary, edgeAlpha));
        bottomGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = bottomGrad;
        ctx.fillRect(0, h - edgeHeight, w, edgeHeight);

        // --- 2. 中央のパルスリング ---
        const centerX = w / 2;
        const centerY = h * 0.75;
        const pulseScale = 0.8 + (averageVolume / 255) * 0.4;
        const pulseRadius = 80 * pulseScale;

        ctx.beginPath();
        ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
        ctx.strokeStyle = colorWithAlpha(style.primary, 0.3);
        ctx.lineWidth = 2;
        ctx.shadowBlur = 0;
        ctx.stroke();

        // --- 3. 円形ビジュアライザー ---
        const barCount = Math.min(Math.floor(data.length / 2), 64);
        const maxBarLength = 120;
        const baseRadius = 80;

        for (let i = 0; i < barCount; i++) {
          const value = data[i];
          const barLength = (value / 255) * maxBarLength;
          const angle = (i / barCount) * Math.PI * 2 - Math.PI / 2;
          const barAlpha = 0.3 + (value / 255) * 0.7;

          const x1 = centerX + Math.cos(angle) * baseRadius;
          const y1 = centerY + Math.sin(angle) * baseRadius;
          const x2 = centerX + Math.cos(angle) * (baseRadius + barLength);
          const y2 = centerY + Math.sin(angle) * (baseRadius + barLength);

          ctx.save();
          ctx.globalAlpha = barAlpha;
          ctx.strokeStyle = style.primary;
          ctx.lineWidth = 3;
          ctx.shadowBlur = 10;
          ctx.shadowColor = style.glow;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
          ctx.restore();
        }
      }

      if (isActiveRef.current) {
        animFrameRef.current = requestAnimationFrame(loop);
      } else {
        // isActive=false 時はループ停止してキャンバスをクリア
        isRunningRef.current = false;
        animFrameRef.current = null;
        const canvas2 = canvasRef.current;
        if (canvas2) {
          const ctx2 = canvas2.getContext('2d');
          if (ctx2) ctx2.clearRect(0, 0, canvas2.width, canvas2.height);
        }
      }
    };

    loopRef.current = loop;
  }, []);

  // isActive 変化時にループ開始/停止
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    if (isActive && !isRunningRef.current && loopRef.current) {
      isRunningRef.current = true;
      animFrameRef.current = requestAnimationFrame(loopRef.current);
    }

    if (!isActive) {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = null;
      }
      isRunningRef.current = false;
      // キャンバスをクリア
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
  }, [isActive]);

  // リサイズ対応 + クリーンアップ
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
        canvas.width = parent.offsetWidth;
        canvas.height = parent.offsetHeight;
      }
    };

    resize();
    const observer = new ResizeObserver(resize);
    if (canvas.parentElement) observer.observe(canvas.parentElement);

    return () => {
      observer.disconnect();
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 5,
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    />
  );
}

/** 16進カラーにアルファ値を適用したrgba文字列を返すユーティリティ */
function colorWithAlpha(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
