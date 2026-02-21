#!/usr/bin/env node

/**
 * Web Project Pre-Tool Enforcer Hook (PreToolUse - Sisyphus)
 *
 * oh-my-opencodeのpre-tool-enforcer.mjsをWeb Projectに忠実に移植。
 * 毎ツール呼び出し前に実行され、作業状態リマインダーとツール別ヒントを注入します。
 *
 * Sisyphus哲学（原本忠実移植）:
 * "The boulder never stops. Continue until all tasks complete."
 * すべてのツール呼び出し前にアクティブな作業状態をリマインダーとして注入し、
 * AIが現在のコンテキストを失わないようにします。
 *
 * メカニズム:
 * 1. アクティブモード状態の読み取り (.claude/state/)
 * 2. 未完了Taskカウント (Claude Code Taskシステム)
 * 3. ツール別最適化ヒント生成
 * 4. hookSpecificOutput.additionalContextで注入
 *
 * 原本との差異:
 * - Todoカウントの代わりにClaude Code Taskカウントを使用
 * - ツール別ヒントをWeb開発フロー(lint/test)基準に調整
 * - Web Projectスキルシステムに合わせたメッセージ
 *
 * @see oss-sources/oh-my-claudecode/scripts/pre-tool-enforcer.mjs (原本)
 */

import { join } from 'path';
import { readState, isStale, ensureStateDir, isSessionOwned } from './lib/state.mjs';
import { readStdin, output, countIncompleteTasks } from './lib/utils.mjs';

// ═══════════════════════════════════════════════════════════════════
// ツール別リマインダー (原本忠実移植 + Web QA 特化)
// ═══════════════════════════════════════════════════════════════════

/**
 * ツール別最適化ヒントを返却.
 * 原本のtool-specific messagesをWeb QAフローに合わせて修正.
 *
 * @param {string} toolName - Claude Code ツール名
 * @returns {string} ツール別ヒントメッセージ
 */
function getToolTip(toolName) {
  switch (toolName) {
    case 'Bash':
      return '並列実行可能なコマンドは同時に呼び出してください。lint/testは依存順序を考慮して実行してください。';

    case 'Task':
      return '独立した作業は並列エージェントで実行してください。run_in_backgroundで長時間作業を実行してください。';

    case 'Edit':
    case 'Write':
      return '変更後の動作確認をしてください。完了前にlintとtest通過を確認してください。';

    case 'Read':
      return '関連ファイルは並列で読んでください。不要なファイル読み込みを避けてください。';

    case 'Grep':
    case 'Glob':
      return 'パターン調査時は複数の検索を並列で実行してください。';

    case 'TaskCreate':
    case 'TaskUpdate':
      return '作業開始前にin_progressに設定、完了後すぐにcompletedに設定してください。';

    default:
      return '';
  }
}

// ═══════════════════════════════════════════════════════════════════
// 状態プレフィックス生成 (原本のprefix messageパターン)
// ═══════════════════════════════════════════════════════════════════

/**
 * 現在のアクティブモードとTaskカウントをプレフィックスとして生成.
 *
 * 原本形式: [X active, Y pending]
 * Web Project形式: [MODE - PROGRESS | Tasks: N]
 */
function buildStatusPrefix(stateDir, sessionId) {
  const parts = [];

  // アクティブモード状態
  const persistent = readState(stateDir, 'persistent');
  if (persistent?.active && !isStale(persistent) && isSessionOwned(persistent, sessionId)) {
    const iter = persistent.iteration ?? 0;
    const max = persistent.max_iterations ?? 20;
    parts.push(`PERSISTENT ${iter}/${max}`);
  }

  const qa = readState(stateDir, 'web-qa');
  if (qa?.active && !isStale(qa) && isSessionOwned(qa, sessionId)) {
    const cycle = qa.cycle ?? 0;
    const max = qa.max_cycles ?? 10;
    parts.push(`QA ${cycle}/${max}`);
  }

  const turbo = readState(stateDir, 'turbo');
  if (turbo?.active && !isStale(turbo) && isSessionOwned(turbo, sessionId)) {
    const count = turbo.reinforcement_count ?? 0;
    parts.push(`TURBO #${count}`);
  }

  // Taskカウント
  const taskCount = countIncompleteTasks(sessionId);
  if (taskCount > 0) {
    parts.push(`Tasks: ${taskCount}`);
  }

  if (parts.length === 0) return null;
  return `[${parts.join(' | ')}]`;
}

// ═══════════════════════════════════════════════════════════════════
// メイン実行
// ═══════════════════════════════════════════════════════════════════

async function main() {
  try {
    const data = await readStdin();
    const toolName = data.tool_name || data.toolName || '';
    const directory = data.directory || process.cwd();
    const sessionId = data.session_id || data.sessionId || '';
    const stateDir = join(directory, '.claude', 'state');

    ensureStateDir(stateDir);

    // アクティブモードがなければパススルー (リマインダー不要)
    const statusPrefix = buildStatusPrefix(stateDir, sessionId);
    if (!statusPrefix) {
      return output({ continue: true });
    }

    // ツール別ヒント
    const tip = getToolTip(toolName);

    // リマインダーメッセージ組み立て
    let reminder = statusPrefix;
    if (tip) {
      reminder += ` ${tip}`;
    }

    return output({
      continue: true,
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext: reminder,
      },
    });
  } catch (error) {
    console.error(`[pre-tool-enforcer] Error: ${error.message}`);
    return output({ continue: true });
  }
}

main();
