'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import type { CommentaryEvent, CommentaryState } from '../types';

/** PCM 16bit音声をデコードして AudioContext で再生する */
async function playPCMAudio(base64Data: string, sampleRate: number = 24000): Promise<void> {
  const binaryStr = atob(base64Data);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }

  const int16 = new Int16Array(bytes.buffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }

  const ctx = new AudioContext({ sampleRate });
  const buffer = ctx.createBuffer(1, float32.length, sampleRate);
  buffer.getChannelData(0).set(float32);

  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(ctx.destination);

  return new Promise((resolve) => {
    source.onended = () => {
      ctx.close();
      resolve();
    };
    source.start();
  });
}

/**
 * AI実況解説フック
 * テキストストリーミング + Live API音声生成を並列実行
 * Live API失敗時はブラウザTTSにフォールバック
 */
export function useCommentary(): {
  commentary: CommentaryState;
  generateCommentary: (event: CommentaryEvent) => Promise<void>;
  stopSpeaking: () => void;
} {
  const [commentary, setCommentary] = useState<CommentaryState>({
    text: '',
    isLoading: false,
    isSpeaking: false,
    isLiveVoice: false,
  });

  const queueRef = useRef<CommentaryEvent[]>([]);
  const isProcessingRef = useRef(false);
  const speechSupportedRef = useRef<boolean>(false);
  const unmountedRef = useRef(false);
  /** Live API利用可能フラグ (初回失敗で無効化) */
  const liveApiEnabledRef = useRef(true);

  useEffect(() => {
    speechSupportedRef.current = typeof window !== 'undefined' && 'speechSynthesis' in window;
    return () => {
      unmountedRef.current = true;
      if (speechSupportedRef.current) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  /** フォールバック: SpeechSynthesis で読み上げ */
  const speakFallback = useCallback((text: string): Promise<void> => {
    return new Promise((resolve) => {
      if (!speechSupportedRef.current || unmountedRef.current) {
        resolve();
        return;
      }
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ja-JP';
      utterance.rate = 1.3;
      utterance.pitch = 1.1;

      utterance.onend = () => {
        if (!unmountedRef.current) {
          setCommentary((prev) => ({ ...prev, isSpeaking: false, isLiveVoice: false }));
        }
        resolve();
      };
      utterance.onerror = () => {
        if (!unmountedRef.current) {
          setCommentary((prev) => ({ ...prev, isSpeaking: false, isLiveVoice: false }));
        }
        resolve();
      };

      if (!unmountedRef.current) {
        setCommentary((prev) => ({ ...prev, isSpeaking: true }));
      }
      window.speechSynthesis.speak(utterance);
    });
  }, []);

  /** Live API で音声を取得して再生 */
  const speakLive = useCallback(async (event: CommentaryEvent): Promise<boolean> => {
    if (!liveApiEnabledRef.current) return false;

    try {
      const res = await fetch('/api/commentary/live', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      });

      if (!res.ok) {
        console.log('Live API returned non-ok, disabling for session');
        liveApiEnabledRef.current = false;
        return false;
      }

      const data = await res.json();
      if (!data.audio || unmountedRef.current) return false;

      if (!unmountedRef.current) {
        setCommentary((prev) => ({ ...prev, isSpeaking: true, isLiveVoice: true }));
      }

      await playPCMAudio(data.audio, 24000);

      if (!unmountedRef.current) {
        setCommentary((prev) => ({ ...prev, isSpeaking: false, isLiveVoice: false }));
      }

      return true;
    } catch (e) {
      console.log('Live API speech error, falling back to TTS:', e);
      liveApiEnabledRef.current = false;
      return false;
    }
  }, []);

  /** テキストストリーミング取得 + 音声再生 */
  const processEvent = useCallback(
    async (event: CommentaryEvent): Promise<void> => {
      if (unmountedRef.current) return;

      setCommentary({ text: '', isLoading: true, isSpeaking: false, isLiveVoice: false });

      let fullText = '';

      // テキストストリーミングと Live API音声を並列実行
      const textPromise = (async () => {
        try {
          const res = await fetch('/api/commentary/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(event),
          });

          if (!res.ok || !res.body) {
            throw new Error(`Commentary API error: ${res.status}`);
          }

          if (!unmountedRef.current) {
            setCommentary((prev) => ({ ...prev, isLoading: false }));
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder();

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (unmountedRef.current) {
              await reader.cancel();
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            const captured = fullText;
            setCommentary((prev) => ({
              ...prev,
              text: captured,
              isLoading: false,
            }));
          }
        } catch (e) {
          console.log('Commentary text stream error:', e);
          if (!unmountedRef.current) {
            setCommentary({ text: '', isLoading: false, isSpeaking: false, isLiveVoice: false });
          }
        }
      })();

      const audioPromise = speakLive(event);

      // テキストと音声の両方を待つ
      const [, liveSuccess] = await Promise.all([textPromise, audioPromise]);

      // Live API音声が失敗した場合、ブラウザTTSにフォールバック
      if (!liveSuccess && fullText && !unmountedRef.current) {
        await speakFallback(fullText);
      }
    },
    [speakLive, speakFallback],
  );

  /** キューを順番に処理 */
  const processQueue = useCallback(async () => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;

    while (queueRef.current.length > 0 && !unmountedRef.current) {
      const event = queueRef.current.shift()!;
      await processEvent(event);
    }

    isProcessingRef.current = false;
  }, [processEvent]);

  /** 外部からイベントを追加してキュー処理を開始 */
  const generateCommentary = useCallback(
    async (event: CommentaryEvent): Promise<void> => {
      queueRef.current.push(event);
      await processQueue();
    },
    [processQueue],
  );

  /** 音声を停止 */
  const stopSpeaking = useCallback(() => {
    if (speechSupportedRef.current) {
      window.speechSynthesis.cancel();
    }
    setCommentary((prev) => ({ ...prev, isSpeaking: false, isLiveVoice: false }));
  }, []);

  return { commentary, generateCommentary, stopSpeaking };
}
