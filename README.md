# KAIJU VOICE — 声で戦え、怪獣バトル

**叫べ。その声が、攻撃になる。**

Gemini APIのマルチモーダル能力をフル活用した、音声入力リアルタイムバトルゲーム。
プレイヤーがマイクに向かって叫ぶと、AIがその「迫力」「創造性」「感情」を分析し、ダメージに変換する。

[![KAIJU VOICE デモ](https://img.youtube.com/vi/uF3PV5CS03M/maxresdefault.jpg)](https://www.youtube.com/watch?v=uF3PV5CS03M)

---

## How It Works

```
🎤 プレイヤーが叫ぶ
    ↓
🧠 Gemini が音声を分析（迫力・創造性・感情）
    ↓
⚔️ 分析結果がダメージに変換
    ↓
🎙️ AI実況が熱い解説をリアルタイム音声で届ける
    ↓
💥 VFXが画面を彩る
```

## Gemini API Integration

本プロジェクトは **4つのGemini API** を組み合わせて使用しています。

| API                | モデル                         | 用途                                                                        |
| ------------------ | ------------------------------ | --------------------------------------------------------------------------- |
| **音声分析**       | `gemini-3-flash-preview`       | プレイヤーの叫び声を解析し、intensity / creativity / emotion をスコアリング |
| **AI実況 (TTS)**   | `gemini-2.5-flash-preview-tts` | バトルイベントに応じた熱い実況を音声で生成・再生                            |
| **AI対戦ロジック** | `gemini-2.0-flash`             | 戦況を読み、AIが感情的に攻撃を選択                                          |
| **怪獣画像生成**   | `Imagen 3`                     | 怪獣・ヒーローの画像を動的に生成                                            |

### 音声分析の仕組み

Gemini の Structured Output を活用し、音声から以下を抽出します：

```json
{
  "intensity": 85,
  "creativity": 72,
  "emotion": 90,
  "language": "mixed",
  "transcript": "ファイヤーーー！Burn everything!!",
  "attackType": "ultimate"
}
```

- 日英混在の叫びは **創造性ボーナス** が加算される
- 技名を叫ぶと `special`、詩的・多言語混在で `ultimate` に昇格

## Game Modes

| モード            | 説明                                                                              |
| ----------------- | --------------------------------------------------------------------------------- |
| **VS AI**         | Gemini が戦況を読んで攻撃してくる。HP低下時は必死に、優勢時は余裕の攻撃を繰り出す |
| **HERO vs KAIJU** | ヒーローと怪獣の対決。属性相性が戦略のカギ                                        |
| **PVP**           | 2人のプレイヤーが交互に叫んで対戦                                                 |

## Features

- **リアルタイム音声分析** — Web Speech API + Gemini でプレイヤーの声を即座に評価
- **AI実況** — プロレス中継のような熱い実況をTTSでリアルタイム生成
- **属性相性** — 火・氷・雷・土・虚無・光の6属性で相性倍率が変動
- **VFX演出** — 必殺技カットイン、パーティクル爆発、KO演出、勝利エフェクト
- **AIプリフェッチ** — プレイヤー録音中にAI攻撃を先読み生成し、体感遅延を最小化
- **波形ビジュアライザー** — 音声入力のリアルタイム波形表示

## Tech Stack

| カテゴリ   | 技術                               |
| ---------- | ---------------------------------- |
| Framework  | Next.js 16 / React 19              |
| Language   | TypeScript (strict)                |
| Styling    | Tailwind CSS 4                     |
| AI         | `@google/genai` + `@ai-sdk/google` |
| Animation  | Framer Motion                      |
| Validation | Zod                                |
| Testing    | Vitest + Testing Library           |

## Getting Started

```bash
# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.local
# GEMINI_API_KEY を設定

# 開発サーバー起動
npm run dev
```

http://localhost:3000 にアクセスしてゲーム開始。

## Architecture

```
src/
├── app/                  # Next.js App Router
│   └── api/              # Gemini API エンドポイント
│       ├── voice/analyze/     # 音声分析
│       ├── commentary/live/   # AI実況 (TTS)
│       ├── ai-opponent/attack/# AI対戦ロジック
│       └── kaiju/generate/    # 画像生成
├── features/             # Feature-First モジュール
│   ├── battle/           # バトルエンジン・ダメージ計算
│   ├── voice/            # 音声キャプチャ・波形取得
│   ├── commentary/       # 実況オーバーレイ
│   ├── ai-opponent/      # AI攻撃生成・プリフェッチ
│   ├── kaiju/            # 怪獣データ・表示
│   ├── music/            # BGM生成
│   └── vfx/              # ビジュアルエフェクト
└── shared/               # 共通ユーティリティ・定数
```

## License

MIT
