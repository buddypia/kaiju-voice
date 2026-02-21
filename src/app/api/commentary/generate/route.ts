import { gemini } from '@/shared/lib/gemini';

const SYSTEM_PROMPT = `あなたは「KAIJU VOICE」怪獣バトルゲームの熱血実況解説者です。
バトルの各イベントに対して、短く熱い実況コメントを生成してください。

ルール:
- 日本語で、プロレス実況のような熱いトーンで
- 1〜2文（最大60文字）で簡潔に
- 怪獣名と属性を活用した実況
- クリティカル時は特にテンション高く
- KO時は劇的に`;

interface CommentaryRequest {
  event: 'battle_start' | 'attack' | 'critical' | 'low_hp' | 'ko';
  attacker?: string;
  defender?: string;
  attackName?: string;
  damage?: number;
  remainingHp?: number;
  maxHp?: number;
  winner?: string;
  loser?: string;
  element1?: string;
  element2?: string;
  totalRounds?: number;
}

function buildPrompt(data: CommentaryRequest): string {
  switch (data.event) {
    case 'battle_start':
      return `バトル開始！${data.attacker}(${data.element1}属性) vs ${data.defender}(${data.element2}属性)。開幕の実況をどうぞ。`;
    case 'attack':
      return `${data.attacker}の攻撃「${data.attackName}」が${data.defender}に${data.damage}ダメージ！残りHP: ${data.remainingHp}/${data.maxHp}。実況をどうぞ。`;
    case 'critical':
      return `クリティカルヒット！${data.attacker}の「${data.attackName}」が${data.defender}に${data.damage}の大ダメージ！！残りHP: ${data.remainingHp}/${data.maxHp}。最高にテンション上げて実況！`;
    case 'low_hp':
      return `${data.defender}のHPが危険域！残りHP: ${data.remainingHp}/${data.maxHp}。追い詰められた状況の実況を。`;
    case 'ko':
      return `決着！${data.winner}が${data.loser}を${data.totalRounds}ラウンドで撃破！勝利の瞬間を劇的に実況！`;
    default:
      return '怪獣バトルの実況をお願いします。';
  }
}

export async function POST(req: Request) {
  try {
    const data: CommentaryRequest = await req.json();
    const prompt = buildPrompt(data);

    const response = await gemini.models.generateContentStream({
      model: 'gemini-3-flash-preview',
      contents: [
        { role: 'user', parts: [{ text: SYSTEM_PROMPT }] },
        { role: 'model', parts: [{ text: '了解しました！熱い実況をお届けします！' }] },
        { role: 'user', parts: [{ text: prompt }] },
      ],
      config: {
        maxOutputTokens: 100,
        temperature: 1.2,
      },
    });

    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of response) {
            const text = chunk.text;
            if (text) {
              controller.enqueue(new TextEncoder().encode(text));
            }
          }
          controller.close();
        } catch (err) {
          console.error('Commentary stream error:', err);
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
      },
    });
  } catch (err) {
    console.error('Commentary API error:', err);
    return Response.json({ error: 'Commentary generation failed' }, { status: 500 });
  }
}
