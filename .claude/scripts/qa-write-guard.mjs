#!/usr/bin/env node

/**
 * QA Write Guard - PreToolUse Hook
 *
 * oh-my-opencodeのOrchestrator Role Enforcementパターン (Pattern #7) ポーティング.
 *
 * 原本 Atlas Hook:
 * - Atlasが.sisyphus/ 外部にWrite/Edit 試行時 ブロック
 * - "YOU ARE VIOLATING ORCHESTRATOR PROTOCOL" 注入
 *
 * 本Guard:
 * - QA モードでテストファイル 削除/毀損ブロック
 * - 生成成果物ファイルの直接編集ブロック
 * - Ultraworkの"NO TEST DELETION" ルール実装
 *
 * PreToolUse Hookとして動作:
 * - matcher: "Edit|Write"
 * - 入力: tool_name, tool_input (file_path, content/old_string/new_string)
 * - 出力: hookSpecificOutput.permissionDecision = "deny" / "allow" / (空オブジェクト)
 */

import { readState, isStale, isSessionOwned } from './lib/state.mjs';
import { readStdin, output } from './lib/utils.mjs';
import { join } from 'path';
import { existsSync } from 'fs';

/**
 * テストファイル判定
 * 絶対パス/相対パス + 一般的な JS/TS テストパターンをサポート.
 */
function isTestFile(filePath) {
  const normalized = String(filePath || '').replace(/\\/g, '/');
  return (
    normalized.includes('/test/') ||
    normalized.startsWith('test/') ||
    normalized.includes('/__tests__/') ||
    /\.test\.[cm]?[jt]sx?$/.test(normalized) ||
    /\.spec\.[cm]?[jt]sx?$/.test(normalized)
  );
}

function isGeneratedFile(filePath) {
  const normalized = String(filePath || '').replace(/\\/g, '/');
  return (
    normalized.endsWith('.d.ts') ||
    normalized.endsWith('.min.js') ||
    normalized.endsWith('.min.css') ||
    normalized.endsWith('.bundle.js') ||
    normalized.endsWith('.map')
  );
}

async function main() {
  try {
    const data = await readStdin();

    const projectDir = process.env.CLAUDE_PROJECT_DIR || data.cwd || process.cwd();
    const stateDir = join(projectDir, '.claude', 'state');
    const sessionId = data.session_id || '';
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    const filePath = toolInput.file_path || '';

    // QA モードが有効化されていなければ無条件通過 (BUG-9: セッションスコープチェック)
    const qaState = readState(stateDir, 'web-qa');
    if (!qaState?.active || isStale(qaState) || !isSessionOwned(qaState, sessionId)) {
      return output({});
    }

    // ═══════════════════════════════════════════════════════════════
    // Guard 1: 生成成果物ファイル保護
    // 自動生成/バンドル成果物はソース修正で再生成する必要がある.
    // ═══════════════════════════════════════════════════════════════
    if (isGeneratedFile(filePath)) {
      const codegenCommand = process.env.CLAUDE_QA_CODEGEN_CMD || 'npm run build';
      return output({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason:
            `[QA GUARD] コード生成ファイル(${filePath.split('/').pop()})は直接修正不可.\n` +
            `ソースファイルを修正してから再生成コマンドを実行してください:\n` +
            `${codegenCommand}`,
        },
      });
    }

    // ═══════════════════════════════════════════════════════════════
    // Guard 2: テストファイル削除防止 (Writeで空/最小ファイル書き込み)
    // 原本 Ultraworkの"NO TEST DELETION" ルール:
    // "If tests fail, fix the CODE not the tests"
    // ═══════════════════════════════════════════════════════════════
    if (toolName === 'Write' && isTestFile(filePath)) {
      const content = toolInput.content || '';
      // BUG-5 fix: 新規ファイル生成は許可、既存ファイルの空化/削除のみブロック
      const fileExists = existsSync(filePath);
      if (fileExists && content.trim().length < 50) {
        return output({
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason:
              `[QA GUARD] QA モードでテストファイルを空にしたり削除したりできません.\n` +
              `テストが失敗したらコードを修正してください。テストを削除しないでください.\n` +
              `File: ${filePath}`,
          },
        });
      }
    }

    // ═══════════════════════════════════════════════════════════════
    // Guard 3: テストassertion削除防止 (Edit)
    // expect() 文が大量に除去される編集を検出
    // ═══════════════════════════════════════════════════════════════
    if (toolName === 'Edit' && isTestFile(filePath)) {
      const oldStr = toolInput.old_string || '';
      const newStr = toolInput.new_string || '';

      const expectCountOld = (oldStr.match(/expect\(/g) || []).length;
      const expectCountNew = (newStr.match(/expect\(/g) || []).length;

      // expect()があったのにすべて除去され、全体サイズが半分以下に減ればブロック
      if (expectCountOld > 0 && expectCountNew === 0 && oldStr.length > newStr.length * 2) {
        return output({
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason:
              `[QA GUARD] テストassertion削除検出!\n` +
              `${expectCountOld}個の expect() 文がすべて除去されます。\n` +
              `テストが失敗したらコードを修正してください。テストを削除しないでください.\n` +
              `File: ${filePath}`,
          },
        });
      }
    }

    // 全Guard通過
    return output({});
  } catch (error) {
    console.error(`[qa-write-guard] Error: ${error.message}`);
    return output({}); // エラー時は許可 (安全方向)
  }
}

main();
