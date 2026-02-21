# ============================================================
# Hackathon Project - Quality Gate (SSOT)
# ============================================================
#
# このファイルが品質検査の**唯一の定義**です。
# 他のファイル(SKILL.md等)はこのファイルを参照のみします。
#
# 使い方:
#   make q.check      # 全体品質検査 (コミット前必須)
#   make q.fix        # 自動修正後検査
#   make help         # ヘルプ
#
# 深刻度 (3-Tier):
#   Critical - 失敗時コミット/PR不可 (q.critical)
#   Major    - 警告表示、進行可能 (q.major.warn)
#   Info     - 参考情報のみ (q.info)
#
# ============================================================

.PHONY: q.check q.fix q.critical q.major.warn q.info help
.PHONY: q.analyze q.format q.format.check q.test q.test-exists
.PHONY: q.check-architecture q.ui-flow q.docs-consistency q.build q.coverage
.PHONY: spec.validate spec.validate-all
.PHONY: codegen codegen.check

.DEFAULT_GOAL := help

# ============================================================
# コマンド設定 (必要に応じてオーバーライド)
# 例: make q.analyze ANALYZE_CMD="pnpm lint"
# ============================================================
ANALYZE_CMD ?= npm run lint
TEST_CMD ?= npm test
COVERAGE_CMD ?= npm run test:coverage
FORMAT_CHECK_CMD ?= npx --no-install prettier --check .
FORMAT_FIX_CMD ?= npx --no-install prettier --write .
AUTO_FIX_CMD ?= npm run lint -- --fix
BUILD_CMD ?= npm run build

# ============================================================
# メインターゲット
# ============================================================

## 全体品質検査 (Critical必須 + Major警告 + Info参考)
q.check: q.critical q.major.warn q.info
	@echo ""
	@echo "✅ Quality Gate PASSED"
	@echo ""

## 自動修正後品質検査
q.fix:
	@echo "🔧 Applying auto-fixes..."
	@echo ""
	@echo ">> $(AUTO_FIX_CMD)"
	@$(AUTO_FIX_CMD)
	@echo ""
	@echo ">> $(FORMAT_FIX_CMD)"
	@$(FORMAT_FIX_CMD)
	@echo ""
	@echo "🔄 Re-checking..."
	@$(MAKE) q.check

# ============================================================
# Critical Checks (失敗時コミット/PR不可)
# ============================================================

## Critical全体実行
q.critical: q.format.check q.analyze q.check-architecture q.ui-flow codegen.check q.docs-consistency q.test q.build
	@echo "✅ All critical checks passed"

## コードフォーマット検査 (修正なし、確認のみ)
## - 一貫したコードスタイル維持
q.format.check:
	@echo "📝 [Critical] Checking code format..."
	@$(FORMAT_CHECK_CMD) 2>/dev/null || \
		(echo "❌ Format check failed. Run: make q.format" && exit 1)

## 静的分析 / リント + セキュリティ (eslint-plugin-security)
## - コンパイルエラー、型エラー、lint違反、セキュリティパターン検知
q.analyze:
	@echo "🔍 [Critical] Running analyze/lint + security..."
	@$(ANALYZE_CMD)

## Feature-Firstアーキテクチャ検証
## - 他のFeature内部直接import禁止
## - Shared → Feature依存性検査
q.check-architecture:
	@echo "🏗️  [Critical] Feature-First アーキテクチャ検証..."
	@if [ -f ./scripts/check_architecture.sh ]; then \
		./scripts/check_architecture.sh; \
	else \
		echo "⚠️  Architecture check script not found (skipped)"; \
	fi

## UI Flow Graph検証
## - ui-flow.json の構造・整合性検証（12項目）
q.ui-flow:
	@echo "🌊 [Critical] UI Flow Graph検証..."
	@python3 ./scripts/validate_ui_flow.py docs/ui-flow/ui-flow.json

## ドキュメント-実装整合性検証 [Critical]
## - src/features/ と docs/features/ の完全対応
## - SPEC/CONTEXT.json 構造検証
## - index.md 鮮度検証
q.docs-consistency:
	@echo "📝 [Critical] ドキュメント-実装整合性検証..."
	@python3 ./scripts/validate_docs_consistency.py

## テスト実行 [Critical]
## - 全ユニット/統合テスト通過必須
q.test:
	@echo "🧪 [Critical] Running tests..."
	@$(TEST_CMD)

## ビルド実行 [Critical]
## - プロダクションビルド成功必須 (Google DoD準拠)
q.build:
	@echo "🏗️  [Critical] Building project..."
	@$(BUILD_CMD)

# ============================================================
# Major Checks (警告表示、進行可能)
# ============================================================

## Major全体実行 (失敗しても続行)
q.major.warn:
	@echo ""
	@echo "📋 [Major] Running recommended checks..."
	@$(MAKE) q.test-exists 2>/dev/null || echo "⚠️  Some test files missing"
	@$(MAKE) q.coverage 2>/dev/null || echo "⚠️  Coverage below threshold"
	@echo ""

## テストファイル存在確認
## - 変更されたモジュールに対応するテストファイル存在確認
q.test-exists:
	@if [ -f ./.quality/scripts/check_test_exists.sh ]; then \
		./.quality/scripts/check_test_exists.sh; \
	else \
		echo "⚠️  Test existence check script not found (skipped)"; \
	fi

## カバレッジ閾値検証 [Major]
## - v8プロバイダー: statements/functions/lines >= 40%, branches >= 30%
## - Coverage Ratchet: 閾値は段階的に引き上げ (vitest.config.ts で管理)
q.coverage:
	@echo "📊 [Major] Running coverage check..."
	@$(COVERAGE_CMD)

# ============================================================
# Info (参考情報のみ)
# ============================================================

## Info出力 (常に成功)
q.info:
	@echo ""
	@echo "ℹ️  [Info] Quality summary"
	@echo "   Tests:        npm test"
	@echo "   Coverage:     npm run test:coverage"
	@echo "   Build:        npm run build"
	@echo "   Lint+Security: npm run lint (includes eslint-plugin-security)"
	@echo ""

# ============================================================
# 個別修正コマンド
# ============================================================

## コードフォーマット適用
q.format:
	@echo "📝 Formatting code..."
	@$(FORMAT_FIX_CMD)

# ============================================================
# SPEC文書検証
# ============================================================

# スクリプトパス
SPEC_VALIDATOR := .claude/skills/spec-validator/scripts/validate.py

## 単一SPEC検証
## Usage: make spec.validate SPEC=docs/features/001-xxx/SPEC-001.md
## Usage: make spec.validate SPEC=001
spec.validate:
ifndef SPEC
	@echo "❌ Error: SPECファイルまたは機能番号を指定してください"
	@echo ""
	@echo "Usage:"
	@echo "  make spec.validate SPEC=docs/features/029-xxx/SPEC-029.md"
	@echo "  make spec.validate SPEC=029"
	@exit 1
endif
	@echo "🔍 Validating SPEC: $(SPEC)"
	@python3 $(SPEC_VALIDATOR) $(SPEC)

## 全体SPEC検証
spec.validate-all:
	@echo "🔍 Validating all SPEC files..."
	@python3 $(SPEC_VALIDATOR) --all
	@echo ""
	@echo "✅ SPEC validation complete"

# ============================================================
# Codegen (ui-flow.json → コード + 図表)
# ============================================================

## SSOT からコード生成
codegen:
	@echo "🔄 Generating from SSOT (ui-flow.json)..."
	@npm run codegen

## Codegen 鮮度チェック [Critical]
codegen.check:
	@echo "🔍 [Critical] Codegen freshness check..."
	@npm run codegen:check

# ============================================================
# ヘルプ
# ============================================================

help:
	@echo ""
	@echo "Hackathon Project - Quality Gate Commands"
	@echo "====================================="
	@echo ""
	@echo "メインコマンド:"
	@echo "  make q.check     全体品質検査 (コミット前必須)"
	@echo "  make q.fix       自動修正後検査"
	@echo ""
	@echo "Critical (失敗時コミット/PR不可):"
	@echo "  make q.format.check      コードフォーマット確認"
	@echo "  make q.analyze           静的分析 + セキュリティ"
	@echo "  make q.check-architecture アーキテクチャ検証"
	@echo "  make q.ui-flow           UI Flow Graph検証"
	@echo "  make q.docs-consistency  ドキュメント-実装整合性検証"
	@echo "  make q.test              テスト実行"
	@echo "  make q.build             ビルド実行"
	@echo ""
	@echo "Major (警告表示、進行可能):"
	@echo "  make q.test-exists       テストファイル存在確認"
	@echo "  make q.coverage          カバレッジ閾値検証"
	@echo ""
	@echo "修正コマンド:"
	@echo "  make q.format    コードフォーマット適用"
	@echo ""
	@echo "SPEC検証:"
	@echo "  make spec.validate SPEC=<path|id>  単一SPEC検証"
	@echo "  make spec.validate-all             全体SPEC検証"
	@echo ""
	@echo "Deploy:"
	@echo "  make deploy              Cloud Run デプロイ (品質ゲート付き)"
	@echo "  make deploy.dry-run      dry-run (デプロイせず確認のみ)"
	@echo "  make deploy.skip-checks  品質チェック省略 (緊急時のみ)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker.build        Docker イメージビルド"
	@echo "  make docker.run          ローカル実行 (GEMINI_API_KEY=xxx)"
	@echo "  make docker.push         Artifact Registry へ push"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra.init          Terraform 初期化"
	@echo "  make infra.plan          Terraform Plan (dry-run)"
	@echo "  make infra.apply         Terraform Apply"
	@echo "  make infra.destroy       Terraform Destroy"
	@echo "  make infra.output        Terraform Output 表示"
	@echo ""

# ============================================================
# Deploy ターゲット (Cloud Run)
# ============================================================
.PHONY: deploy deploy.dry-run deploy.skip-checks

## Cloud Run デプロイ (品質ゲート付き)
deploy:
	@./scripts/deploy.sh

## デプロイ dry-run (ビルド確認のみ)
deploy.dry-run:
	@./scripts/deploy.sh --dry-run

## デプロイ (品質チェック省略 - 緊急時のみ)
deploy.skip-checks:
	@./scripts/deploy.sh --skip-checks

# ============================================================
# Docker ターゲット
# ============================================================
.PHONY: docker.build docker.run docker.push

DOCKER_IMAGE ?= hackathon-project
DOCKER_TAG ?= latest

## Docker イメージビルド
docker.build:
	@echo "🐳 Building Docker image..."
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

## ローカル Docker 実行
## Usage: make docker.run GEMINI_API_KEY=your-key
docker.run:
ifndef GEMINI_API_KEY
	@echo "❌ Error: GEMINI_API_KEY を指定してください"
	@echo "Usage: make docker.run GEMINI_API_KEY=your-key"
	@exit 1
endif
	@echo "🐳 Running Docker container..."
	docker run --rm -p 3000:3000 \
		-e GEMINI_API_KEY=$(GEMINI_API_KEY) \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

## Artifact Registry へ push
## Usage: make docker.push GCP_PROJECT_ID=xxx REGION=asia-northeast1
docker.push:
ifndef GCP_PROJECT_ID
	@echo "❌ Error: GCP_PROJECT_ID を指定してください"
	@exit 1
endif
	$(eval REGION ?= asia-northeast1)
	$(eval REPO_URL := $(REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/$(DOCKER_IMAGE))
	@echo "🐳 Tagging and pushing to Artifact Registry..."
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(REPO_URL)/$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(REPO_URL)/$(DOCKER_IMAGE):$(DOCKER_TAG)

# ============================================================
# Infrastructure ターゲット (Terraform)
# ============================================================
.PHONY: infra.init infra.plan infra.apply infra.destroy infra.output

TF_DIR := terraform

## Terraform 初期化
## Usage: make infra.init GCP_PROJECT_ID=xxx
infra.init:
ifndef GCP_PROJECT_ID
	@echo "❌ Error: GCP_PROJECT_ID を指定してください"
	@exit 1
endif
	@echo "🏗️  Initializing Terraform..."
	cd $(TF_DIR) && terraform init -backend-config="bucket=$(GCP_PROJECT_ID)-tfstate"

## Terraform Plan (dry-run)
infra.plan:
	@echo "🏗️  Running Terraform plan..."
	cd $(TF_DIR) && terraform plan -out=tfplan

## Terraform Apply
infra.apply:
	@echo "🏗️  Applying Terraform changes..."
	cd $(TF_DIR) && terraform apply tfplan

## Terraform Destroy (要確認)
infra.destroy:
	@echo "⚠️  Destroying infrastructure..."
	cd $(TF_DIR) && terraform destroy

## Terraform Output 表示
infra.output:
	@cd $(TF_DIR) && terraform output
