---
title: '1つのゲームにGemini APIを3つ統合した設計パターン — 音声分析・AI対戦・画像生成のマルチモデルアーキテクチャ'
emoji: '🎮'
type: 'tech'
topics: ['gemini', 'ai', 'hackathon', 'gamedev', 'architecture']
published: false
---

## TL;DR

Gemini 3 Tokyo Hackathon（Cerebral Valley主催）で準優勝した「KAIJU VOICE」は、**3つのGemini APIを1つのゲームに統合**しています。

この記事では、マルチモデル統合で直面した設計課題と解決パターンを解説します:

1. **Structured Output設計** — Zodスキーマ → JSON Schema変換で、AIの出力を「ゲームが消費できるデータ」に確実に変換
2. **感情駆動AI対戦** — HP比率に応じた動的プロンプト + temperature 1.0で「毎回違う対戦体験」
3. **プリフェッチ最適化** — プレイヤーの録音中にAI応答を先読みし、体感待ち時間をゼロに

---

## ゲーム概要

KAIJU VOICE は「叫び声で怪獣を戦わせる」カードバトルゲームです。

```
プレイヤーが叫ぶ → Geminiが3軸で分析 → ダメージに変換
```

3つのGemini APIが、それぞれ独立した「専門エージェント」としてゲーム体験を支えています。

---

## アーキテクチャ全体像

```
┌─────────────────────────────────────────────────────────────┐
│                    KAIJU VOICE — 3 Agent Architecture        │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐                       │
│  │ Voice Agent  │    │ Battle Agent │                       │
│  │ gemini-3-    │    │ gemini-3-    │                       │
│  │ flash        │    │ flash        │                       │
│  │              │    │              │                       │
│  │ 音声→3軸JSON │    │ 戦況→攻撃    │                       │
│  │ Structured   │    │ temperature  │                       │
│  │ Output       │    │ 1.0          │                       │
│  └──────┬───────┘    └──────┬───────┘                       │
│         │                   │                                │
│         ▼                   ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Battle Engine (Client)                   │   │
│  │  ダメージ計算 → VFX → ターン管理                      │   │
│  └──────────────────────────────────────────────────────┘   │
│         ▲                                                    │
│  ┌──────┴───────┐                                           │
│  │ Visual Agent │                                           │
│  │ Imagen 4     │                                           │
│  │ 怪獣画像生成  │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

| エージェント     | モデル                  | 入力             | 出力             |
| ---------------- | ----------------------- | ---------------- | ---------------- |
| **Voice Agent**  | gemini-3-flash-preview  | 音声(base64)     | 3軸スコア(JSON)  |
| **Battle Agent** | gemini-3-flash-preview  | 戦況コンテキスト | 攻撃データ(JSON) |
| **Visual Agent** | imagen-4.0-generate-001 | キャラクター情報 | 画像(base64)     |

---

## パターン 1: Structured Output設計 — AIの出力を「確実にパース」する

### 課題

ゲームでAIを使う最大の問題は**出力の不安定さ**です。自由形式のテキストを返されると:

- JSON.parseが失敗する
- フィールドが欠けている
- 数値の範囲が想定外

リアルタイムゲームでパースエラーが起きると、その瞬間ゲームが止まります。

### 解決: responseJsonSchema + Zodスキーマ

Geminiの `responseJsonSchema` を使い、**AIの出力形式を完全に制約**しました。

```typescript
// Zod スキーマを Single Source of Truth として定義
const voiceAnalysisSchema = z.object({
  intensity: z.number().min(0).max(100), // 迫力
  creativity: z.number().min(0).max(100), // 創造性
  emotion: z.number().min(0).max(100), // 感情
  language: z.enum(['ja', 'en', 'mixed']),
  transcript: z.string(),
  attackType: z.enum(['physical', 'special', 'ultimate']),
});

// Zod → 標準JSON Schema に変換してGeminiに渡す
const result = await model.generateContent({
  contents: [
    {
      role: 'user',
      parts: [
        { text: systemPrompt },
        { inlineData: { mimeType: 'audio/webm', data: audioBase64 } },
      ],
    },
  ],
  generationConfig: {
    responseMimeType: 'application/json',
    responseJsonSchema: toJSONSchema(voiceAnalysisSchema),
  },
});

// 返却値は必ずスキーマ通り — パースエラーゼロ
const analysis = voiceAnalysisSchema.parse(JSON.parse(result.text()));
```

### なぜ responseSchema ではなく responseJsonSchema か

Gemini APIには2つのスキーマ指定方法があります:

| 方式                     | 形式                | 互換性       |
| ------------------------ | ------------------- | ------------ |
| `responseSchema`         | Gemini独自形式      | Gemini専用   |
| **`responseJsonSchema`** | **標準JSON Schema** | **業界標準** |

`responseJsonSchema` を選んだ理由:

1. **Zodとの統合**: `toJSONSchema()` で型定義から自動導出。手動でスキーマを書く必要なし
2. **TypeScript型との統一**: `z.infer<typeof schema>` でTypeScriptの型も自動生成
3. **バリデーションの二重保証**: Geminiが構造を保証 + Zodがランタイムで検証

### 設計ポイント: システムプロンプトとスキーマの役割分担

```
システムプロンプト = 「何を評価するか」の指示
  → 声の迫力、技名の創造性、感情の込め方を評価してください

responseJsonSchema = 「どういう形式で返すか」の制約
  → { intensity: number, creativity: number, emotion: number, ... }
```

この分離により、プロンプトの改善とスキーマの変更を独立して行えます。

---

## パターン 2: 感情駆動AI対戦 — HPに応じて「人格が変わる」AI

### 課題

AI対戦相手が毎回同じような攻撃をしたら、すぐ飽きます。かといって完全ランダムでは「知性」を感じません。

### 解決: 動的プロンプト + 高temperature

**HP比率に応じてシステムプロンプトを動的に切り替える**ことで、AIに「感情」を持たせました。

```typescript
function buildSystemPrompt(aiHp: number, playerHp: number, element: string): string {
  // HP比率で「感情」が変わる
  let situationNote: string;
  if (aiHp < 25) {
    situationNote = '絶体絶命。必死で、感情的で、必殺技を繰り出す。';
  } else if (aiHp < 50) {
    situationNote = '追い詰められている。焦りと怒りが混じった攻撃をする。';
  } else if (playerHp < 25) {
    situationNote = '圧倒的優勢。余裕と高揚感を持って畳み掛ける。';
  } else {
    situationNote = '互角の戦い。力強く、自信を持って攻撃する。';
  }

  // 属性ごとの技名ヒント
  const moveHints = ELEMENT_MOVE_HINTS[element];
  // fire: '灼熱・炎・業火・爆炎'
  // ice:  '氷結・絶零・凍牙・吹雪'
  // ...

  return `あなたは怪獣バトルゲームの怪獣です。
属性: ${element}（使える技のヒント: ${moveHints}）
現在の状況: ${situationNote}
日本語で叫び声を生成してください。`;
}
```

### temperature 1.0 の意味

```typescript
const result = await model.generateContent({
  // ...
  generationConfig: {
    temperature: 1.0, // 最大の多様性
    maxOutputTokens: 150, // 簡潔に
    responseMimeType: 'application/json',
    responseJsonSchema: aiAttackSchema,
  },
});
```

`temperature: 1.0` は「同じプロンプトでも毎回違う結果を返す」設定です。Structured Outputと組み合わせることで:

- **形式は厳密**: 必ず `{ shout, intensity, creativity, emotion }` の形で返る
- **内容は創造的**: 「灼熱砲ォォォ！！」「絶零の断末魔ァァァ！」など毎回違う

**「出力形式は厳密に、内容は創造的に」** — これがStructured Output + 高temperatureの設計思想です。

### 実際の出力例

HP残り20%の氷属性怪獣:

```json
{
  "shout": "絶零砲ォォォォ！！凍てつく魂の最後の叫びィィィ！！",
  "intensity": 92,
  "creativity": 78,
  "emotion": 95,
  "attackType": "ultimate"
}
```

HP残り80%で優勢な火属性怪獣:

```json
{
  "shout": "フッ...灼熱の業火よ、この程度か？",
  "intensity": 65,
  "creativity": 70,
  "emotion": 55,
  "attackType": "special"
}
```

HPが減るにつれてAIが必死になっていくのが見えるため、プレイヤーの没入感が段違いでした。

---

## パターン 3: プリフェッチ最適化 — AI応答の待ち時間をゼロにする

### 課題

リアルタイムゲームでAI APIの応答を毎ターン待つと、テンポが崩壊します。

```
従来: プレイヤー攻撃 → [800ms待ち] → AI攻撃表示
    → この800msがゲーム体験を台無しにする
```

### 解決: 録音中の「空き時間」を利用

プレイヤーが5秒間叫んでいる間は、UIは録音中のビジュアライザーを表示しているだけ。**この間にAIの次の攻撃を裏で生成**しておきます。

```typescript
// useAIOpponent.ts — プリフェッチの仕組み

const prefetchedRef = useRef<AIAttackResult | null>(null);

// プレイヤーの録音開始と同時にプリフェッチ
function prefetchAIAttack(gameState: GameState) {
  const controller = new AbortController();

  fetch('/api/ai-opponent/attack', {
    method: 'POST',
    body: JSON.stringify(gameState),
    signal: controller.signal,
  })
    .then((res) => res.json())
    .then((data) => {
      prefetchedRef.current = data;
    })
    .catch(() => {
      /* 失敗は無視 — ライブ生成にフォールバック */
    });
}

// AIターン時に結果を取得
function consumePrefetched(): AIAttackResult | null {
  const result = prefetchedRef.current;
  prefetchedRef.current = null;
  return result;
}
```

### タイムライン比較

```
【プリフェッチあり】
0s ─── 録音開始 + プリフェッチ開始
       ├── フォアグラウンド: 音声録音 (5秒)
       └── バックグラウンド: AI攻撃生成 (~800ms)
5s ─── 録音完了
5.3s ── AI攻撃表示（プリフェッチ済み: 300ms遅延）← 快適

【プリフェッチなし】
0s ─── 録音開始
5s ─── 録音完了
5s ─── AI攻撃API呼び出し開始
5.8s ── AI攻撃表示（ライブ生成: 800ms遅延）← 待たされる
```

300ms vs 800ms — この500msの差が体感テンポを劇的に改善します。

### useRef を使う理由

`useState` ではなく `useRef` を使っているのは、**プリフェッチの結果がUIに影響しない**ためです:

- `useState`: 値が変わるたびに再レンダリング → プリフェッチ完了時に不要な再レンダリングが走る
- `useRef`: 値を保持するだけ → 再レンダリングなし → consumeする時だけ取り出す

### フォールバック値

プリフェッチが間に合わなかった場合やAPIエラー時のフォールバック:

```typescript
const DEFAULT_VOICE_ANALYSIS = {
  intensity: 60,
  creativity: 60,
  emotion: 60,
  transcript: 'ガアアアアッ！',
  attackType: 'physical',
  language: 'ja',
};
```

---

## まとめ: マルチモデル統合の設計原則

KAIJU VOICEの開発を通じて得た、Gemini APIマルチモデル統合の設計原則:

### 1. 各モデルを「専門エージェント」として設計する

1つのモデルに全てを任せるのではなく、得意な領域に特化させる:

- 分析は gemini-3-flash + Structured Output（安定性重視）
- 創造は gemini-3-flash + temperature 1.0（多様性重視）
- 画像は Imagen 4（画像生成に特化）

### 2. Structured Outputは「契約」として使う

AIの出力形式をJSON Schemaで制約することで、ゲームロジック側が安心してデータを消費できます。「AIが何を返してくるか分からない」状態を排除することが、リアルタイムアプリの鍵です。

### 3. 遅延はアーキテクチャで解決する

AIの応答時間はモデルの限界です。プリフェッチ、並列実行（Promise.all）、段階的フォールバックなど、**アーキテクチャレベルで遅延を隠す**設計が重要です。

### 4. フォールバックは「劣化しつつも動く」

プリフェッチ → ライブ生成 → デフォルト値。API失敗でゲームが止まらないよう、常に次の手段を用意しておきます。

---

## 技術スタック

| カテゴリ   | 技術                               |
| ---------- | ---------------------------------- |
| Framework  | Next.js 16 / React 19              |
| Language   | TypeScript (strict)                |
| AI         | `@google/genai` + `@ai-sdk/google` |
| Styling    | Tailwind CSS 4                     |
| Animation  | Framer Motion 12                   |
| Validation | Zod 4                              |
| State      | XState 5 + useReducer              |

**リポジトリ**: [GitHub URL]
**デモ動画**: https://www.youtube.com/watch?v=uF3PV5CS03M

#BuildWithGemini #GeminiHackathon
