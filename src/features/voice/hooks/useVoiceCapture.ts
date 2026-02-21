'use client';

import { useState, useRef, useCallback } from 'react';
import { RECORDING_DURATION_MS } from '@/shared/constants/kaiju-data';

interface UseVoiceCaptureReturn {
  startRecording: () => Promise<boolean>;
  isRecording: boolean;
  audioBlob: Blob | null;
  analyserData: Uint8Array | null;
  liveTranscript: string;
  error: string | null;
}

/**
 * 音声キャプチャフック
 * マイクから音声を録音し、波形データを提供する
 */
export function useVoiceCapture(onComplete?: (blob: Blob) => void): UseVoiceCaptureReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [analyserData, setAnalyserData] = useState<Uint8Array | null>(null);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const stopRecording = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch((e) => console.error('AudioContext close error:', e));
      audioContextRef.current = null;
    }
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
    setIsRecording(false);
    setAnalyserData(null);
  }, []);

  const startRecording = useCallback(async (): Promise<boolean> => {
    setError(null);
    setAudioBlob(null);
    setLiveTranscript('');
    chunksRef.current = [];

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      console.error('マイクアクセスエラー:', e);
      setError('マイクの使用を許可してください');
      return false;
    }

    try {
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach((track) => track.stop());
        if (onComplete) {
          onComplete(blob);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);

      /** Web Speech API でリアルタイム文字起こし */
      const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognitionCtor) {
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = 'ja-JP';
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.onresult = (event: SpeechRecognitionEvent) => {
          let text = '';
          for (let i = 0; i < event.results.length; i++) {
            text += event.results[i][0].transcript;
          }
          setLiveTranscript(text);
        };
        recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
          console.warn('SpeechRecognition error:', e.error);
        };
        recognition.start();
        recognitionRef.current = recognition;
      }

      /** アニメーションループ: setAnalyserData はフックから安定参照 */
      const localAnalyserRef = analyserRef;
      const localAnimFrameRef = animationFrameRef;

      const loop = () => {
        if (!localAnalyserRef.current) return;
        const dataArray = new Uint8Array(localAnalyserRef.current.frequencyBinCount);
        localAnalyserRef.current.getByteFrequencyData(dataArray);
        setAnalyserData(new Uint8Array(dataArray));
        localAnimFrameRef.current = requestAnimationFrame(loop);
      };

      loop();

      timeoutRef.current = setTimeout(() => {
        stopRecording();
      }, RECORDING_DURATION_MS);
      return true;
    } catch (e) {
      console.error('録音開始エラー:', e);
      setError('録音の開始に失敗しました');
      stream.getTracks().forEach((track) => track.stop());
      return false;
    }
  }, [onComplete, stopRecording]);

  return { startRecording, isRecording, audioBlob, analyserData, liveTranscript, error };
}
