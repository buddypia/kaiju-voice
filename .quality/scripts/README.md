# Quality Gate Scripts

このディレクトリには、`Makefile`の品質検査ターゲットから呼び出すスクリプトが含まれます。

## SSOT 構造

```
Makefile (SSOT)           # 品質検査定義の唯一のソース
  └── .quality/scripts/   # 個別検証スクリプト
        ├── check_codegen.sh
        ├── check_gemini_schema.sh
        ├── check_arb_sync.sh
        └── check_test_exists.sh
```

## 使用方法

```bash
# 全体品質検査（コミット前必須）
make q.check

# 自動修正後の検査
make q.fix
```

## スクリプト一覧

| スクリプト               |  重大度  | 説明                                            |
| ------------------------ | :------: | ----------------------------------------------- |
| `check_codegen.sh`       | Critical | Freezed/Riverpod コード生成ファイルの最新化確認 |
| `check_gemini_schema.sh` | Critical | Edge Function Gemini 構造化出力の強制確認       |
| `check_arb_sync.sh`      |  Major   | ARB 多言語キーの同期確認                        |
| `check_test_exists.sh`   |  Major   | 変更されたファイルのテスト存在確認              |

## Exit Codes

| Code | 意味 |
| :--: | ---- |
| `0`  | PASS |
| `1`  | FAIL |

## 新しい検証の追加時

1. `.quality/scripts/check_xxx.sh` スクリプトを作成
2. `Makefile`にターゲットを追加 (q.xxx)
3. `q.critical` または `q.major.warn`に依存関係を追加

**SSOT 原則**: ルール定義と実行コマンドは `Makefile` にのみ存在します。
