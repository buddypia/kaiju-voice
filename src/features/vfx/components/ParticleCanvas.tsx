'use client';

import { useEffect, useRef } from 'react';
import type { KaijuElement } from '@/features/battle/types/battle';
import { ELEMENT_STYLES } from '@/shared/lib/design-tokens';

interface ParticleCanvasProps {
  /** 攻撃属性 */
  element: KaijuElement;
  /** エフェクト発火トリガー */
  isActive: boolean;
  /** パーティクル量 (1-3, default 2) */
  intensity?: number;
  /** エフェクト発生位置 */
  position: 'left' | 'right';
}

/** パーティクルの内部状態 */
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;
  rotation: number;
  rotationSpeed: number;
  type: KaijuElement;
}

/** 属性別パーティクル生成 */
function createParticle(
  element: KaijuElement,
  canvasWidth: number,
  canvasHeight: number,
  position: 'left' | 'right',
): Particle {
  const style = ELEMENT_STYLES[element];
  const lifespan = 0.5 + Math.random() * 0.5;
  const baseX = position === 'left' ? canvasWidth * 0.25 : canvasWidth * 0.75;
  const baseY = canvasHeight * 0.5;

  const common = {
    life: lifespan,
    maxLife: lifespan,
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.2,
    type: element,
  };

  switch (element) {
    case 'fire':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 80,
        y: baseY + (Math.random() - 0.5) * 60,
        vx: (Math.random() - 0.5) * 2,
        vy: -(2 + Math.random() * 3),
        size: 4 + Math.random() * 8,
        color: Math.random() > 0.5 ? style.primary : '#f97316',
      };
    case 'ice':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 100,
        y: baseY - 60 + Math.random() * 40,
        vx: (Math.random() - 0.5) * 1.5,
        vy: 1 + Math.random() * 2,
        size: 5 + Math.random() * 7,
        color: style.primary,
      };
    case 'thunder':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 60,
        y: baseY + (Math.random() - 0.5) * 80,
        vx: (Math.random() - 0.5) * 8,
        vy: (Math.random() - 0.5) * 8,
        size: 2 + Math.random() * 4,
        color: style.primary,
        life: 0.1 + Math.random() * 0.25,
        maxLife: 0.1 + Math.random() * 0.25,
      };
    case 'earth':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 80,
        y: baseY + 40,
        vx: (Math.random() - 0.5) * 4,
        vy: -(3 + Math.random() * 4),
        size: 6 + Math.random() * 8,
        color: style.primary,
      };
    case 'void':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 60,
        y: baseY + (Math.random() - 0.5) * 60,
        vx: 0,
        vy: 0,
        size: 10 + Math.random() * 20,
        color: style.primary,
        life: 0.6 + Math.random() * 0.4,
        maxLife: 0.6 + Math.random() * 0.4,
      };
    case 'light':
      return {
        ...common,
        x: baseX + (Math.random() - 0.5) * 80,
        y: baseY + (Math.random() - 0.5) * 60,
        vx: (Math.random() - 0.5) * 3,
        vy: -(1 + Math.random() * 3),
        size: 3 + Math.random() * 6,
        color: style.primary,
      };
  }
}

/** 各属性のパーティクル描画 */
function drawParticle(ctx: CanvasRenderingContext2D, p: Particle): void {
  const alpha = p.life / p.maxLife;
  ctx.save();
  ctx.globalAlpha = alpha;

  switch (p.type) {
    case 'fire': {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 12;
      ctx.shadowColor = p.color;
      ctx.fill();
      break;
    }
    case 'ice': {
      // 六角形
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i;
        const r = p.size * (0.5 + alpha * 0.5);
        if (i === 0) ctx.moveTo(r * Math.cos(angle), r * Math.sin(angle));
        else ctx.lineTo(r * Math.cos(angle), r * Math.sin(angle));
      }
      ctx.closePath();
      ctx.strokeStyle = p.color;
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 8;
      ctx.shadowColor = p.color;
      ctx.stroke();
      break;
    }
    case 'thunder': {
      // 稲妻の線分
      ctx.strokeStyle = p.color;
      ctx.lineWidth = 2;
      ctx.shadowBlur = 15;
      ctx.shadowColor = p.color;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y - p.size * 3);
      ctx.lineTo(p.x + p.size, p.y);
      ctx.lineTo(p.x - p.size * 0.5, p.y + p.size);
      ctx.lineTo(p.x + p.size * 0.5, p.y + p.size * 3);
      ctx.stroke();
      break;
    }
    case 'earth': {
      // 四角形
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 6;
      ctx.shadowColor = p.color;
      ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
      break;
    }
    case 'void': {
      // リング（収縮・膨張）
      const phase = 1 - alpha;
      const radius = p.size * (0.3 + phase * 0.7);
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.strokeStyle = p.color;
      ctx.lineWidth = 2 + (1 - phase) * 2;
      ctx.shadowBlur = 20;
      ctx.shadowColor = p.color;
      ctx.stroke();
      break;
    }
    case 'light': {
      // 光の粒子（星形）
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 15;
      ctx.shadowColor = p.color;
      ctx.fill();
      break;
    }
  }

  ctx.restore();
}

/**
 * 属性攻撃時のパーティクルエフェクトコンポーネント
 * Canvas 2D API を使用してリアルタイムアニメーションを描画
 */
export function ParticleCanvas({
  element,
  isActive,
  intensity = 2,
  position,
}: ParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);
  const emitUntilRef = useRef<number>(0);
  const isRunningRef = useRef<boolean>(false);
  // 最新 props をループから参照するための ref（effect 内で更新）
  const elementRef = useRef(element);
  const intensityRef = useRef(intensity);
  const positionRef = useRef(position);
  // アニメーションループ関数を ref で保持（自己再帰を避けるため）
  const loopRef = useRef<((timestamp: number) => void) | null>(null);

  // props 変化を effect 内で ref に同期
  useEffect(() => {
    elementRef.current = element;
  }, [element]);

  useEffect(() => {
    intensityRef.current = intensity;
  }, [intensity]);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  // ループ関数を初期化（マウント時のみ）
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    const loop = (timestamp: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const el = elementRef.current;
      const inten = intensityRef.current;
      const pos = positionRef.current;

      const dt = Math.min((timestamp - lastTimeRef.current) / 1000, 0.05);
      lastTimeRef.current = timestamp;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // パーティクル生成（発火中のみ）
      if (timestamp < emitUntilRef.current) {
        const count = inten * 15;
        const perFrame = count / (0.8 * 60);
        const toEmit = Math.floor(perFrame + Math.random());
        for (let i = 0; i < toEmit; i++) {
          particlesRef.current.push(createParticle(el, canvas.width, canvas.height, pos));
        }
      }

      // パーティクル更新・描画
      particlesRef.current = particlesRef.current.filter((p) => {
        p.life -= dt;
        if (p.life <= 0) return false;

        switch (p.type) {
          case 'fire':
            p.vx += (Math.random() - 0.5) * 0.3;
            p.vy -= 0.05;
            break;
          case 'ice':
            p.vy += 0.05;
            break;
          case 'thunder':
            break;
          case 'earth':
            p.vy += 0.15;
            break;
          case 'void':
            break;
        }

        p.x += p.vx;
        p.y += p.vy;
        p.rotation += p.rotationSpeed;

        drawParticle(ctx, p);
        return true;
      });

      if (particlesRef.current.length > 0 || timestamp < emitUntilRef.current) {
        animFrameRef.current = requestAnimationFrame(loop);
      } else {
        isRunningRef.current = false;
        animFrameRef.current = null;
      }
    };

    loopRef.current = loop;
  }, []);

  // isActive 変化時にループを開始
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    if (isActive && !isRunningRef.current && loopRef.current) {
      emitUntilRef.current = performance.now() + 800;
      isRunningRef.current = true;
      lastTimeRef.current = performance.now();
      animFrameRef.current = requestAnimationFrame(loopRef.current);
    }
  }, [isActive]);

  // キャンバスリサイズ対応 + クリーンアップ
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
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    />
  );
}
