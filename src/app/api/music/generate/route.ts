import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';

const client = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY!,
  httpOptions: { apiVersion: 'v1alpha' },
});

interface GenerateMusicRequest {
  battleIntensity: number;
  element1: string;
  element2: string;
  phase: string;
}

/**
 * WAVヘッダを生成する (48kHz, 16bit, ステレオ)
 */
function createWavHeader(pcmDataLength: number): Buffer {
  const sampleRate = 48000;
  const numChannels = 2;
  const bitsPerSample = 16;
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const dataSize = pcmDataLength;
  const chunkSize = 36 + dataSize;

  const header = Buffer.alloc(44);
  // RIFFチャンク
  header.write('RIFF', 0, 'ascii');
  header.writeUInt32LE(chunkSize, 4);
  header.write('WAVE', 8, 'ascii');
  // fmtチャンク
  header.write('fmt ', 12, 'ascii');
  header.writeUInt32LE(16, 16); // Subchunk1Size (PCM=16)
  header.writeUInt16LE(1, 20); // AudioFormat (PCM=1)
  header.writeUInt16LE(numChannels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitsPerSample, 34);
  // dataチャンク
  header.write('data', 36, 'ascii');
  header.writeUInt32LE(dataSize, 40);

  return header;
}

/**
 * バトル状態からBGMプロンプトを生成する
 */
function buildMusicPrompt(req: GenerateMusicRequest): { prompt: string; bpm: number } {
  const elementMap: Record<string, string> = {
    fire: 'fiery intense orchestral',
    ice: 'cold mysterious ethereal',
    thunder: 'electric energetic percussion',
    earth: 'powerful deep drums',
    void: 'dark ambient cosmic',
  };

  const phaseMap: Record<string, string> = {
    ready: 'calm anticipation',
    battle: 'intense epic battle',
    result: 'triumphant victory fanfare',
  };

  const e1 = elementMap[req.element1] ?? 'epic';
  const e2 = elementMap[req.element2] ?? 'battle';
  const phaseDesc = phaseMap[req.phase] ?? 'epic battle';

  const prompt = `${phaseDesc}, ${e1} vs ${e2}, kaiju monster battle music, cinematic orchestral`;
  const bpm = Math.round(80 + req.battleIntensity * 0.8);

  return { prompt, bpm };
}

export async function POST(request: NextRequest) {
  console.log('BGM生成開始');
  try {
    const body: GenerateMusicRequest = await request.json();
    const { prompt, bpm } = buildMusicPrompt(body);

    console.log(`BGM生成: prompt="${prompt}", bpm=${bpm}`);

    const pcmChunks: Buffer[] = [];

    const session = await client.live.music.connect({
      model: 'models/lyria-realtime-exp',
      callbacks: {
        onmessage: (message: unknown) => {
          const msg = message as { serverContent?: { audioChunks?: Array<{ data?: string }> } };
          const chunks = msg?.serverContent?.audioChunks;
          if (chunks) {
            for (const chunk of chunks) {
              if (chunk.data) {
                pcmChunks.push(Buffer.from(chunk.data, 'base64'));
              }
            }
          }
        },
        onclose: () => {
          console.log('BGM WebSocket接続終了');
        },
        onerror: (err: unknown) => {
          console.error('BGM WebSocketエラー:', err);
        },
      },
    });

    await session.setWeightedPrompts({
      weightedPrompts: [{ text: prompt, weight: 1.0 }],
    });
    await session.setMusicGenerationConfig({
      musicGenerationConfig: { bpm, temperature: 1.0, guidance: 3.0 },
    });
    await session.play();

    await new Promise<void>((resolve) => {
      setTimeout(() => {
        session.stop();
        resolve();
      }, 15000);
    });

    if (pcmChunks.length === 0) {
      console.error('BGM生成: PCMチャンクが空');
      return NextResponse.json({ audioUrl: null, error: 'BGMデータが取得できませんでした' });
    }

    const pcmData = Buffer.concat(pcmChunks);
    const wavHeader = createWavHeader(pcmData.length);
    const wavData = Buffer.concat([wavHeader, pcmData]);
    const base64Wav = wavData.toString('base64');

    console.log(`BGM生成完了: size=${wavData.length}bytes`);
    return NextResponse.json({ audioUrl: `data:audio/wav;base64,${base64Wav}` });
  } catch (e) {
    console.error('BGM生成エラー:', e);
    return NextResponse.json({ audioUrl: null, error: 'BGM生成に失敗しました' });
  }
}
