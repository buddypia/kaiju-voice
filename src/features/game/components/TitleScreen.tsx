'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Flame, Skull, Bot, Users, Info, X, Shield } from 'lucide-react';
import { MESSAGES } from '@/shared/constants/messages';
import type { GameMode } from '@/features/battle/types/battle';

interface TitleScreenProps {
  onStart: (mode: GameMode) => void;
}

/** タイトル画面コンポーネント — 劇的な演出で第一印象を最大化 */
export function TitleScreen({ onStart }: TitleScreenProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showSubtitle, setShowSubtitle] = useState(false);
  const [showManual, setShowManual] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowSubtitle(true), 800);
    return () => clearTimeout(timer);
  }, []);

  /** 背景パーティクルアニメーション */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    interface Ember {
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      alpha: number;
      color: string;
      life: number;
      maxLife: number;
    }

    const embers: Ember[] = [];
    const colors = ['#ef4444', '#22d3ee', '#eab308', '#a855f7', '#84cc16'];

    let animId: number;

    const loop = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 新しい火花を追加
      if (embers.length < 60) {
        const color = colors[Math.floor(Math.random() * colors.length)];
        embers.push({
          x: Math.random() * canvas.width,
          y: canvas.height + 10,
          vx: (Math.random() - 0.5) * 0.8,
          vy: -(0.5 + Math.random() * 1.5),
          size: 1 + Math.random() * 3,
          alpha: 0.3 + Math.random() * 0.5,
          color,
          life: 3 + Math.random() * 4,
          maxLife: 3 + Math.random() * 4,
        });
      }

      for (let i = embers.length - 1; i >= 0; i--) {
        const e = embers[i];
        e.x += e.vx;
        e.y += e.vy;
        e.life -= 0.016;
        e.alpha = (e.life / e.maxLife) * 0.6;

        if (e.life <= 0) {
          embers.splice(i, 1);
          continue;
        }

        ctx.beginPath();
        ctx.arc(e.x, e.y, e.size, 0, Math.PI * 2);
        ctx.fillStyle = e.color;
        ctx.globalAlpha = e.alpha;
        ctx.shadowBlur = 10;
        ctx.shadowColor = e.color;
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;

      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-background vignette">
      {/* 背景パーティクル */}
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" aria-hidden="true" />

      {/* 背景グラデーション */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute inset-0 animate-gradient-shift opacity-30"
          style={{
            background:
              'linear-gradient(135deg, #0b1120 0%, #1e3a5f 25%, #2d1b4e 50%, #1a2332 75%, #0b1120 100%)',
          }}
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.2 }}
          transition={{ duration: 2 }}
          className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, #ef4444 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.2 }}
          transition={{ duration: 2, delay: 0.5 }}
          className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, #a855f7 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.1 }}
          transition={{ duration: 2.5, delay: 0.3 }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
          style={{
            background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
      </div>

      {/* 怪獣シルエット (左右) */}
      <motion.div
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 0.1, x: 0 }}
        transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
        className="absolute left-4 bottom-0 select-none pointer-events-none"
        aria-hidden="true"
      >
        <Flame size={280} strokeWidth={0.5} className="text-fire" />
      </motion.div>
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 0.1, x: 0 }}
        transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
        className="absolute right-4 bottom-0 select-none pointer-events-none"
        style={{ transform: 'scaleX(-1)' }}
        aria-hidden="true"
      >
        <Skull size={280} strokeWidth={0.5} className="text-fire" />
      </motion.div>

      {/* コンテンツ */}
      <div className="relative z-10 flex flex-col items-center gap-8">
        {/* タイトルロゴ — 文字ごとのスタッガーアニメーション */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex overflow-hidden">
            {'KAIJU VOICE'.split('').map((char, i) => (
              <motion.span
                key={i}
                initial={{ y: 80, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{
                  delay: 0.1 + i * 0.05,
                  duration: 0.6,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="text-9xl font-bold tracking-widest select-none text-shimmer"
              >
                {char === ' ' ? '\u00A0' : char}
              </motion.span>
            ))}
          </div>

          {showSubtitle && (
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="text-4xl font-semibold tracking-[0.3em] text-foreground text-glow font-noto-sans-jp"
            >
              {MESSAGES.game_subtitle}
            </motion.p>
          )}
        </div>

        {/* 特徴バッジ */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.5 }}
          className="flex gap-3"
        >
          {['Gemini AI', 'Live API', 'Imagen 3', 'Lyria BGM'].map((tech) => (
            <span
              key={tech}
              className="px-3 py-1 text-xs font-mono text-white/50 border border-white/10 rounded-full backdrop-blur-xl bg-white/5 hover:bg-white/10 hover:border-white/30 hover:shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-all duration-250"
            >
              {tech}
            </span>
          ))}
        </motion.div>

        {/* スタートボタン */}
        <div className="flex flex-col items-center gap-4 mt-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex gap-4"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onStart('vsai')}
              className="flex flex-col items-center gap-2 px-10 py-5 rounded-xl text-white btn-gradient-border animate-glow-pulse-btn cursor-pointer"
            >
              <Bot size={28} aria-hidden="true" />
              <span className="text-xl font-bold">{MESSAGES.game_mode_vsai}</span>
              <span className="text-xs text-white/60">{MESSAGES.game_mode_vsai_desc}</span>
            </motion.button>

            {/* ヒーロー VS 怪獣ボタン — アンバーアクセントで差別化 */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onStart('hero_vs_kaiju')}
              className="flex flex-col items-center gap-2 px-10 py-5 rounded-xl text-white btn-base border cursor-pointer"
              style={{
                borderColor: '#fbbf2480',
                background: 'rgba(251, 191, 36, 0.08)',
                boxShadow: '0 0 20px rgba(251, 191, 36, 0.15)',
              }}
            >
              <Shield size={28} aria-hidden="true" style={{ color: '#fbbf24' }} />
              <span className="text-xl font-bold" style={{ color: '#fbbf24' }}>
                {MESSAGES.game_mode_hero}
              </span>
              <span className="text-xs text-white/60">{MESSAGES.game_mode_hero_desc}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onStart('pvp')}
              className="flex flex-col items-center gap-2 px-10 py-5 rounded-xl text-white btn-base border border-white/20 bg-white/5 hover:bg-white/10 cursor-pointer"
            >
              <Users size={28} aria-hidden="true" />
              <span className="text-xl font-bold">{MESSAGES.game_mode_pvp}</span>
              <span className="text-xs text-white/60">{MESSAGES.game_mode_pvp_desc}</span>
            </motion.button>
          </motion.div>

          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2, duration: 0.5 }}
            onClick={() => setShowManual(true)}
            className="flex items-center gap-2 px-6 py-2 text-sm font-medium text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 rounded-full transition-colors"
          >
            <Info size={16} />
            遊び方・マニュアル
          </motion.button>
        </div>

        {/* ヒントテキスト */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.4 }}
          transition={{ delay: 1.5, duration: 0.5 }}
          className="text-sm text-foreground/40 font-mono"
        >
          マイクに向かって叫んで怪獣を操れ
        </motion.p>
      </div>

      {/* マニュアルモーダル */}
      <AnimatePresence>
        {showManual && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="relative w-full max-w-lg p-6 bg-slate-900 border border-white/20 rounded-2xl shadow-2xl"
            >
              <button
                onClick={() => setShowManual(false)}
                className="absolute top-4 right-4 p-2 text-white/50 hover:text-white hover:bg-white/10 rounded-full transition-colors"
              >
                <X size={20} />
              </button>

              <h2 className="text-2xl font-bold text-amber-400 mb-4 flex items-center gap-2">
                <Info className="text-amber-400" />
                ゲームの遊び方
              </h2>

              <div className="space-y-4 text-sm text-white/80 leading-relaxed">
                <section>
                  <h3 className="text-lg font-bold text-white mb-1 border-b border-white/10 pb-1">
                    1. 音声でバトル！
                  </h3>
                  <p>
                    このゲームはあなたの「声」が攻撃力になります。自分のターンが来たらマイクボタンを押し、思いの丈を叫んでください。
                  </p>
                </section>

                <section>
                  <h3 className="text-lg font-bold text-white mb-1 border-b border-white/10 pb-1">
                    2. AIによる判定（考え方）
                  </h3>
                  <p>AI審判があなたの声を以下の3つの軸で分析し、ダメージを決定します：</p>
                  <ul className="list-disc list-inside pl-4 mt-2 space-y-1 text-white/70">
                    <li>
                      <strong className="text-white">迫力 (Intensity)</strong>:
                      声の大きさ、エネルギー。大きく力強いほど高得点。
                    </li>
                    <li>
                      <strong className="text-white">感情 (Emotion)</strong>:
                      込められた気持ちの強さ。
                    </li>
                    <li>
                      <strong className="text-white">創造性 (Creativity)</strong>:
                      言葉のユニークさ。ただ叫ぶより、技名を叫んだり、英語を交えたりすると高得点！
                    </li>
                  </ul>
                </section>

                <section>
                  <h3 className="text-lg font-bold text-white mb-1 border-b border-white/10 pb-1">
                    3. クリティカルヒット
                  </h3>
                  <p>
                    「創造性」が80を超えると、一定確率でダメージが
                    <strong className="text-amber-400">2倍（クリティカル）</strong>
                    になります！面白い叫び声を工夫してみましょう。
                  </p>
                </section>

                <section>
                  <h3 className="text-lg font-bold text-white mb-1 border-b border-white/10 pb-1">
                    4. 叫び方の例
                  </h3>
                  <p className="mb-2">こんな風に叫んでみよう！</p>
                  <div className="space-y-2 text-white/70">
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 text-cyan-400 font-bold text-xs mt-0.5">基本</span>
                      <p>&quot;くらえぇぇぇ！&quot; &quot;ぶっ飛ばしてやる！&quot;</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 text-violet-400 font-bold text-xs mt-0.5">
                        技名
                      </span>
                      <p>&quot;灼熱の炎よ、すべてを焼き尽くせ！&quot;</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 text-amber-400 font-bold text-xs mt-0.5">混在</span>
                      <p>
                        &quot;Burn to ashes! 灰になれぇぇ！&quot;{' '}
                        <span className="text-amber-400/80 text-xs">← 日英混在で1.2倍!</span>
                      </p>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 text-rose-400 font-bold text-xs mt-0.5">必殺</span>
                      <p>&quot;Thunder god! 万雷の神、ボルタリオンストライク！&quot;</p>
                    </div>
                  </div>
                </section>

                <section>
                  <h3 className="text-lg font-bold text-white mb-1 border-b border-white/10 pb-1">
                    5. バトルログの確認
                  </h3>
                  <p>
                    バトル画面のログには、AIがあなたの声をどう評価したか（迫力・創造性・感情のスコア）が表示されます。
                  </p>
                </section>
              </div>

              <div className="mt-6 flex justify-center">
                <button
                  onClick={() => setShowManual(false)}
                  className="px-8 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-bold transition-colors"
                >
                  閉じる
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
