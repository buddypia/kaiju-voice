# 001: KAIJU VOICE — 声で戦う怪獣バトルゲーム

> **状態**: SpecDrafting (0%) | **優先度**: P0-MVP | **修正日**: 2026-02-21
> **Tier**: 1 - 高リスク (外部API 3種連携 + リアルタイム音声) | **機能タイプ**: AI + ゲーム

---

## 0. AI 実装契約

### 0.1 ターゲットファイル

| レイヤー  | 範囲 (Glob)                           | 作業 | 条件 | 備考                              |
| --------- | ------------------------------------- | :--: | ---- | --------------------------------- |
| Type      | `src/features/voice/types/**`         |  🆕  | -    | VoiceAnalysis, AttackResult       |
| Type      | `src/features/battle/types/**`        |  🆕  | -    | Kaiju, BattleState, Player, Turn  |
| Type      | `src/features/kaiju/types/**`         |  🆕  | -    | KaijuProfile, KaijuImage          |
| Hook      | `src/features/voice/hooks/**`         |  🆕  | -    | useVoiceCapture, useVoiceAnalysis |
| Hook      | `src/features/battle/hooks/**`        |  🆕  | -    | useBattleEngine, useGameFlow      |
| Hook      | `src/features/kaiju/hooks/**`         |  🆕  | -    | useKaijuGeneration                |
| Hook      | `src/features/music/hooks/**`         |  🆕  | -    | useBattleBGM                      |
| API Route | `src/app/api/voice/analyze/route.ts`  |  🆕  | -    | Gemini Live API 音声分析          |
| API Route | `src/app/api/kaiju/generate/route.ts` |  🆕  | -    | Imagen 3 怪獣画像生成             |
| API Route | `src/app/api/music/generate/route.ts` |  🆕  | -    | Lyria BGM生成                     |
| Component | `src/features/voice/components/**`    |  🆕  | -    | VoiceRecorder, VoiceVisualizer    |
| Component | `src/features/battle/components/**`   |  🆕  | -    | BattleArena, HPBar, DamageEffect  |
| Component | `src/features/kaiju/components/**`    |  🆕  | -    | KaijuCard, KaijuDisplay           |
| Component | `src/features/game/components/**`     |  🆕  | -    | TitleScreen, SelectScreen, etc.   |
| Page      | `src/app/page.tsx`                    |  🆕  | -    | タイトル画面                      |
| Page      | `src/app/select/page.tsx`             |  🆕  | -    | 怪獣選択画面                      |
| Page      | `src/app/battle/page.tsx`             |  🆕  | -    | バトル画面                        |
| Page      | `src/app/result/page.tsx`             |  🆕  | -    | リザルト画面                      |
| Layout    | `src/app/layout.tsx`                  |  🆕  | -    | ルートレイアウト (ダークテーマ)   |
| Style     | `src/app/globals.css`                 |  🆕  | -    | グローバルスタイル + テーマ       |
| Shared    | `src/shared/lib/gemini.ts`            |  🆕  | -    | Gemini クライアント初期化         |
| Shared    | `src/shared/constants/messages.ts`    |  🆕  | -    | UI メッセージ定数                 |
| Shared    | `src/shared/constants/kaiju-data.ts`  |  🆕  | -    | 怪獣プリセットデータ              |
| Test      | `tests/unit/features/battle/**`       |  🆕  | -    | バトルエンジンテスト              |
| Test      | `tests/unit/features/voice/**`        |  🆕  | -    | 音声分析テスト                    |

### 0.2 状態 & アーキテクチャ

#### 0.2.1 コア状態

| 状態要素      | タイプ                 | 必須 | 用途                      | 初期値    |
| ------------- | ---------------------- | :--: | ------------------------- | --------- |
| `gamePhase`   | `GamePhase`            |  ✅  | ゲーム全体の進行状態      | `'title'` |
| `players`     | `[Player, Player]`     |  ✅  | 2人のプレイヤー情報       | preset    |
| `currentTurn` | `0 \| 1`               |  ✅  | 現在のターン (P1=0, P2=1) | `0`       |
| `roundNumber` | `number`               |  ✅  | 現在のラウンド数          | `1`       |
| `isRecording` | `boolean`              |  ✅  | 音声録音中か              | `false`   |
| `isAnalyzing` | `boolean`              |  ✅  | 音声分析中か              | `false`   |
| `lastAttack`  | `AttackResult \| null` |  ⚪  | 直前の攻撃結果            | `null`    |
| `battleLog`   | `BattleLogEntry[]`     |  ⚪  | バトルログ                | `[]`      |
| `bgmUrl`      | `string \| null`       |  ⚪  | 現在のBGM URL             | `null`    |

**状態 type 定義**:

```typescript
type GamePhase = 'title' | 'select' | 'battle' | 'battle-voice' | 'battle-attack' | 'result';

interface Player {
  id: 0 | 1;
  name: string;
  kaiju: KaijuProfile;
  hp: number;
  maxHp: number;
}

interface KaijuProfile {
  id: string;
  name: string;
  nameJa: string;
  element: 'fire' | 'ice' | 'thunder' | 'earth' | 'void';
  description: string;
  imageUrl: string | null;
  baseAttack: number;
  baseDefense: number;
}

interface AttackResult {
  player: 0 | 1;
  voiceAnalysis: VoiceAnalysis;
  damage: number;
  isCritical: boolean;
  attackName: string;
}

interface VoiceAnalysis {
  intensity: number; // 0-100: 声の大きさ・エネルギー
  creativity: number; // 0-100: 言葉の創造性・ユニークさ
  emotion: number; // 0-100: 感情の強さ
  language: string; // 検出言語 ('ja', 'en', 'mixed')
  transcript: string; // 認識されたテキスト
  attackType: 'physical' | 'special' | 'ultimate';
}

interface BattleLogEntry {
  round: number;
  turn: 0 | 1;
  attack: AttackResult;
  remainingHp: [number, number];
  timestamp: number;
}
```

#### 0.2.2 アーキテクチャガイダンス

**Feature分離**:

| Feature  | 責務                        |
| -------- | --------------------------- |
| `voice`  | 音声キャプチャ + Gemini分析 |
| `battle` | バトルロジック + 状態管理   |
| `kaiju`  | 怪獣データ + Imagen画像生成 |
| `music`  | Lyria BGM生成               |
| `game`   | ゲームフロー制御 (XState)   |

**ゲーム状態マシン (XState)**:

```
title → select → battle ⟳ (voice → attack → check)
                            ↓ HP <= 0
                          result → title
```

### 0.3 エラーハンドリングポリシー

| エラータイプ         | UI表示               | 再試行 | 備考              |
| -------------------- | -------------------- | :----: | ----------------- |
| マイク許可なし       | ダイアログ           |   ❌   | マイク許可を案内  |
| 音声分析タイムアウト | トースト             |   ✅   | 10秒制限          |
| Imagen生成失敗       | プレースホルダー使用 |   ✅   | SVGフォールバック |
| Lyria生成失敗        | デフォルトBGM使用    |   ✅   | 静的音楽ファイル  |
| API通信エラー        | トースト + 再試行    |   ✅   | 最大2回           |

### 0.5 API Contract

| ID         | Method | Path                  | Auth | 説明                  |
| ---------- | ------ | --------------------- | :--: | --------------------- |
| API-001-01 | POST   | `/api/voice/analyze`  |  ❌  | 音声データ → 攻撃分析 |
| API-001-02 | POST   | `/api/kaiju/generate` |  ❌  | 怪獣名 → 画像生成     |
| API-001-03 | POST   | `/api/music/generate` |  ❌  | 戦況 → BGM生成        |

#### API-001-01: 音声分析

**Request**: `multipart/form-data` — audioBlob (WebM/WAV)
**Response**:

```json
{
  "intensity": 85,
  "creativity": 72,
  "emotion": 90,
  "language": "ja",
  "transcript": "ファイヤーブレス！",
  "attackType": "special"
}
```

#### API-001-02: 怪獣画像生成

**Request**:

```json
{
  "kaijuName": "Infernus",
  "element": "fire",
  "action": "breathing fire at enemy",
  "style": "anime kaiju battle scene, dramatic lighting"
}
```

**Response**: `{ "imageUrl": "data:image/png;base64,..." }`

#### API-001-03: BGM生成

**Request**:

```json
{
  "battleIntensity": "high",
  "element1": "fire",
  "element2": "ice",
  "phase": "climax"
}
```

**Response**: `{ "audioUrl": "data:audio/wav;base64,..." }`

### 0.7 AI Logic & Prompts

#### 0.7.1 AI 役割定義

| 役割            | 目的                     | モデル/API       |
| --------------- | ------------------------ | ---------------- |
| Voice Judge     | 叫び声の攻撃力を判定     | Gemini 2.0 Flash |
| Kaiju Artist    | 怪獣のバトルシーンを描く | Imagen 3         |
| Battle Composer | 戦況BGMを生成            | Lyria            |

#### 0.7.2 Voice Judge System Prompt

```
あなたは「KAIJU VOICE」バトルゲームの審判AIです。
プレイヤーが叫んだ音声を分析し、怪獣の攻撃力を判定してください。

## 判定基準
1. **intensity** (0-100): 声の大きさ、エネルギー、迫力
2. **creativity** (0-100): 叫んだ言葉の創造性、ユニークさ、面白さ
3. **emotion** (0-100): 感情の強さ、込められた気持ち
4. **language**: 検出された言語 ("ja", "en", "mixed")
5. **attackType**: 攻撃の種類
   - "physical": 単純な叫び声、シンプルな言葉
   - "special": 技名を叫ぶ、創造的な攻撃名
   - "ultimate": 複数言語混在、詩的、非常に創造的な叫び

## ルール
- 日本語と英語の混在は creativity ボーナス (+10-20)
- 面白い叫び声は creativity と emotion 両方にボーナス
- 同じ叫びの繰り返しは creativity ペナルティ
- JSON のみで応答してください
```

#### 0.7.3 Voice Analysis Response Schema

```json
{
  "type": "object",
  "required": ["intensity", "creativity", "emotion", "language", "transcript", "attackType"],
  "properties": {
    "intensity": { "type": "number", "minimum": 0, "maximum": 100 },
    "creativity": { "type": "number", "minimum": 0, "maximum": 100 },
    "emotion": { "type": "number", "minimum": 0, "maximum": 100 },
    "language": { "type": "string", "enum": ["ja", "en", "mixed"] },
    "transcript": { "type": "string" },
    "attackType": { "type": "string", "enum": ["physical", "special", "ultimate"] }
  }
}
```

### 0.9 Design Tokens

**テーマ**: Terminal Noir + 怪獣バトル (炎・氷・雷のエフェクト色)

| 用途         | Tailwindクラス                                       |
| ------------ | ---------------------------------------------------- |
| 背景         | `bg-[#0b1120]`                                       |
| パネル       | `backdrop-blur-xl bg-white/5 border border-white/10` |
| HP バー (P1) | `bg-gradient-to-r from-cyan-500 to-blue-500`         |
| HP バー (P2) | `bg-gradient-to-r from-red-500 to-orange-500`        |
| ダメージ表示 | `text-amber-400 animate-bounce`                      |
| 録音中       | `border-red-500 animate-pulse shadow-red-500/50`     |
| 分析中       | `border-cyan-400 animate-pulse shadow-cyan-400/50`   |

---

## 1. 概要

### 1.1 目標 (WHY)

声で怪獣を操る斬新なゲーム体験により、ハッカソン審査員に強烈なインパクトを与える。Gemini Live API + Imagen 3 + Lyria の3つのAPIを最大活用し、リアルタイムAIインタラクションの可能性を示す。

### 1.2 ユーザーストーリー

```
AS A ハッカソン会場の参加者
I WANT TO マイクに向かって叫んで怪獣を操り、隣の人と対戦する
SO THAT Gemini AI が声の創造性を判定し、笑いながら白熱したバトルができる
```

### 1.3 MVP 範囲

| 含む                          | 除外                               |
| ----------------------------- | ---------------------------------- |
| ローカル2P ターン制バトル     | オンライン対戦                     |
| 音声分析 → 攻撃力決定         | リアルタイム連続音声ストリーミング |
| 怪獣画像のAI生成              | 怪獣アニメーション                 |
| 戦況BGM生成                   | SEフェクト (効果音)                |
| タイトル→選択→バトル→リザルト | ランキング・スコアボード           |
| 5体の怪獣プリセット           | カスタム怪獣作成                   |
| HP制 (先にHP 0で負け)         | スキル・特殊能力システム           |

### 1.4 目的 / 非目的

#### 目的

1. **デモ映え**: 会場で叫んで戦える、見ていて面白いゲーム
2. **API活用**: Gemini Live API + Imagen 3 + Lyria の3種同時活用
3. **インタラクティブ性**: AIがリアルタイムで声を評価し攻撃に変換

#### 非目的

| 項目         | 理由             |
| ------------ | ---------------- |
| ユーザー認証 | ハッカソン不要   |
| データ永続化 | セッション内のみ |
| モバイル対応 | PC デモのみ      |
| 多言語対応   | 日本語UI固定     |

---

## 2. 機能要件

### FR-00101: 音声キャプチャ

| 項目             | 内容                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| **説明**         | ブラウザのマイクから音声をキャプチャ                                                             |
| **実装ファイル** | `src/features/voice/hooks/useVoiceCapture.ts`, `src/features/voice/components/VoiceRecorder.tsx` |
| **テスト**       | `tests/unit/features/voice/useVoiceCapture.test.ts`                                              |
| **状態**         | ⬜ 未開始                                                                                        |

**AC**:

| AC  | Given          | When           | Then                          |
| :-: | -------------- | -------------- | ----------------------------- |
| AC1 | マイク許可済み | 録音ボタン押下 | 音声キャプチャ開始、5秒間録音 |
| AC2 | 録音中         | 5秒経過        | 自動停止、audioBlob取得       |
| AC3 | マイク未許可   | 録音ボタン押下 | 許可ダイアログ表示            |

**ロジック**:

```pseudocode
FUNCTION startRecording():
  stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
  recorder.start()
  setTimeout(() => recorder.stop(), 5000)  // 5秒制限
  return audioBlob
```

### FR-00102: 音声リアルタイム分析 (Gemini)

| 項目             | 内容                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------ |
| **説明**         | 音声データをGemini に送信し攻撃力を分析                                              |
| **実装ファイル** | `src/app/api/voice/analyze/route.ts`, `src/features/voice/hooks/useVoiceAnalysis.ts` |
| **テスト**       | `tests/unit/features/voice/useVoiceAnalysis.test.ts`                                 |
| **状態**         | ⬜ 未開始                                                                            |

**AC**:

| AC  | Given          | When        | Then                                               |
| :-: | -------------- | ----------- | -------------------------------------------------- |
| AC1 | 音声データあり | 分析API呼出 | intensity/creativity/emotion/language 取得 3秒以内 |
| AC2 | 音声データなし | 分析API呼出 | エラー返却                                         |

**ロジック**:

```pseudocode
FUNCTION analyzeVoice(audioBlob: Blob) -> VoiceAnalysis:
  // 1. 音声をBase64変換
  audioBase64 = toBase64(audioBlob)

  // 2. Gemini に音声 + System Prompt 送信
  response = gemini.generateContent({
    model: "gemini-2.0-flash",
    contents: [
      { role: "user", parts: [
        { inlineData: { mimeType: "audio/webm", data: audioBase64 } },
        { text: "この音声を分析してください" }
      ]}
    ],
    systemInstruction: VOICE_JUDGE_PROMPT,
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: voiceAnalysisSchema
    }
  })

  // 3. 結果をパース
  RETURN parseJSON(response.text)
```

### FR-00103: バトルエンジン

| 項目             | 内容                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **説明**         | HP管理・ダメージ計算・ターン制・勝敗判定                                              |
| **実装ファイル** | `src/features/battle/hooks/useBattleEngine.ts`, `src/features/battle/types/battle.ts` |
| **テスト**       | `tests/unit/features/battle/useBattleEngine.test.ts`                                  |
| **状態**         | ⬜ 未開始                                                                             |

**AC**:

| AC  | Given        | When             | Then                            |
| :-: | ------------ | ---------------- | ------------------------------- |
| AC1 | バトル中     | 音声分析結果受信 | ダメージ計算 → 相手HP減少       |
| AC2 | 相手HP 0以下 | ダメージ適用後   | 勝利判定 → result画面遷移       |
| AC3 | 両者HP > 0   | ダメージ適用後   | ターン交替 → 次プレイヤーに切替 |

**ダメージ計算ロジック**:

```pseudocode
FUNCTION calculateDamage(analysis: VoiceAnalysis, attacker: Player, defender: Player) -> number:
  // 基礎ダメージ = (intensity + creativity + emotion) / 3
  basePower = (analysis.intensity + analysis.creativity + analysis.emotion) / 3

  // 攻撃タイプ倍率
  typeMultiplier = MATCH analysis.attackType:
    "physical" → 1.0
    "special"  → 1.3
    "ultimate" → 1.8

  // 言語ボーナス (多言語混在は創造的)
  langBonus = IF analysis.language == "mixed" THEN 1.2 ELSE 1.0

  // 属性相性 (じゃんけん: fire > ice > thunder > earth > void > fire)
  elementBonus = getElementBonus(attacker.kaiju.element, defender.kaiju.element)

  // 最終ダメージ
  damage = ROUND(basePower * typeMultiplier * langBonus * elementBonus * (attacker.kaiju.baseAttack / defender.kaiju.baseDefense))

  // クリティカル判定: creativity > 80 で 20% 確率
  IF analysis.creativity > 80 AND random() < 0.2:
    damage *= 2
    isCritical = true

  RETURN MAX(1, damage)  // 最低1ダメージ保証
```

**属性相性**:
| 攻撃 ↓ / 防御 → | fire | ice | thunder | earth | void |
| ---------------- | :--: | :--: | :-----: | :---: | :---: |
| fire | 1.0 | 1.5 | 0.8 | 1.0 | 0.8 |
| ice | 0.8 | 1.0 | 1.5 | 0.8 | 1.0 |
| thunder | 1.0 | 0.8 | 1.0 | 1.5 | 0.8 |
| earth | 1.0 | 1.0 | 0.8 | 1.0 | 1.5 |
| void | 1.5 | 0.8 | 1.0 | 0.8 | 1.0 |

### FR-00104: 怪獣ビジュアル生成 (Imagen 3)

| 項目             | 内容                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **説明**         | Imagen 3 で怪獣の戦闘シーンを動的に生成                                                 |
| **実装ファイル** | `src/app/api/kaiju/generate/route.ts`, `src/features/kaiju/hooks/useKaijuGeneration.ts` |
| **テスト**       | `tests/unit/features/kaiju/useKaijuGeneration.test.ts`                                  |
| **状態**         | ⬜ 未開始                                                                               |

**AC**:

| AC  | Given        | When                | Then                          |
| :-: | ------------ | ------------------- | ----------------------------- |
| AC1 | 怪獣選択時   | Imagen API呼出      | 怪獣画像が5秒以内に生成される |
| AC2 | Imagen失敗時 | タイムアウト/エラー | SVGフォールバック画像表示     |

### FR-00105: リアルタイムBGM (Lyria)

| 項目             | 内容                                                                              |
| ---------------- | --------------------------------------------------------------------------------- |
| **説明**         | 戦況に応じてBGMをLyriaで動的に生成                                                |
| **実装ファイル** | `src/app/api/music/generate/route.ts`, `src/features/music/hooks/useBattleBGM.ts` |
| **テスト**       | なし (統合テストで検証)                                                           |
| **状態**         | ⬜ 未開始                                                                         |

**AC**:

| AC  | Given        | When        | Then                               |
| :-: | ------------ | ----------- | ---------------------------------- |
| AC1 | バトル開始時 | BGM生成要求 | バトルBGM再生開始 10秒以内         |
| AC2 | Lyria失敗時  | エラー      | 静音で続行 (BGMなしでもゲーム進行) |

### FR-00106: バトルUI

| 項目             | 内容                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| **説明**         | HPバー・怪獣表示・ダメージエフェクト・ターン表示                                                       |
| **実装ファイル** | `src/features/battle/components/BattleArena.tsx`, `HPBar.tsx`, `DamageEffect.tsx`, `TurnIndicator.tsx` |
| **テスト**       | `tests/unit/features/battle/BattleArena.test.tsx`                                                      |
| **状態**         | ⬜ 未開始                                                                                              |

**AC**:

| AC  | Given        | When             | Then                                          |
| :-: | ------------ | ---------------- | --------------------------------------------- |
| AC1 | バトル画面   | 初期表示         | 2体の怪獣 + HPバー + ターン表示               |
| AC2 | ダメージ発生 | 攻撃結果反映     | HPバーアニメーション + ダメージ数値エフェクト |
| AC3 | クリティカル | 2倍ダメージ      | 画面シェイク + 大きいダメージ数値             |
| AC4 | 録音中       | マイクボタン押下 | 赤い脈動エフェクト + 波形ビジュアライザ       |

### FR-00107: ゲームフロー

| 項目             | 内容                                                |
| ---------------- | --------------------------------------------------- |
| **説明**         | タイトル→怪獣選択→バトル→リザルト の画面遷移        |
| **実装ファイル** | `src/features/game/components/GameStateMachine.tsx` |
| **テスト**       | `tests/unit/features/game/gameFlow.test.ts`         |
| **状態**         | ⬜ 未開始                                           |

**ゲームフロー**:

```
1. タイトル画面: 「KAIJU VOICE」ロゴ + 「START」ボタン
2. 選択画面: P1が怪獣選択 → P2が怪獣選択
3. バトル画面:
   a. 「P1のターン！叫べ！」表示
   b. P1が録音ボタン押下 → 5秒録音 → AI分析 → ダメージ計算 → HP更新
   c. 勝敗チェック → 決着なら4へ、続行ならP2ターンに
   d. P2も同様に実行
   e. ラウンド進行
4. リザルト画面: 勝者表示 + バトルサマリー + 「もう一度」ボタン
```

---

## 3. 依存性 & リスク

### 3.1 前提依存性

| 依存対象         | 必要項目                | 状態 |
| ---------------- | ----------------------- | :--: |
| `GEMINI_API_KEY` | Gemini + Imagen + Lyria |  ⏳  |
| マイク許可       | ブラウザ Permission     |  ⏳  |
| `@google/genai`  | SDK v1.41.0+            |  ✅  |

### 3.2 トップ 3 リスク

| リスク                | 影響 | 対応                                       |
| --------------------- | :--: | ------------------------------------------ |
| Gemini音声分析の遅延  |  高  | ローディングアニメーションで体感速度カバー |
| Imagen生成の遅延/失敗 |  中  | SVGフォールバック怪獣アイコン              |
| Lyria APIの利用制限   |  低  | BGMなしでもゲーム進行可能                  |

### 3.3 シーケンス図

#### バトルターンフロー

```
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌────────┐
│  Player  │     │   React  │     │ API Route │     │ Gemini │
└────┬─────┘     └────┬─────┘     └─────┬─────┘     └───┬────┘
     │                 │                  │                │
     │ 1. 録音ボタン   │                  │                │
     │────────────────>│                  │                │
     │                 │                  │                │
     │ 2. 5秒録音      │                  │                │
     │   (音声波形表示) │                  │                │
     │                 │                  │                │
     │                 │ 3. POST /api/voice/analyze        │
     │                 │─────────────────>│                │
     │                 │                  │                │
     │                 │                  │ 4. Gemini音声分析│
     │                 │                  │───────────────>│
     │                 │                  │                │
     │                 │                  │ 5. VoiceAnalysis│
     │                 │                  │<───────────────│
     │                 │                  │                │
     │                 │ 6. 攻撃結果      │                │
     │                 │<─────────────────│                │
     │                 │                  │                │
     │ 7. ダメージ表示  │                  │                │
     │   + HPバー更新   │                  │                │
     │<────────────────│                  │                │
     │                 │                  │                │
```

---

## 5. 怪獣プリセットデータ

| ID  | 名前      | 日本語名       | 属性    | 攻撃 | 防御 | 説明                           |
| --- | --------- | -------------- | ------- | :--: | :--: | ------------------------------ |
| 01  | Infernus  | インフェルヌス | fire    |  12  |  8   | 灼熱の怪獣。すべてを焼き尽くす |
| 02  | Glacius   | グレイシアス   | ice     |  8   |  12  | 氷の怪獣。絶対零度の守護者     |
| 03  | Voltarion | ボルタリオン   | thunder |  11  |  9   | 雷の怪獣。稲妻を纏う破壊者     |
| 04  | Terradon  | テラドン       | earth   |  9   |  11  | 大地の怪獣。揺るがぬ巨体       |
| 05  | Nihilus   | ニヒルス       | void    |  10  |  10  | 虚無の怪獣。全てを飲み込む     |

---

## 6. メッセージ定数

| メッセージキー          | テキスト                                   |
| ----------------------- | ------------------------------------------ |
| `game_title`            | KAIJU VOICE                                |
| `game_subtitle`         | 声で戦え、怪獣バトル                       |
| `game_start`            | スタート                                   |
| `select_title`          | 怪獣を選べ                                 |
| `select_player1`        | プレイヤー1 の番                           |
| `select_player2`        | プレイヤー2 の番                           |
| `battle_yourTurn`       | {name}のターン！叫べ！                     |
| `battle_recording`      | 録音中...                                  |
| `battle_analyzing`      | AI分析中...                                |
| `battle_damage`         | {damage} ダメージ！                        |
| `battle_critical`       | クリティカル！！                           |
| `battle_round`          | ラウンド {n}                               |
| `result_winner`         | {name} の勝利！                            |
| `result_playAgain`      | もう一度戦う                               |
| `error_micPermission`   | マイクの使用を許可してください             |
| `error_analysisTimeout` | 分析がタイムアウトしました。もう一度叫べ！ |
| `error_imagenFailed`    | 画像生成に失敗しました                     |

---

## 7. 変更履歴

| 日付       | バージョン | 変更内容 |
| ---------- | ---------- | -------- |
| 2026-02-21 | v1.0       | 初稿     |
