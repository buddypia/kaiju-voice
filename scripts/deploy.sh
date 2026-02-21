#!/bin/bash
# ============================================================
# Hackathon Project - Cloud Run Deploy Script
# ============================================================
#
# gcloud CLI ベースの軽量デプロイスクリプト。
# Terraform不要、--source . でソースから直接デプロイ。
# デプロイ成功時に docs/deployments/DEPLOY-LOG.md へ自動記録。
#
# Usage:
#   ./scripts/deploy.sh                    # デフォルト設定でデプロイ
#   ./scripts/deploy.sh --skip-checks      # 品質チェック省略
#   ./scripts/deploy.sh --dry-run          # ビルドのみ (デプロイしない)
#   ./scripts/deploy.sh --project xxx      # プロジェクト指定
#   ./scripts/deploy.sh --region xxx       # リージョン指定
#   ./scripts/deploy.sh --service xxx      # サービス名指定
#
# ============================================================

set -euo pipefail

# プロジェクトルート (このスクリプトの親ディレクトリの親)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ============================================================
# デフォルト設定
# ============================================================
GCP_PROJECT="${GCP_PROJECT:?GCP_PROJECT 環境変数を設定してください}"
GCP_REGION="${GCP_REGION:-asia-northeast1}"
SERVICE_NAME="${SERVICE_NAME:-hackathon-project}"
SKIP_CHECKS=false
DRY_RUN=false
ALLOW_UNAUTH="--allow-unauthenticated"

# デプロイログ
DEPLOY_LOG="$PROJECT_ROOT/docs/deployments/DEPLOY-LOG.md"

# ============================================================
# 引数パース
# ============================================================
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-checks)
      SKIP_CHECKS=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --project)
      GCP_PROJECT="$2"
      shift 2
      ;;
    --region)
      GCP_REGION="$2"
      shift 2
      ;;
    --service)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --no-allow-unauthenticated)
      ALLOW_UNAUTH=""
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --skip-checks                品質チェック省略"
      echo "  --dry-run                    ビルドのみ (デプロイしない)"
      echo "  --project <id>               GCPプロジェクトID (default: $GCP_PROJECT)"
      echo "  --region <region>            リージョン (default: $GCP_REGION)"
      echo "  --service <name>             サービス名 (default: $SERVICE_NAME)"
      echo "  --no-allow-unauthenticated   認証必須に変更"
      echo "  -h, --help                   このヘルプを表示"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ============================================================
# ユーティリティ
# ============================================================
log_step() { echo ""; echo "== $1"; echo ""; }
log_ok()   { echo "  [OK] $1"; }
log_warn() { echo "  [WARN] $1"; }
log_fail() { echo "  [FAIL] $1"; exit 1; }

# ============================================================
# Phase 1: Pre-flight
# ============================================================
log_step "Phase 1: Pre-flight"

# gcloud CLI チェック
if ! command -v gcloud &> /dev/null; then
  log_fail "gcloud CLI がインストールされていません"
fi
log_ok "gcloud CLI found"

# gcloud 認証チェック
if ! gcloud auth print-access-token &> /dev/null 2>&1; then
  log_fail "gcloud 未認証です。'gcloud auth login' を実行してください"
fi
log_ok "gcloud authenticated"

# Git 情報取得
GIT_COMMIT=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_MSG=$(git -C "$PROJECT_ROOT" log -1 --pretty=format:"%s" 2>/dev/null || echo "")

# Git status チェック
if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null)" ]]; then
  log_warn "uncommitted changes があります"
  git -C "$PROJECT_ROOT" status --short
  echo ""
else
  log_ok "working tree clean"
fi

# 品質ゲート
QUALITY_GATE="PASSED"
if [[ "$SKIP_CHECKS" == "false" ]]; then
  log_step "Running quality gate (make q.critical)..."
  if ! make -C "$PROJECT_ROOT" q.critical; then
    log_fail "品質ゲート失敗。修正後に再実行してください (or --skip-checks)"
  fi
  log_ok "Quality gate passed"
else
  QUALITY_GATE="SKIPPED"
  log_warn "品質チェックをスキップしました (--skip-checks)"
fi

# ============================================================
# Standalone バンドル検証 (sucrase NFT チェック)
# ============================================================
log_step "Standalone バンドル検証"

# next.config.ts に serverExternalPackages: ['sucrase'] が設定されているか
if grep -q "serverExternalPackages.*sucrase" "$PROJECT_ROOT/next.config.ts" 2>/dev/null; then
  log_ok "next.config.ts: serverExternalPackages に sucrase 設定あり"
else
  log_fail "next.config.ts に serverExternalPackages: ['sucrase'] が未設定です。sandbox/serve のトランスパイルが Cloud Run で失敗します"
fi

# ローカルビルドで standalone 出力の sucrase 存在を検証
log_step "ローカルビルド検証 (npm run build)..."
if npm run build --prefix "$PROJECT_ROOT" > /dev/null 2>&1; then
  log_ok "Build succeeded"
else
  log_fail "ビルド失敗。npm run build を手動で実行して確認してください"
fi

STANDALONE_SUCRASE="$PROJECT_ROOT/.next/standalone/node_modules/sucrase"
if [[ -d "$STANDALONE_SUCRASE" ]]; then
  log_ok "standalone に sucrase がバンドルされています"
  # sucrase の transform() が動作するか簡易テスト
  if node -e "const{transform}=require('$STANDALONE_SUCRASE');transform('<div/>',{transforms:['jsx'],jsxRuntime:'classic',production:true})" 2>/dev/null; then
    log_ok "sucrase transform() 動作確認 OK"
  else
    log_fail "sucrase transform() が standalone 環境で動作しません"
  fi
else
  log_fail "standalone に sucrase が含まれていません。next.config.ts の serverExternalPackages を確認してください"
fi

# ============================================================
# Phase 2: Deploy
# ============================================================
if [[ "$DRY_RUN" == "true" ]]; then
  log_step "Phase 2: Dry Run (デプロイはスキップ)"
  echo "  以下の設定でデプロイされます:"
  echo "    Service:  $SERVICE_NAME"
  echo "    Project:  $GCP_PROJECT"
  echo "    Region:   $GCP_REGION"
  echo "    Auth:     ${ALLOW_UNAUTH:-"認証必須"}"
  echo ""
  echo "  実際にデプロイするには --dry-run を外してください"
  exit 0
fi

log_step "Phase 2: Deploying to Cloud Run"
echo "  Service:  $SERVICE_NAME"
echo "  Project:  $GCP_PROJECT"
echo "  Region:   $GCP_REGION"
echo ""

# Secret Manager から GEMINI_API_KEY を取得してデプロイ
DEPLOY_CMD=(
  gcloud run deploy "$SERVICE_NAME"
  --source .
  --region "$GCP_REGION"
  --project "$GCP_PROJECT"
)

if [[ -n "$ALLOW_UNAUTH" ]]; then
  DEPLOY_CMD+=("$ALLOW_UNAUTH")
fi

# Secret Manager にキーが存在するか確認
if gcloud secrets describe gemini-api-key --project="$GCP_PROJECT" &> /dev/null 2>&1; then
  log_ok "Secret Manager: gemini-api-key found"
  DEPLOY_CMD+=(--set-secrets "GEMINI_API_KEY=gemini-api-key:latest")
else
  log_warn "Secret Manager に gemini-api-key が見つかりません"
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    log_warn "環境変数 GEMINI_API_KEY を直接設定します"
    DEPLOY_CMD+=(--set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY")
  else
    log_fail "GEMINI_API_KEY が未設定です。Secret Manager に登録するか環境変数で指定してください"
  fi
fi

# デプロイ実行
DEPLOY_STATUS="FAILED"
if "${DEPLOY_CMD[@]}"; then
  DEPLOY_STATUS="OK"
fi

# ============================================================
# Phase 3: Post-flight (デプロイ検証)
# ============================================================
log_step "Phase 3: Post-flight (デプロイ検証)"

# リビジョン名取得
REVISION=$(gcloud run revisions list \
  --service "$SERVICE_NAME" \
  --region "$GCP_REGION" \
  --project "$GCP_PROJECT" \
  --sort-by "~creationTimestamp" \
  --limit 1 \
  --format "value(metadata.name)" 2>/dev/null || echo "unknown")
log_ok "Revision: $REVISION"

# サービス URL 取得
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$GCP_REGION" \
  --project "$GCP_PROJECT" \
  --format "value(status.url)" 2>/dev/null || echo "")

if [[ -z "$SERVICE_URL" ]]; then
  log_warn "サービス URL を取得できませんでした"
else
  log_ok "URL: $SERVICE_URL"

  # ヘルスチェック
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" 2>/dev/null || echo "000")
  if [[ "$HTTP_STATUS" == "200" ]]; then
    log_ok "Health check: HTTP $HTTP_STATUS"
  else
    log_warn "Health check: HTTP $HTTP_STATUS (200 以外)"
  fi
fi

# ============================================================
# Phase 4: リビジョン記録
# ============================================================
log_step "Phase 4: Recording deployment"

if [[ "$DEPLOY_STATUS" == "OK" && -f "$DEPLOY_LOG" ]]; then
  DEPLOY_TIME=$(date "+%Y-%m-%d %H:%M")

  # 既存エントリ数をカウント (ヘッダー行を除く)
  ENTRY_COUNT=$(grep -c "^|[[:space:]]*[0-9]" "$DEPLOY_LOG" 2>/dev/null || echo "0")
  NEXT_NUM=$((ENTRY_COUNT + 1))

  # Git commit (短縮メッセージ: 40文字まで)
  GIT_INFO="${GIT_COMMIT} ${GIT_MSG:0:40}"

  # テーブル行を追記
  LOG_LINE="| ${NEXT_NUM} | ${DEPLOY_TIME} | \`${REVISION}\` | \`${GIT_INFO}\` | ${DEPLOY_STATUS} | ${QUALITY_GATE} | ${SERVICE_URL:-N/A} |"

  # ヘッダー区切り行 (|---|) の直後に挿入
  # sed: 区切り行の次の行として新しいエントリを追加（最新が上）
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "/^| ---/a\\
${LOG_LINE}
" "$DEPLOY_LOG"
  else
    sed -i "/^| ---/a ${LOG_LINE}" "$DEPLOY_LOG"
  fi

  log_ok "Recorded to docs/deployments/DEPLOY-LOG.md (#${NEXT_NUM})"
else
  if [[ "$DEPLOY_STATUS" != "OK" ]]; then
    log_warn "デプロイ失敗のため記録をスキップ"
  elif [[ ! -f "$DEPLOY_LOG" ]]; then
    log_warn "DEPLOY-LOG.md が見つかりません: $DEPLOY_LOG"
  fi
fi

# ============================================================
# 結果サマリー
# ============================================================
log_step "Deploy Complete"
echo "  Service:   $SERVICE_NAME"
echo "  Project:   $GCP_PROJECT"
echo "  Region:    $GCP_REGION"
echo "  Revision:  $REVISION"
echo "  Commit:    $GIT_COMMIT"
echo "  Status:    $DEPLOY_STATUS"
echo "  URL:       ${SERVICE_URL:-"(取得失敗)"}"
echo ""
