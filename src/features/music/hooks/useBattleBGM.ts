'use client';

import { useRef } from 'react';

/** バトルBGM管理フック */
export function useBattleBGM() {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const startBGM = async (element1: string, element2: string) => {
    try {
      const res = await fetch('/api/music/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          battleIntensity: 'medium',
          element1,
          element2,
          phase: 'battle',
        }),
      });
      const data = await res.json();
      if (data.audioUrl) {
        const audio = new Audio(data.audioUrl);
        audio.loop = true;
        audio.volume = 0.3;
        await audio.play();
        audioRef.current = audio;
      }
    } catch (err) {
      console.error('BGM生成失敗:', err);
    }
  };

  const stopBGM = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  };

  return { startBGM, stopBGM };
}
