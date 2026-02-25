# Case Study: KAIJU VOICE — oh-my-claude-code で準優勝した話

> Gemini 3 ハッカソン東京 (Cerebral Valley) にて、oh-my-claude-code の開発パイプラインを使って
> 「声で戦う怪獣バトルゲーム」を開発し、**準優勝**を達成しました。
>
> このドキュメントでは、パイプラインが実際にどのように仕様→UI→コードを生み出したかを
> 具体的なコードとともに紹介します。

---

## プロジェクト概要

| 項目           | 値                                                  |
| -------------- | --------------------------------------------------- |
| プロジェクト名 | KAIJU VOICE                                         |
| コンセプト     | 叫び声で怪獣を操るカードバトルゲーム                |
| 技術スタック   | Next.js 16 / React 19 / TypeScript / Tailwind CSS 4 |
| AIプロバイダー | Gemini 3 Flash, Imagen 4, Gemini TTS, Lyria         |
| 結果           | Gemini 3 ハッカソン東京 **準優勝**                  |

---

## 1. Pipeline が生成した SPEC → 型定義

### Pipeline の流れ

```
feature-pilot (Tier S)
  → architect: BRIEF.md + CONTEXT.json 生成
    → spec: SPEC-001-kaiju-voice.md 生成
      → implement: TypeScript コード生成
```

### SPEC で定義された型 (入力)

SPEC ドキュメントの `§0.2 状態 & アーキテクチャ` セクションに、
ゲームのコア型が疑似コードとして定義されました:

```
SPEC-001-kaiju-voice.md §0.2.1:

interface Player {
  id: 0 | 1;
  name: string;
  kaiju: KaijuProfile;
  hp: number;
  maxHp: number;
}

interface VoiceAnalysis {
  intensity: number;   // 0-100: 声の大きさ・エネルギー
  creativity: number;  // 0-100: 言葉の創造性・ユニークさ
  emotion: number;     // 0-100: 感情の強さ
  language: string;    // 'ja', 'en', 'mixed'
  transcript: string;
  attackType: 'physical' | 'special' | 'ultimate';
}
```

### 実装された TypeScript 型 (出力)

`src/features/battle/types/battle.ts` — SPEC の型定義がそのまま TypeScript に:

```typescript
/** 怪獣の属性 */
export type KaijuElement = 'fire' | 'ice' | 'thunder' | 'earth' | 'void' | 'light';

/** ゲームフェーズ */
export type GamePhase = 'title' | 'select' | 'battle' | 'result';

/** バトルサブフェーズ */
export type BattleSubPhase =
  | 'ready'
  | 'recording'
  | 'analyzing'
  | 'attacking'
  | 'waiting'
  | 'ai_thinking';

/** 怪獣プロフィール */
export interface KaijuProfile {
  id: string;
  name: string;
  nameJa: string;
  element: KaijuElement;
  category: CharacterCategory;
  description: string;
  imageUrl: string | null;
  baseAttack: number;
  baseDefense: number;
}

/** 音声分析結果 */
export interface VoiceAnalysis {
  intensity: number;
  creativity: number;
  emotion: number;
  language: 'ja' | 'en' | 'mixed';
  transcript: string;
  attackType: 'physical' | 'special' | 'ultimate';
}

/** ゲームアクション (12種の discriminated union) */
export type GameAction =
  | { type: 'START_GAME'; mode: GameMode }
  | { type: 'SELECT_KAIJU'; player: 0 | 1; kaiju: KaijuProfile }
  | { type: 'START_RECORDING' }
  | { type: 'APPLY_ATTACK'; attack: AttackResult }
  | { type: 'NEXT_TURN' }
  | { type: 'END_BATTLE'; winner: 0 | 1 };
// ... 全12アクション
```

**ポイント**: SPEC で定義された型構造がほぼそのまま TypeScript 型になった。
`light` 属性の追加と `GameAction` の discriminated union 化は、
implement ステップで feature-implementer が自動的に拡張した。

---

## 2. SPEC のダメージ式 → 実際のコード

### SPEC の疑似コード (入力)

```
FR-00103: ダメージ計算式

basePower = (intensity + creativity + emotion) / 3
typeMultiplier: physical=1.0, special=1.3, ultimate=1.8
langBonus: mixed=1.2, else=1.0
elementBonus = ELEMENT_MATCHUP[attacker.element][defender.element]
statRatio = baseAttack / baseDefense
damage = round(basePower × typeMultiplier × langBonus × elementBonus × statRatio)
critical: if creativity > 80 && random() < 0.2 → damage × 2
```

### 実装されたコード (出力)

`src/features/battle/hooks/useBattleEngine.ts`:

```typescript
/** ダメージ計算ロジック (SPEC FR-00103 準拠) */
export function calculateDamage(
  analysis: VoiceAnalysis | { error: string },
  attacker: Player,
  defender: Player,
): AttackResult {
  const basePower = (analysis.intensity + analysis.creativity + analysis.emotion) / 3;

  const typeMultiplier =
    analysis.attackType === 'ultimate' ? 1.8 : analysis.attackType === 'special' ? 1.3 : 1.0;

  const langBonus = analysis.language === 'mixed' ? 1.2 : 1.0;
  const elementBonus = ELEMENT_MATCHUP[attacker.kaiju.element][defender.kaiju.element];
  const statRatio = attacker.kaiju.baseAttack / defender.kaiju.baseDefense;

  let damage = Math.round(basePower * typeMultiplier * langBonus * elementBonus * statRatio);

  let isCritical = false;
  if (analysis.creativity > 80 && Math.random() < 0.2) {
    damage *= 2;
    isCritical = true;
  }

  damage = Math.max(1, damage);

  return { player: attacker.id, voiceAnalysis: analysis, damage, isCritical, attackName };
}
```

**ポイント**: SPEC の疑似コードと実装コードが1:1対応。
`// SPEC FR-00103 準拠` のコメントで traceability を確保。

---

## 3. Feature-First アーキテクチャの実現

### SPEC のアーキテクチャ定義 (入力)

```
§0.2.2 アーキテクチャガイダンス:

| Feature  | 責務                        |
| voice    | 音声キャプチャ + Gemini分析 |
| battle   | バトルロジック + 状態管理   |
| kaiju    | 怪獣データ + Imagen画像生成 |
| music    | Lyria BGM生成               |
| game     | ゲームフロー制御            |
```

### 実現されたディレクトリ構造 (出力)

```
src/features/
├── ai-opponent/          ← SPEC にない追加 (AI対戦機能)
│   ├── hooks/useAIOpponent.ts
│   └── index.ts
├── battle/               ← SPEC 通り
│   ├── components/
│   │   ├── BattleArena.tsx
│   │   ├── HPBar.tsx
│   │   ├── DamageEffect.tsx
│   │   ├── AttackSequence.tsx
│   │   ├── BattleLog.tsx
│   │   └── TurnIndicator.tsx
│   ├── hooks/useBattleEngine.ts
│   ├── types/battle.ts
│   └── index.ts
├── commentary/           ← SPEC にない追加 (AI実況)
│   ├── components/CommentaryOverlay.tsx
│   ├── hooks/useCommentary.ts
│   ├── types.ts
│   └── index.ts
├── game/                 ← SPEC 通り
│   ├── components/
│   │   ├── TitleScreen.tsx
│   │   ├── SelectScreen.tsx
│   │   ├── BattleScreen.tsx
│   │   └── ResultScreen.tsx
│   ├── hooks/useGameState.ts
│   └── index.ts
├── kaiju/                ← SPEC 通り
├── music/                ← SPEC 通り
├── vfx/                  ← SPEC にない追加 (視覚効果)
│   ├── components/
│   │   ├── ImpactFlash.tsx
│   │   ├── KnockOutEffect.tsx
│   │   ├── ParticleCanvas.tsx
│   │   ├── PinchOverlay.tsx
│   │   ├── UltimateCutIn.tsx
│   │   ├── VictoryCelebration.tsx
│   │   └── VoiceVisualizer.tsx
│   └── index.ts
└── voice/                ← SPEC 通り
```

**ポイント**:

- SPEC で定義された5つの Feature (voice/battle/kaiju/music/game) はそのまま実現
- 開発中に必要性が判明した3つの Feature (ai-opponent/commentary/vfx) が追加
- 各 Feature は `index.ts` バレルファイルで公開 API を制御
- Feature 間の依存は `index.ts` 経由のみ (CLAUDE.md の規則通り)

---

## 4. Gemini Structured Output → API ルート

### SPEC の API 契約 (入力)

```
FR-00102: Gemini Voice Analysis API

入力: audio/webm (base64)
出力: VoiceAnalysis (JSON)
応答形式: responseJsonSchema (標準 JSON Schema)
```

### 実装された API ルート (出力)

`src/app/api/voice/analyze/route.ts`:

```typescript
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

const response = await ai.models.generateContent({
  model: 'gemini-3-flash-preview',
  contents: [
    {
      role: 'user',
      parts: [
        { inlineData: { mimeType: audioFile.type, data: base64Audio } }, // 音声
        { text: 'この音声を分析して攻撃力を判定してください' },
      ],
    },
  ],
  config: {
    systemInstruction: VOICE_JUDGE_PROMPT,
    responseMimeType: 'application/json',
    responseJsonSchema: voiceAnalysisSchema, // ← responseSchema ではない
  },
});
```

**ポイント**:

- `responseJsonSchema` (標準 JSON Schema) を使用 — `responseSchema` (Gemini 独自形式) は CLAUDE.md で禁止
- マルチモーダル入力: `inlineData` で音声を直接送信
- パースエラーゼロ: Structured Output により JSON が常に valid

---

## 5. AI対戦相手: HP連動の感情表現

### 設計思想

AI対戦の「感情」は、ハッカソンのデモ映えを大幅に向上させた要素の一つ。
HP が減少するにつれて AI の叫び声が変化する:

```
HP 80%+ → 余裕の高笑い
HP 50%  → 本気モード
HP 25%  → 必死の悲鳴
HP 10%  → 最後の咆哮
```

### 実装: Battle Agent の動的プロンプト

`src/app/api/ai-opponent/attack/route.ts` より:

```typescript
// HP比率に基づく感情指示
const hpRatio = request.aiHp / request.maxHp;
let emotionGuide: string;

if (hpRatio > 0.7) {
  emotionGuide = '余裕と高揚感。強者としての叫び。';
} else if (hpRatio > 0.4) {
  emotionGuide = '本気モード。真剣な戦いの叫び。';
} else if (hpRatio > 0.15) {
  emotionGuide = '追い詰められた必死さ。絶体絶命の叫び。';
} else {
  emotionGuide = '最後の力を振り絞る。魂の咆哮。';
}
```

**結果**: デモ審査で「AI が本当に必死になっている」という評価を受けた。
`temperature: 1.0` の高設定で創造的な叫び声が生まれ、毎回異なるバトル体験に。

---

## 6. Dual-Path TTS: テキスト + 音声の並列処理

### 課題

AI実況をリアルタイムで表示しつつ音声も再生したい。
しかしテキスト生成 (SSE) と音声生成 (Live API) は独立した API。

### 実装: Promise.all による並列実行

`src/features/commentary/hooks/useCommentary.ts`:

```typescript
// テキストストリーミングと Live API音声を並列実行
const textPromise = (async () => {
  const res = await fetch('/api/commentary/generate', { method: 'POST', ... });
  const reader = res.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    fullText += decoder.decode(value, { stream: true });
    setCommentary(prev => ({ ...prev, text: fullText }));  // リアルタイム表示
  }
})();

const audioPromise = speakLive(event);  // Live API PCM 音声

const [, liveSuccess] = await Promise.all([textPromise, audioPromise]);

// Live API失敗 → ブラウザTTSフォールバック
if (!liveSuccess && fullText) {
  await speakFallback(fullText);  // SpeechSynthesisUtterance
}
```

### 3段階フォールバック

```
Level 1: Gemini TTS (Live API) — PCM 24kHz
  ↓ 失敗
Level 2: ブラウザ SpeechSynthesis — ja-JP, rate 1.3
  ↓ 未サポート
Level 3: テキストのみ表示 (音声なし)
```

**ポイント**: 初回 Live API 失敗で `liveApiEnabledRef.current = false` に。
以降のリクエストは即座にフォールバックに移行し、無駄な API コールを防止。

---

## 7. Prefetch パターン: AI ターンの待ち時間を削減

### 課題

プレイヤーが叫んでいる 5秒間、AI は何もしていない。
この時間を利用して AI の攻撃を事前生成できるのではないか。

### 実装

`src/features/ai-opponent/hooks/useAIOpponent.ts`:

```typescript
/** プレイヤーターン中にAI攻撃を事前生成（バックグラウンド） */
const prefetchAIAttack = useCallback((request: AIAttackRequest) => {
  if (prefetchAbortRef.current) prefetchAbortRef.current.abort();

  const controller = new AbortController();
  prefetchAbortRef.current = controller;

  fetchAIAttack(request, controller.signal).then((analysis) => {
    if (!controller.signal.aborted) {
      prefetchedRef.current = analysis; // useRef に保存
    }
  });
}, []);

/** プリフェッチ済みの攻撃を取得して消費する */
const consumePrefetched = useCallback((): VoiceAnalysis | null => {
  const cached = prefetchedRef.current;
  prefetchedRef.current = null;
  return cached; // あれば即座に返却、なければ null
}, []);
```

### タイムライン比較

```
プリフェッチなし:
  [プレイヤー5秒] → [AI生成 ~800ms] → [攻撃表示]
  合計: ~800ms 待ち

プリフェッチあり:
  [プレイヤー5秒 + AI生成を並行] → [consume ~0ms] → [攻撃表示]
  合計: ~300ms 待ち (UI遷移のみ)
```

---

## 8. 怪獣データ: SPEC → 定数ファイル

### SPEC のプリセット定義 (入力)

```
§3.3 怪獣プリセット:

| ID | 名前           | 属性    | ATK | DEF |
| 01 | Infernus       | fire    | 12  | 8   |
| 02 | Glacius        | ice     | 8   | 12  |
| 03 | Voltarion      | thunder | 11  | 9   |
| 04 | Terradon       | earth   | 9   | 11  |
| 05 | Nihilus        | void    | 10  | 10  |
```

### 実装された定数ファイル (出力)

`src/shared/constants/kaiju-data.ts`:

```typescript
/** 属性相性テーブル: ELEMENT_MATCHUP[攻撃][防御] = 倍率 */
export const ELEMENT_MATCHUP: Record<KaijuElement, Record<KaijuElement, number>> = {
  fire: { fire: 1.0, ice: 1.5, thunder: 0.8, earth: 1.0, void: 0.8, light: 0.8 },
  ice: { fire: 0.8, ice: 1.0, thunder: 1.5, earth: 0.8, void: 1.0, light: 1.0 },
  thunder: { fire: 1.0, ice: 0.8, thunder: 1.0, earth: 1.5, void: 0.8, light: 1.0 },
  earth: { fire: 1.0, ice: 1.0, thunder: 0.8, earth: 1.0, void: 1.5, light: 0.8 },
  void: { fire: 1.5, ice: 0.8, thunder: 1.0, earth: 0.8, void: 1.0, light: 1.5 },
  light: { fire: 1.5, ice: 1.0, thunder: 1.0, earth: 1.5, void: 0.8, light: 1.0 },
};

/** 怪獣プリセットデータ (5体) */
export const KAIJU_PRESETS: KaijuProfile[] = [
  {
    id: '01',
    name: 'Infernus',
    nameJa: 'インフェルヌス',
    element: 'fire',
    category: 'kaiju',
    description: '灼熱の怪獣。すべてを焼き尽くす',
    imageUrl: '/images/kaiju-infernus.png',
    baseAttack: 12,
    baseDefense: 8,
  },
  // ... 全5体
];

export const INITIAL_HP = 200;
export const RECORDING_DURATION_MS = 5000;
```

---

## 9. VFX コンポーネント: Canvas 2D パーティクルシステム

パイプラインが生成した VFX は6属性それぞれ異なるパーティクル物理を持つ:

```
fire:    円形粒子、上昇 + ドリフト、オレンジ/赤グラデーション
ice:     六角形(ポリゴン描画)、落下、シアンストローク
thunder: 稲妻型ポリライン、高速・短寿命
earth:   正方形、重力付き、茶/ライム
void:    拡大リング(ストロークのみ)、紫
light:   発光円形、アンバー
```

これらは `src/features/vfx/components/ParticleCanvas.tsx` で
単一の Canvas 2D コンポーネントに統合され、
`attacker.kaiju.element` プロパティで自動切替される。

---

## 10. テスト: SPEC FR → テストケース

`tests/unit/features/battle/useBattleEngine.test.ts`:

```typescript
describe('calculateDamage', () => {
  it('physical < special < ultimate の順にダメージが増加する', () => {
    // FR-00103: typeMultiplier = physical:1.0, special:1.3, ultimate:1.8
    const physical = calculateDamage({ ...base, attackType: 'physical' }, p1, p2);
    const special = calculateDamage({ ...base, attackType: 'special' }, p1, p2);
    const ultimate = calculateDamage({ ...base, attackType: 'ultimate' }, p1, p2);
    expect(physical.damage).toBeLessThan(special.damage);
    expect(special.damage).toBeLessThan(ultimate.damage);
  });

  it('fire → ice は属性ボーナス 1.5x を適用する', () => {
    // FR-00103: elementBonus = ELEMENT_MATCHUP[attacker][defender]
    const fireVsIce = calculateDamage(base, firePlayer, icePlayer);
    const fireVsFire = calculateDamage(base, firePlayer, firePlayer);
    expect(fireVsIce.damage).toBeGreaterThan(fireVsFire.damage);
  });

  it('mixed 言語は 1.2x ボーナスを適用する', () => {
    const mixed = calculateDamage({ ...base, language: 'mixed' }, p1, p2);
    const ja = calculateDamage({ ...base, language: 'ja' }, p1, p2);
    expect(mixed.damage).toBeGreaterThan(ja.damage);
  });

  it('最低ダメージは 1', () => {
    const weakAttack = calculateDamage(
      { ...base, intensity: 1, creativity: 1, emotion: 1 },
      p1,
      p2,
    );
    expect(weakAttack.damage).toBeGreaterThanOrEqual(1);
  });
});
```

**ポイント**: 各テストケースが SPEC の FR 番号を参照。
`feature-implementer` スキルが実装と同時にテストを生成した。

---

## まとめ: パイプラインが生み出したもの

| パイプラインのステップ | 入力                   | 出力 (実際のファイル)                                           |
| ---------------------- | ---------------------- | --------------------------------------------------------------- |
| architect              | 「声で戦う怪獣バトル」 | BRIEF.md + CONTEXT.json                                         |
| spec                   | BRIEF.md               | SPEC-001 (型定義, FR, API契約, ダメージ式)                      |
| implement: Type        | SPEC §0.2              | `battle/types/battle.ts` (12型 + 12アクション)                  |
| implement: Data        | SPEC §3.3              | `kaiju-data.ts` (5怪獣 + 5ヒーロー + 6×6属性表)                 |
| implement: API         | SPEC §2.x              | 6つの API ルート (voice/battle/commentary/kaiju/music)          |
| implement: Hook        | SPEC §1.x              | 7つの Custom Hook (battle/voice/commentary/ai/music/kaiju/game) |
| implement: UI          | SPEC + screens/        | 4画面 + 20+ コンポーネント                                      |
| implement: VFX         | (デモ映え追加)         | 7つの VFX コンポーネント (Canvas 2D + framer-motion)            |
| implement: Test        | SPEC FR                | 7テストケース (FR-00103 準拠)                                   |
| quality_gate           | 全ファイル             | lint 0 errors, test 100% pass, build success                    |

### 数字で見る成果

- **開発時間**: 約6時間 (ハッカソン当日)
- **総ファイル数**: 50+ ファイル
- **総コード行数**: 約5,000行
- **Gemini API**: 6エンドポイント (Voice, Battle, Commentary Text, Commentary TTS, Kaiju Image, Music)
- **Feature 数**: 8 (SPEC の5つ + 追加3つ)
- **VFX**: 7コンポーネント (6属性パーティクル + KO演出)
- **テスト**: 7ケース (ダメージ計算の全パターン)
- **結果**: **準優勝**

### パイプラインの貢献

1. **SPEC → 型の自動変換**: 疑似コードが TypeScript 型にほぼ1:1で変換された
2. **Feature-First 構造の強制**: CLAUDE.md + quality_gate が構造を保証
3. **API 契約の明示化**: SPEC の JSON Schema 定義が `responseJsonSchema` にそのまま使用可能
4. **テスト同時生成**: 実装と同時にテストが生成され、回帰を防止
5. **追加機能の自然な統合**: ai-opponent/commentary/vfx は既存構造に沿って追加できた
