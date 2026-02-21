import { GoogleGenAI } from '@google/genai';

/** 標準Gemini クライアント (音声分析 + 画像生成) */
export const gemini = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY!,
});

/** Lyria RealTime 用クライアント (v1alpha API) */
export const geminiAlpha = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY!,
  httpOptions: { apiVersion: 'v1alpha' },
});
