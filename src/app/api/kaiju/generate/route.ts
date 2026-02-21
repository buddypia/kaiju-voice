import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });

interface GenerateKaijuRequest {
  kaijuName: string;
  element: string;
  action: string;
  style: string;
  /** ヒーローか怪獣かのカテゴリ */
  category?: 'kaiju' | 'hero';
}

export async function POST(request: NextRequest) {
  console.log('怪獣画像生成開始');
  try {
    const body: GenerateKaijuRequest = await request.json();
    const { kaijuName, element, action, style, category } = body;

    console.log(
      `怪獣画像生成: name=${kaijuName}, element=${element}, action=${action}, category=${category}`,
    );

    /** カテゴリに応じてプロンプトを切り替え */
    const prompt =
      category === 'hero'
        ? `${kaijuName}, ${element} element hero, ${action}, ${style}, golden aura, dark background, epic lighting`
        : `${kaijuName}, ${element} element kaiju, ${action}, ${style}, dark background, epic lighting`;

    const response = await ai.models.generateImages({
      model: 'imagen-4.0-generate-001',
      prompt,
      config: {
        numberOfImages: 1,
        aspectRatio: '1:1',
      },
    });

    const imageBytes = response.generatedImages?.[0]?.image?.imageBytes;
    if (!imageBytes) {
      console.error('画像生成: imageBytes が空');
      return NextResponse.json({ imageUrl: null, error: '画像データが取得できませんでした' });
    }

    const imageUrl = `data:image/png;base64,${imageBytes}`;
    console.log('怪獣画像生成完了');
    return NextResponse.json({ imageUrl });
  } catch (e) {
    console.error('怪獣画像生成エラー:', e);
    return NextResponse.json({ imageUrl: null, error: '画像生成に失敗しました' });
  }
}
