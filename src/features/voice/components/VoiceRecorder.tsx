'use client';

import { useRef, useEffect, useMemo } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useVoiceCapture } from '@/features/voice/hooks/useVoiceCapture';
import { RECORDING_DURATION_MS } from '@/shared/constants/kaiju-data';
import { MESSAGES } from '@/shared/constants/messages';

interface VoiceRecorderProps {
  onRecordingStart?: () => void;
  onRecordingComplete: (blob: Blob) => void;
  isDisabled: boolean;
  /** 録音中のanalyserDataを親に通知 */
  onAnalyserUpdate?: (data: Uint8Array | null) => void;
}

/**
 * 音声録音コンポーネント
 * 大きな円形ボタンでマイク録音を制御し、音声波形をCanvas描画する
 */
export function VoiceRecorder({
  onRecordingStart,
  onRecordingComplete,
  isDisabled,
  onAnalyserUpdate,
}: VoiceRecorderProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { startRecording, isRecording, analyserData, liveTranscript, error } =
    useVoiceCapture(onRecordingComplete);

  /** analyserData から 0-1 の powerLevel を計算 */
  const powerLevel = useMemo(() => {
    if (!analyserData) return 0;
    const sum = analyserData.reduce((acc, val) => acc + val, 0);
    return Math.min(1, sum / (analyserData.length * 128));
  }, [analyserData]);

  /** analyserData 変化時に親コンポーネントに通知 */
  useEffect(() => {
    if (onAnalyserUpdate) {
      onAnalyserUpdate(analyserData);
    }
  }, [analyserData, onAnalyserUpdate]);

  /** powerLevel に応じたリングカラー */
  const ringColor =
    powerLevel < 0.3
      ? '#60a5fa'
      : powerLevel < 0.6
        ? '#22d3ee'
        : powerLevel < 0.8
          ? '#fbbf24'
          : '#ef4444';

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const barWidth = (width / analyserData.length) * 2.5;
    let x = 0;

    for (let i = 0; i < analyserData.length; i++) {
      const barHeight = (analyserData[i] / 255) * height;
      const normalizedVal = analyserData[i] / 255;
      const alpha = 0.4 + normalizedVal * 0.6;

      // 声の大きさで色を変化: 小さい→シアン, 大きい→赤
      const r = Math.round(34 + normalizedVal * (239 - 34));
      const g = Math.round(211 + normalizedVal * (68 - 211));
      const b = Math.round(238 + normalizedVal * (68 - 238));
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;

      const bw = barWidth - 1;
      const bh = barHeight;
      const bx = x;
      const by = height - barHeight;
      const radius = Math.min(bw / 2, 3);

      if (ctx.roundRect) {
        ctx.beginPath();
        ctx.roundRect(bx, by, bw, bh, radius);
        ctx.fill();
      } else {
        ctx.fillRect(bx, by, bw, bh);
      }

      x += barWidth;
    }
  }, [analyserData]);

  const handleClick = async () => {
    if (isDisabled || isRecording) return;
    const success = await startRecording();
    if (success && onRecordingStart) {
      onRecordingStart();
    }
  };

  const progressPercent = isRecording ? 100 : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative flex items-center justify-center">
        {/* SVG パワーリング (録音中のみ表示) */}
        {isRecording && (
          <svg
            width="140"
            height="140"
            viewBox="0 0 140 140"
            className="absolute animate-power-ring-pulse"
            style={{ transition: 'opacity 0.15s ease' }}
          >
            <circle
              cx="70"
              cy="70"
              r="65"
              fill="none"
              stroke={ringColor}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="408"
              strokeDashoffset={408 * (1 - powerLevel)}
              transform="rotate(-90 70 70)"
              style={{ transition: 'stroke-dashoffset 0.05s linear, stroke 0.1s ease' }}
            />
          </svg>
        )}

        <button
          onClick={handleClick}
          disabled={isDisabled || isRecording}
          aria-label={isRecording ? MESSAGES.battle_recording : MESSAGES.battle_shout}
          className={`relative flex items-center justify-center w-28 h-28 rounded-full border-2 transition-all duration-250 cursor-pointer min-h-[44px] min-w-[44px] ${
            isRecording
              ? 'border-red-500 bg-red-500/20 animate-glow-pulse'
              : isDisabled
                ? 'border-white/20 bg-white/5 cursor-not-allowed opacity-50'
                : 'border-cyan-400/50 bg-cyan-400/10 hover:bg-cyan-400/20 hover:border-cyan-400/80 animate-glow-pulse'
          }`}
          style={
            isRecording
              ? {
                  boxShadow: `0 0 ${40 + powerLevel * 60}px rgba(239, 68, 68, ${0.3 + powerLevel * 0.4})`,
                }
              : !isDisabled
                ? { boxShadow: '0 0 20px rgba(34, 211, 238, 0.3)' }
                : {}
          }
        >
          {isRecording ? (
            <Mic size={44} className="text-red-400 animate-pulse" />
          ) : (
            <MicOff size={44} className={isDisabled ? 'text-white/20' : 'text-foreground'} />
          )}
        </button>

        {isRecording && (
          <div
            className="absolute -inset-2 rounded-full border-2 border-red-500/50 animate-ping"
            style={{ animationDuration: `${RECORDING_DURATION_MS / 1000}s` }}
          />
        )}
      </div>

      <canvas
        ref={canvasRef}
        width={280}
        height={60}
        aria-label="音声波形ビジュアライザー"
        className={`w-72 rounded transition-opacity duration-250 ${isRecording ? 'opacity-100' : 'opacity-0'}`}
      />

      {/* リアルタイム文字起こし表示（録音中〜AI分析完了まで保持） */}
      {liveTranscript && (
        <div className="w-72 px-3 py-2 rounded-lg backdrop-blur-xl bg-white/5 border border-white/10">
          <p className="text-sm font-bold text-cyan-300 text-center break-all leading-snug">
            「{liveTranscript}」
          </p>
        </div>
      )}

      <p className="text-base font-bold text-muted-foreground text-center h-5">
        {error ? (
          <span className="text-red-400">{error}</span>
        ) : isRecording ? (
          <span className="text-red-400">{MESSAGES.battle_recording}</span>
        ) : isDisabled ? (
          ''
        ) : (
          <span className="text-cyan-400 animate-glow-pulse">タップして叫べ！</span>
        )}
      </p>

      {isRecording && (
        <div className="w-48 h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-red-500 rounded-full"
            style={{
              width: `${progressPercent}%`,
              transition: `width ${RECORDING_DURATION_MS}ms linear`,
            }}
          />
        </div>
      )}
    </div>
  );
}
