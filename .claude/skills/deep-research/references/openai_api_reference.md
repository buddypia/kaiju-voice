# OpenAI Deep Research API 参照

## 概要

OpenAI Deep Researchは複雑な研究作業を実行するエージェント機能である。ウェブを探索して情報を収集し、多段階推論を通じて総合的なリサーチレポートを生成する。

## 公式文書

- [Deep Research Guide](https://platform.openai.com/docs/guides/deep-research)
- [OpenAI Cookbook - Deep Research](https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api)
- [o3-deep-research Model](https://platform.openai.com/docs/models/o3-deep-research)

## 使用可能なモデル

| モデル ID               | 説明                                         |
| ----------------------- | -------------------------------------------- |
| `o3-deep-research`      | 深層合成および高品質出力に最適化されたモデル |
| `o4-mini-deep-research` | 軽量化モデル、迅速な応答が必要な場合に適合   |

> 参考: モデル ID の後に日付バージョンが付く場合がある (例: `o3-deep-research-2025-06-26`)

## API 使用法

### 非同期バックグラウンドリクエスト (推奨, v2.0)

Deep Researchは長時間実行される可能性があるため `background=True` で非同期実行することが推奨される。

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY")

# 1. リサーチ開始 (即時返却)
response = client.responses.create(
    model="o3-deep-research",
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "リサーチテーマ"}]
        }
    ],
    reasoning={"summary": "auto"},
    tools=[{"type": "web_search_preview"}],
    background=True  # 非同期実行
)

response_id = response.id  # レスポンス ID 保存

# 2. 状態ポーリング
import time

while True:
    result = client.responses.retrieve(response_id)
    if result.status == "completed":
        # 結果抽出
        for block in result.output:
            if block.type == "message":
                for content in block.content:
                    if content.type == "output_text":
                        print(content.text)
        break
    elif result.status in ("failed", "cancelled"):
        print(f"Research failed: {result.status}")
        break
    time.sleep(15)  # 15秒間隔ポーリング
```

### 状態値

| 状態          | 説明           |
| ------------- | -------------- |
| `queued`      | 待機中         |
| `in_progress` | リサーチ進行中 |
| `completed`   | 完了           |
| `failed`      | 失敗           |
| `cancelled`   | キャンセル済み |

### 同期リクエスト (単純使用時)

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY")

response = client.responses.create(
    model="o3-deep-research",
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "リサーチテーマ"}]
        }
    ],
    reasoning={"summary": "auto"},
    tools=[{"type": "web_search_preview"}]
)
```

### ストリーミングリクエスト

```python
stream = client.responses.create(
    model="o3-deep-research",
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "リサーチテーマ"}]
        }
    ],
    reasoning={"summary": "auto"},
    tools=[{"type": "web_search_preview"}],
    stream=True
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
```

## 必須パラメータ

| パラメータ | タイプ | 説明                                             |
| ---------- | ------ | ------------------------------------------------ |
| `model`    | string | 使用するモデル ID                                |
| `input`    | array  | ユーザー入力メッセージ配列                       |
| `tools`    | array  | 使用するツール配列 (最低1つのデータソースが必要) |

## 選択的パラメータ

| パラメータ   | タイプ  | デフォルト値 | 説明                                              |
| ------------ | ------- | ------------ | ------------------------------------------------- |
| `reasoning`  | object  | -            | 推論オプション (`{"summary": "auto"}` 推奨)       |
| `stream`     | boolean | false        | ストリーミングモード有効化                        |
| `background` | boolean | false        | 非同期バックグラウンド実行 (長時間リサーチ時推奨) |

## レスポンス照会 API

### `client.responses.retrieve(response_id)`

`background=True` で生成されたレスポンスの状態と結果を照会する。

```python
result = client.responses.retrieve(response_id)
print(result.status)  # queued, in_progress, completed, failed, cancelled
```

## サポートツール (Tools)

Deep Researchは最低1つのデータソースが必要である:

### 1. Web Search

```python
{"type": "web_search_preview"}
```

ウェブ検索を通じて最新情報を収集する。

### 2. File Search (Vector Store)

```python
{
    "type": "file_search",
    "vector_store_ids": ["vs_xxx"]
}
```

内部文書を検索する。最大2つの vector store 接続可能。

### 3. Remote MCP Servers

```python
{
    "type": "mcp",
    "server_label": "my_server",
    "server_url": "https://example.com/mcp",
    "allowed_tools": ["tool_name"]
}
```

外部 MCP サーバーを通じてカスタムツール使用可能。

## レスポンス構造

```python
response.output[0].content[0].text  # メイン結果テキスト
response.output[0].summary[0].text  # 推論要約 (reasoning.summary 有効化時)
```

## ストリーミングイベント

| イベントタイプ                          | 説明                 |
| --------------------------------------- | -------------------- |
| `response.reasoning_summary_text.delta` | 推論要約テキスト増分 |
| `response.output_text.delta`            | 出力テキスト増分     |
| `response.completed`                    | レスポンス完了       |

## ChatGPTとの相違点

APIを通じたDeep ResearchはChatGPTバージョンと以下のような違いがある:

1. **明確化質問なし**: プロンプトを明確にするための追加質問をしない
2. **プロンプト再作成なし**: 入力そのままリサーチ開始
3. **完全なプロンプトが必要**: 全ての必要な情報を事前に含める必要がある

### 推奨プロンプト戦略

1. **プロンプト拡張器使用**: 軽量モデル(gpt-4.1等)で先にプロンプトを拡張
2. **詳細情報を含む**:
   - 希望する範囲 (時間、地域)
   - 比較ポイント
   - 希望する指標/メトリック
   - 好みの出典
   - 出力形式

## 使用推奨事例

**適合する場合:**

- 多段階推論が必要な複雑な研究
- 複数ソースからの情報合成
- 総合レポート作成
- 市場分析、技術動向調査

**不適合な場合:**

- 単純な事実確認
- 簡単なQ&A
- 短い対話

## コスト考慮事項

Deep Researchモデルは一般モデルよりコストが高い:

- より多くのトークン使用
- ウェブ検索コスト追加
- 長い実行時間

単純作業には一般モデルの使用を推奨する。

## エラーコード

| コード | 説明               | 解決策                           |
| ------ | ------------------ | -------------------------------- |
| 401    | 認証失敗           | API キー確認                     |
| 429    | リクエスト上限超過 | しばらく後に再試行               |
| 404    | モデルなし         | モデル ID 確認、アクセス権限確認 |
| 500    | サーバーエラー     | 再試行                           |

## 関連リンク

- [OpenAI Platform](https://platform.openai.com/)
- [API Reference](https://platform.openai.com/docs/api-reference)
- [Deep Research FAQ](https://help.openai.com/en/articles/10500283-deep-research-faq)
