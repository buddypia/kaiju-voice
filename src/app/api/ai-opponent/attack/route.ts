import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import type { AIAttackRequest, AIAttackResponse } from '@/features/battle/types/battle';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });

/** 属性ごとの技名ヒント */
const ELEMENT_MOVE_HINTS: Record<string, string> = {
  fire: '灼熱・炎・業火・爆炎',
  ice: '氷結・絶零・凍牙・吹雪',
  thunder: '雷鳴・迅雷・電撃・雷光',
  earth: '地震・岩砕・大地・崩壊',
  void: '虚無・消滅・暗黒・混沌',
};

/** AIバトル叫び生成プロンプト */
function buildSystemPrompt(request: AIAttackRequest): string {
  const aiHpRatio = request.aiHp / request.maxHp;
  const opponentHpRatio = request.opponentHp / request.maxHp;
  const elementHints = ELEMENT_MOVE_HINTS[request.aiKaiju.element] ?? '力・破壊・猛威';

  let situationNote = '';
  if (aiHpRatio < 0.25) {
    situationNote =
      'あなたのHPは残りわずか（25%未満）。絶体絶命の状況で全力を振り絞っている。必死で、感情的で、必殺技を繰り出す。';
  } else if (aiHpRatio < 0.5) {
    situationNote = 'あなたのHPは半分以下。追い詰められている。焦りと怒りが混じった攻撃をする。';
  } else if (opponentHpRatio < 0.25) {
    situationNote =
      '相手のHPは残りわずか（25%未満）。あなたが圧倒的優勢。余裕と高揚感を持って畳み掛ける。';
  } else {
    situationNote = '互角の戦い。力強く、自信を持って攻撃する。';
  }

  return `あなたは怪獣バトルゲーム「KAIJU VOICE」に登場するAI怪獣「${request.aiKaiju.nameJa}」です。
属性: ${request.aiKaiju.element}（使える技のヒント: ${elementHints}）
対戦相手: ${request.opponentKaiju.nameJa}
現在の状況: ${situationNote}
ラウンド: ${request.roundNumber}

あなたの役割:
- 怪獣として、バトル状況に応じた叫びと技名を日本語で生成する
- 叫びは短く（1〜2文、最大40文字）、迫力があり、技名を含む
- attackType は状況に応じて選ぶ（HP低下時はspecial/ultimateが多くなる）

JSONのみで応答してください。`;
}

/** Gemini出力スキーマ */
const aiAttackSchema = {
  type: 'object',
  required: ['shoutText', 'intensity', 'creativity', 'emotion', 'attackType'],
  properties: {
    shoutText: { type: 'string', description: '叫びテキスト（日本語、1-2文、技名含む）' },
    intensity: { type: 'number', description: '0-100: 迫力' },
    creativity: { type: 'number', description: '0-100: 創造性' },
    emotion: { type: 'number', description: '0-100: 感情' },
    attackType: { type: 'string', enum: ['physical', 'special', 'ultimate'] },
  },
};

/**
 * AI対戦相手の攻撃生成エンドポイント
 * POST /api/ai-opponent/attack
 */
export async function POST(request: NextRequest) {
  console.log('AI対戦攻撃生成開始');
  try {
    const body: AIAttackRequest = await request.json();

    const { aiKaiju, opponentKaiju, aiHp, opponentHp, maxHp, roundNumber } = body;
    if (
      !aiKaiju ||
      !opponentKaiju ||
      aiHp === undefined ||
      opponentHp === undefined ||
      !maxHp ||
      !roundNumber
    ) {
      return NextResponse.json({ error: 'リクエストパラメータが不足しています' }, { status: 400 });
    }

    console.log(
      `AI攻撃生成: ${aiKaiju.nameJa} vs ${opponentKaiju.nameJa}, aiHP=${aiHp}/${maxHp}, oppHP=${opponentHp}/${maxHp}`,
    );

    const systemPrompt = buildSystemPrompt(body);

    const userMessage = `ラウンド${roundNumber}の攻撃を生成してください。`;

    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: [{ role: 'user', parts: [{ text: userMessage }] }],
      config: {
        systemInstruction: systemPrompt,
        responseMimeType: 'application/json',
        responseJsonSchema: aiAttackSchema,
        temperature: 1.0,
        maxOutputTokens: 150,
      },
    });

    const text = response.text;
    if (!text) {
      console.error('AI攻撃生成: レスポンステキストが空');
      return NextResponse.json({ error: 'AI攻撃生成の応答が空です' }, { status: 500 });
    }

    console.log(`AI攻撃生成完了: ${text}`);

    const result: AIAttackResponse = JSON.parse(text);
    return NextResponse.json(result);
  } catch (e) {
    console.error('AI攻撃生成エラー:', e);
    return NextResponse.json({ error: 'AI攻撃生成に失敗しました' }, { status: 500 });
  }
}
