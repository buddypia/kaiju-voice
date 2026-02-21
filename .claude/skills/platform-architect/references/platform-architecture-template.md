# {Project Name} Platform Architecture

> **Arc42ベース** | **バージョン**: {version} | **最終更新**: {date}

本文書は{project_name}プラットフォームの全体アーキテクチャを、Arc42テンプレートに基づき10セクションで記述する。

---

## 1. Introduction & Goals（導入と目標）

### 1.1 プロジェクト概要

{プロジェクトの概要説明}

### 1.2 品質目標

| 優先度 | 品質属性 | 目標   |
| :----: | -------- | ------ |
|   1    | {属性}   | {目標} |
|   2    | {属性}   | {目標} |
|  ...   | ...      | ...    |

### 1.3 ステークホルダー

| ステークホルダー | 関心事   |
| ---------------- | -------- |
| {名前}           | {関心事} |

---

## 2. Constraints（制約）

> **機械可読制約**: [constraints.json](./constraints.json)

### 2.1 技術的制約

| 制約   | 詳細   | 根拠       |
| ------ | ------ | ---------- |
| {制約} | {詳細} | {PADR-NNN} |

### 2.2 ビジネス制約

| 制約   | 詳細   |
| ------ | ------ |
| {制約} | {詳細} |

### 2.3 組織的制約

| 制約   | 詳細   |
| ------ | ------ |
| {制約} | {詳細} |

---

## 3. Context & Scope（コンテキストとスコープ）

> **詳細図**: [C4 Platform Diagrams](./c4/platform-c4.md)

### 3.1 System Context（Level 1）

{システムコンテキスト図または説明}

### 3.2 外部システム

| 外部システム | 役割   | 通信         |
| ------------ | ------ | ------------ |
| {システム}   | {役割} | {プロトコル} |

---

## 4. Solution Strategy（ソリューション戦略）

| PADR                            | 決定       | 要約   |
| ------------------------------- | ---------- | ------ |
| [PADR-NNN](./adr/PADR-NNN-*.md) | {タイトル} | {要約} |

### 4.1 Two-Layer Architecture

```
Layer 1: Platform Architecture（本文書）
├── 全機能に適用される共通制約
├── constraints.json で機械可読化
└── 更新頻度: 年1-2回

Layer 2: Feature Architecture（各機能ADR）
├── 機能ごとの個別アーキテクチャ決定
├── docs/features/<id>-<name>/ADR-<id>.md
└── Platform制約からの逸脱にはATAM Lite正当化が必要
```

---

## 5. Building Blocks View（構成要素ビュー）

> **詳細図**: [C4 Container Diagram](./c4/platform-c4.md#level-2-container)

### 5.1 フロントエンド

{フロントエンドのフォルダ構造と説明}

### 5.2 バックエンド

{バックエンドコンポーネントの一覧}

---

## 6. Runtime View（ランタイムビュー）

{主要ユースケースのシーケンス図やフロー説明}

---

## 7. Deployment View（デプロイビュー）

{インフラ構成図と環境一覧}

---

## 8. Cross-Cutting Concepts（横断的関心事）

> **詳細**: [cross-cutting/](./cross-cutting/) ディレクトリ

### 8.1 エラーハンドリング

> [error-handling.md](./cross-cutting/error-handling.md)

### 8.2 ログ

> [logging.md](./cross-cutting/logging.md)

### 8.3 セキュリティ

> [security.md](./cross-cutting/security.md)

---

## 9. Architecture Decisions（アーキテクチャ決定）

### 9.1 Platform ADR 一覧

| ID       | タイトル                          | ステータス | カテゴリ   |
| -------- | --------------------------------- | ---------- | ---------- |
| PADR-NNN | [{タイトル}](./adr/PADR-NNN-*.md) | Accepted   | {カテゴリ} |

### 9.2 Architecture Contract Pattern

{ADR + constraints.json 二重構造の説明}

---

## 10. Tech Radar（技術レーダー）

> **詳細**: [tech-radar.md](./tech-radar.md)

{Tech Radarサマリー}

---

## 参照

- [CLAUDE.md]({path}) - プロジェクトガイドライン
- [constraints.json](./constraints.json) - 機械可読制約契約
- [tech-stack-rules.md]({path}) - 技術スタック詳細

---

**文書ステータス**: Active
**メンテナンス**: Platform Architecture変更時に同期更新（年1-2回）
