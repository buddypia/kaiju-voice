# 001 — KAIJU VOICE

> 声で戦う怪獣バトルゲーム

| 項目       | 値            |
| ---------- | ------------- |
| **状態**   | Done          |
| **タイプ** | NEW_FEATURE   |
| **優先度** | P0-MVP        |
| **進捗**   | 100% (7/7 FR) |
| **作成日** | 2026-02-21    |
| **完了日** | 2026-02-21    |

## 概要

プレイヤーが叫んだ言葉・感情・言語の創造性を Gemini が分析し、怪獣が戦う 2P ローカルバトルゲーム。

## 機能要件

| FR       | 名前                      | 状態 | 主要ファイル                                       |
| -------- | ------------------------- | :--: | -------------------------------------------------- |
| FR-00101 | 音声キャプチャ            | Done | `useVoiceCapture.ts`, `VoiceRecorder.tsx`          |
| FR-00102 | 音声分析 (Gemini)         | Done | `api/voice/analyze/route.ts`                       |
| FR-00103 | バトルエンジン            | Done | `useBattleEngine.ts`, `useGameState.ts`            |
| FR-00104 | 怪獣ビジュアル (Imagen 3) | Done | `api/kaiju/generate/route.ts`, `KaijuDisplay.tsx`  |
| FR-00105 | BGM (Lyria)               | Done | `api/music/generate/route.ts`, `useBattleBGM.ts`   |
| FR-00106 | バトルUI                  | Done | `HPBar.tsx`, `DamageEffect.tsx`, `BattleArena.tsx` |
| FR-00107 | ゲームフロー              | Done | `TitleScreen.tsx` ~ `ResultScreen.tsx`, `page.tsx` |

## 画面

| 画面     | ファイル                                        |
| -------- | ----------------------------------------------- |
| タイトル | `src/features/game/components/TitleScreen.tsx`  |
| 怪獣選択 | `src/features/game/components/SelectScreen.tsx` |
| バトル   | `src/features/game/components/BattleScreen.tsx` |
| リザルト | `src/features/game/components/ResultScreen.tsx` |

## API Routes

| エンドポイント             | 用途                               |
| -------------------------- | ---------------------------------- |
| `POST /api/voice/analyze`  | 音声 → Gemini 分析 → VoiceAnalysis |
| `POST /api/kaiju/generate` | Imagen 3 で怪獣画像生成            |
| `POST /api/music/generate` | Lyria RealTime でBGM生成           |

## テスト

| ファイル                  | テスト数 |
| ------------------------- | :------: |
| `useBattleEngine.test.ts` |    7     |
| `useGameState.test.ts`    |    9     |
| **合計**                  |  **16**  |

## 品質検証

| 検証         | 結果             |
| ------------ | ---------------- |
| `next build` | 成功             |
| `eslint`     | 0 エラー, 1 警告 |
| `vitest`     | 16/16 通過       |

## 文書

- [SPEC](SPEC-001-kaiju-voice.md)
- [CONTEXT](CONTEXT.json)
