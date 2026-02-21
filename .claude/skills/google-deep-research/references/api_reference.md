# Google Deep Research API Reference

## Overview

Deep Researchは複雑な長期実行コンテキスト収集および合成作業を実行するよう設計されたエージェントである。
Gemini APIを通じてアクセス可能であり、Interactions APIを通じてのみ使用できる。

## API エンドポイント

### Base URL

```
https://generativelanguage.googleapis.com/v1beta
```

### エージェントモデル

```
deep-research-pro-preview-12-2025
```

## API 使用法

### 1. リサーチ開始 (POST /interactions)

```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/interactions" \
  -H "Content-Type: application/json" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -d '{
    "input": "Research the history of Google TPUs.",
    "agent": "deep-research-pro-preview-12-2025",
    "background": true
  }'
```

**Request Body:**

| フィールド | タイプ  | 必須 | 説明                                      |
| ---------- | ------- | ---- | ----------------------------------------- |
| input      | string  | Yes  | リサーチテーマまたは質問                  |
| agent      | string  | Yes  | エージェントモデル ID                     |
| background | boolean | Yes  | バックグラウンド実行可否 (常に true 推奨) |

**Response:**

```json
{
  "id": "interactions/abc123",
  "status": "in_progress"
}
```

### 2. 状態確認 (GET /interactions/{id})

```bash
curl -X GET "https://generativelanguage.googleapis.com/v1beta/interactions/INTERACTION_ID" \
  -H "x-goog-api-key: $GEMINI_API_KEY"
```

**Response (進行中):**

```json
{
  "id": "interactions/abc123",
  "status": "in_progress"
}
```

**Response (完了):**

```json
{
  "id": "interactions/abc123",
  "status": "completed",
  "outputs": [
    {
      "text": "# Research Report\n\n..."
    }
  ]
}
```

**Response (失敗):**

```json
{
  "id": "interactions/abc123",
  "status": "failed",
  "error": "Error message"
}
```

## Python SDK

### インストール

```bash
pip install google-genai
```

### 基本使用法

```python
import time
from google import genai

client = genai.Client()

# リサーチ開始
interaction = client.interactions.create(
    input="Research the history of Google TPUs.",
    agent='deep-research-pro-preview-12-2025',
    background=True
)

print(f"Research started: {interaction.id}")

# 結果ポーリング
while True:
    interaction = client.interactions.get(interaction.id)
    if interaction.status == "completed":
        print(interaction.outputs[-1].text)
        break
    elif interaction.status == "failed":
        print(f"Research failed: {interaction.error}")
        break
    time.sleep(10)
```

## 制限事項

| 項目             | 制限                       |
| ---------------- | -------------------------- |
| 最大実行時間     | 60分                       |
| 一般的な完了時間 | 20分以内                   |
| オーディオ入力   | サポートされていない       |
| 基本ツール       | google_search, url_context |

## 状態値

| 状態          | 説明           |
| ------------- | -------------- |
| `in_progress` | リサーチ進行中 |
| `completed`   | リサーチ完了   |
| `failed`      | リサーチ失敗   |

## 注意事項

1. **background=True 必須**: Deep Researchは長期実行作業であるため常にバックグラウンドモードで実行する必要がある。
2. **ポーリング間隔**: 10秒間隔でポーリングすることが推奨される。
3. **generate_content 未サポート**: Deep ResearchはInteractions APIを通じてのみアクセス可能である。
4. **API キー**: Google AI Studioで発行されたGEMINI_API_KEYが必要である。

## 参考リンク

- [Gemini Deep Research Agent 公式文書](https://ai.google.dev/gemini-api/docs/deep-research)
- [Google AI Studio](https://aistudio.google.com/)
- [Build with Gemini Deep Research ブログ](https://blog.google/technology/developers/deep-research-agent-gemini-api/)
