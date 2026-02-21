import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });

const VOICE_JUDGE_PROMPT = `あなたは「KAIJU VOICE」バトルゲームの審判AIです。
プレイヤーが叫んだ音声を分析し、怪獣の攻撃力を判定してください。

## 判定基準
1. intensity (0-100): 声の大きさ、エネルギー、迫力
2. creativity (0-100): 叫んだ言葉の創造性、ユニークさ、面白さ
3. emotion (0-100): 感情の強さ、込められた気持ち
4. language: 検出された言語 ("ja", "en", "mixed")
5. attackType: 攻撃の種類
   - "physical": 単純な叫び声、シンプルな言葉
   - "special": 技名を叫ぶ、創造的な攻撃名
   - "ultimate": 複数言語混在、詩的、非常に創造的な叫び

## ルール
- 日本語と英語の混在は creativity ボーナス (+10-20)
- 面白い叫び声は creativity と emotion 両方にボーナス
- JSON のみで応答してください`;

const voiceAnalysisSchema = {
  type: 'object',
  required: ['intensity', 'creativity', 'emotion', 'language', 'transcript', 'attackType'],
  properties: {
    intensity: { type: 'number' },
    creativity: { type: 'number' },
    emotion: { type: 'number' },
    language: { type: 'string', enum: ['ja', 'en', 'mixed'] },
    transcript: { type: 'string' },
    attackType: { type: 'string', enum: ['physical', 'special', 'ultimate'] },
  },
};

export async function POST(request: NextRequest) {
  console.log('音声分析開始');
  try {
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File | null;

    if (!audioFile) {
      return NextResponse.json({ error: '音声ファイルが見つかりません' }, { status: 400 });
    }

    console.log(`音声分析: mimeType=${audioFile.type}, size=${audioFile.size}`);

    const arrayBuffer = await audioFile.arrayBuffer();
    const base64Audio = Buffer.from(arrayBuffer).toString('base64');

    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: [
        {
          role: 'user',
          parts: [
            { inlineData: { mimeType: audioFile.type, data: base64Audio } },
            { text: 'この音声を分析して攻撃力を判定してください' },
          ],
        },
      ],
      config: {
        systemInstruction: VOICE_JUDGE_PROMPT,
        responseMimeType: 'application/json',
        responseJsonSchema: voiceAnalysisSchema,
      },
    });

    const text = response.text;
    if (!text) {
      console.error('音声分析: レスポンステキストが空');
      return NextResponse.json({ error: '音声分析の応答が空です' }, { status: 500 });
    }
    console.log(`音声分析完了: ${text}`);

    const result = JSON.parse(text);
    return NextResponse.json(result);
  } catch (e) {
    console.error('音声分析エラー:', e);
    return NextResponse.json({ error: '音声分析に失敗しました' }, { status: 500 });
  }
}
