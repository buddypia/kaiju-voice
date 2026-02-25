# 【準優勝】Gemini 3 Tokyo Hackathon：Gemini 3をエンジンにした独自「Agent Skills」パイプラインで怪獣カードバトルを作った裏側

こんにちは、[あなたの名前/ハンドルネーム]です。

先日開催されたCerebral Valley主催の「Gemini 3 Tokyo Hackathon」に参加し、我々のチームが開発した『怪獣カードバトル（KAIJU VOICE）』が見事**準優勝（2nd Place）**を獲得しました！🥈✨

本記事では、ハッカソンという超短期間で、最新のGemini API群を組み合わせて高品質なWebゲームを完成させた裏側を公開します。
特に、単なるチャットUIでのコード生成を脱却し、**Geminiの圧倒的な推論力とコンテキスト長を活かした「Agent Skills」駆動の自律型開発パイプライン**をどう構築したのか、その全貌をご紹介します。

## 開発したプロダクト『KAIJU VOICE — 声で戦え、怪獣バトル』

今回開発したのは、Gemini APIのマルチモーダル能力をフル活用した、音声入力リアルタイムバトルゲームです。

### ゲーム画面

![ゲーム画面1](./game-screenshot/1.png)
![ゲーム画面2](./game-screenshot/2.png)
![ゲーム画面3](./game-screenshot/3.png)
![ゲーム画面4](./game-screenshot/4.png)
![ゲーム画面5](./game-screenshot/5.png)

プレイヤーがマイクに向かって叫ぶと、AIがその「迫力」「創造性」「感情」を即座に分析し、ダメージに変換して怪獣に攻撃を与えます。

### 活用した3つのGemini API

1. **音声分析** (`gemini-3-flash-preview`): プレイヤーの叫び声を解析し、感情や創造性をJSON構造化データでスコアリング。
2. **AI対戦ロジック** (`gemini-3-flash-preview`): 戦況を読み、AIが感情的に攻撃を選択。
3. **怪獣画像生成** (`Imagen 3`): 怪獣・ヒーローの画像を動的に生成。

---

## なぜ「普通のAIコーディング」ではダメだったのか

ハッカソンにおいて、ブラウザのチャット画面に「〇〇を作って」とお願いするのはもはや当たり前です。
しかし、今回のように「Next.js 16 (App Router)」「TypeScript (strict)」「VFXアニメーション」「複数AIバックエンドの統合」といった複雑なプロジェクトになると、以下の壁にぶつかります。

1.  **AIが以前のコンテキスト（前提条件や仕様）を忘れる**
2.  **アーキテクチャの一貫性が崩壊する**
3.  **バグを直そうとして別のバグを生むループに陥る**

そこで私たちは、チャットUIに頼るのではなく、リポジトリ内に**「Geminiを自律的に動かすためのAgent Skillsパイプライン」**を構築し、Geminiに開発そのものを”指揮”させるアプローチをとりました。

---

## 準優勝を導いたGemini Agentパイプライン 4つのキーポイント

私たちのプロジェクトの真のコアは、ソースコード（`src/`）ではなく、Geminiエージェントを自動化・統制する基盤ディレクトリ（`.agents/` や `.quality/`）にあります。

### Key Point 1: YAMLで定義された自律型AIワークフロー (`.agents/pipelines/`)

AIに「適当にコードを書いて」と丸投げするのではなく、人間が定義したプロセスに沿ってGeminiを自律実行させる仕組みを作りました。

パイプラインディレクトリには、タスクごとのワークフローをYAMLで定義しています。

```yaml
# .agents/pipelines/new-feature.yaml の一部抜粋
steps:
  architect:
    skill: feature-architect
    model: gemini-3-pro
    outputs: [BRIEF.md, CONTEXT.json]
  spec:
    skill: feature-spec-generator
    model: gemini-3-flash
    outputs: [SPEC-*.md, screens/*.md]
  readiness_gate:
    type: gate
    checks: [schema_validation, upstream_contract]
  implement:
    skill: feature-implementer
    model: gemini-3-flash
    tdd: true # テスト駆動開発を強制
```

Geminiは「要件定義 → 仕様書生成 → 品質ゲート（Readiness Gate） → TDDでの実装」といったステップを、このYAMLに沿ってステップ・バイ・ステップで進行します。Gemini 3の高い指示追従能力（Instruction Following）により、この厳格なワークフローを逸脱することなく実行できます。

### Key Point 2: 専門特化の「Agent Skills」による分業制 (`.agents/skills/`)

1つの巨大なプロンプトにすべてを詰め込むと、いかにGemini 3といえども精度が落ちます。そこで、AIに役割（人格）を与えるための**「Agent Skills（エージェントスキル）」**を約50種類定義しました。

- `feature-architect`: 機能全体のアーキテクチャを設計する専門家
- `ui-approval-gate`: UI/UXの観点から生成されたコードを厳しくレビューするゲートキーパー
- `domain-modeler`: ドメイン駆動設計（DDD）に基づくモデル定義を行う

エージェントのオーケストレーターは、現在のタスクに応じて必要な「Skill」を動的にActivate（有効化）します。
複雑なアーキテクチャ設計には推論力の高い **Gemini 3 Pro** を、大量のコード生成やテスト修正の高速イテレーションには爆速の **Gemini 3 Flash** を呼び出すなど、Skillごとに最適なGeminiモデルをルーティングしています。

### Key Point 3: SSOT駆動設計とGeminiの「超長文コンテキスト」の融合

AI開発における最大の敵は「仕様と実装の乖離」です。
これを防ぐため、我々は `docs/features/` 配下のMarkdownやJSONを**SSOT（Single Source of Truth：単一の信頼できる情報源）**と定め、コードよりも先に更新するルールを徹底しました。

ここで火を噴くのが、**Geminiの「100万トークンを超える超長文コンテキストウィンドウ」**です。

```json
// CONTEXT.json の例
{
  "feature_id": "001-kaiju-voice",
  "quick_resume": {
    "current_state": "Implementing",
    "next_actions": ["音声分析APIの実装"]
  },
  "progress": { "percentage": 60 }
}
```

Agentがタスクを再開する際、Geminiの巨大なコンテキストウィンドウを利用して、この `CONTEXT.json` だけでなく、関連する仕様書、アーキテクチャ制約ルール（`constraints.json`）、さらには既存コードベースの大部分を一気に丸ごと読み込ませます。
これにより、「AIが仕様を忘れる」問題は完全に消滅し、一貫性のある高度な実装が可能になりました。

### Key Point 4: 妥協なき二重の自動品質管理（Quality Gate）と自己修復

生成されたコードが本当に動くのか？それを人間が都度レビューするのは非効率の極みです。
我々は「実装前」と「実装後」に二重の品質ゲート（Quality Gate）を設けました。

1.  **Readiness Gate（実装前）**:
    実装に入る前に、自動生成された仕様書がプロジェクトの制約を満たしているかを `.quality/scripts/validate_spec.py` 等で機械的に検証します。
2.  **Quality Gate（実装後）**:
    実装が終わると自動的に `make q.check` が走り、静的解析（ESLint）やテスト（Vitest）、依存方向の検証を行います。

もしエラーが出た場合、そのエラーログをGemini 3 Flashに投げ返します。Flashの圧倒的なスピードにより、数秒で**自己修復（Self-Healing）ループ**が回り、エラーを解消したコードが再提出されます。この高速な試行錯誤こそが、複雑なゲームを3日で完成させた原動力です。

---

## おわりに：Gemini 3が切り拓くAgentic SWEの未来

今回、Gemini 3という最先端の強力なモデル（Proの深い推論力とFlashの圧倒的なスピード、そして巨大なコンテキスト）と、自分たちで組み上げたAgent Skillsパイプラインを組み合わせることで、「人間は要件定義とパイプラインの指揮に集中し、設計・実装・テストはGeminiエージェントが自律的に行う」というソフトウェア開発の未来の形を体現できました。

単なる「チャットAIによるコーディング支援」を超えた、**「GeminiをエンジンとしたAgentic SWE（自律型ソフトウェアエンジニアリング）」**の有効性が、ハッカソン準優勝という結果で証明されたと感じています。

素晴らしい場を提供してくださったCerebral Valleyの皆様、関係者の皆様、本当にありがとうございました！

（※リポジトリを公開できる場合はGitHubリンクを記載。難しければTwitterのフォローを促すなど）
