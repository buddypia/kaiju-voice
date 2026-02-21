#!/usr/bin/env node

/**
 * Hackathon Project Post-Tool Verifier Hook (PostToolUse)
 *
 * oh-my-opencodeのpost-tool-verifier.mjsをHackathon Projectに 忠実に移植.
 * ツール実行の都度実行されて 結果を検証してセッション統計を追跡します.
 *
 * メカニズム (原本ベース):
 * 1. Bash 出力から 失敗パターン検出 (error, failed, permission denied 等)
 * 2. セッション統計 追跡 (ツール呼び出しカウント, 最後のツール 等)
 * 3. ツール別検証メッセージ生成
 * 4. バックグラウンド作業検出
 *
 * 原本との差異:
 * - Remember tag 処理 除外 (Notepad システム削除済み)
 * - セッション統計を.claude/state/に保存 (原本は~/.claude/.session-stats.json)
 * - Web QA(lint/test) 中心 失敗パターン 追加
 *
 * @see oss-sources/oh-my-claudecode/scripts/post-tool-verifier.mjs (原本)
 */

import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { readState, isStale, ensureStateDir, SUPPORTED_MODES } from './lib/state.mjs';
import { readStdin, output } from './lib/utils.mjs';

// ═══════════════════════════════════════════════════════════════════
// 失敗パターン検出 (原本忠実移植 + Web QA 特化)
// ═══════════════════════════════════════════════════════════════════

/** 成功オーバーライドパターン (v2.1 新規 - BUG-4 修正)
 * このパターンにマッチングしたら失敗パターンチェックをスキップ.
 * "0 tests failed" のようなfalse positive 防止.
 */
const SUCCESS_OVERRIDES = [
  /0 tests? failed/i,
  /0 issues? found/i,
  /no issues found/i,
  /all tests passed/i,
];

/** Bash コマンド失敗パターン (原本ベース, v2.1 精密化) */
const BASH_FAILURE_PATTERNS = [
  /error:/i,
  /\bfailed\b/i,
  /\bfailure\b/i,
  /permission denied/i,
  /exit code:\s*[1-9]/i,
  /command not found/i,
  /no such file/i,
  /\bfatal\b/i,
  /\bpanic\b/i,
  /segmentation fault/i,
];

/** QA 失敗パターン (lint/test 中心, v2.1: 0 除外 精密化) */
const QA_FAILURE_PATTERNS = [
  /[1-9]\d* issues? found/i, // analyze/lint 失敗
  /[1-9]\d* problems?/i, // eslint 問題 件数
  /some tests failed/i, // test 失敗
  /[1-9]\d* tests? failed/i, // test 失敗 (1以上のみ)
  /test suites?:\s*[1-9]\d*\s+failed/i,
  /\blint(?:ing)? failed\b/i,
  /\beslint\b.*\b(error|failed)\b/i,
  /\btype[\s-]?check(?:ing)? failed\b/i,
  /compilation failed/i,
];

/** Write/Edit 失敗パターン (原本と同一) */
const WRITE_FAILURE_PATTERNS = [/permission/i, /read.only/i, /not found/i, /does not exist/i];

/** バックグラウンド作業検出パターン (v2.1: 精密化 - BUG-4 修正) */
const BACKGROUND_PATTERNS = [
  /running in background/i,
  /background process/i,
  /background task/i,
  /daemon started/i,
  /task_id/i,
  /spawned/i,
];

/**
 * ツール出力から失敗有無を検出.
 *
 * @param {string} toolName - ツール名
 * @param {string} toolOutput - ツール出力
 * @returns {{ failed: boolean, patterns: string[], isBackground: boolean }}
 */
function analyzeToolOutput(toolName, toolOutput) {
  if (!toolOutput) return { failed: false, patterns: [], isBackground: false };

  const output = String(toolOutput);
  const matchedPatterns = [];
  let isBackground = false;

  // v2.1: SUCCESS_OVERRIDES チェック (BUG-4 修正)
  // 成功パターンにマッチングすれば失敗パターンチェックをスキップ
  const isSuccessOverride = SUCCESS_OVERRIDES.some((p) => p.test(output));

  switch (toolName) {
    case 'Bash': {
      if (!isSuccessOverride) {
        // Bash 失敗パターン
        for (const pattern of BASH_FAILURE_PATTERNS) {
          if (pattern.test(output)) {
            matchedPatterns.push(pattern.source);
          }
        }
        // QA 失敗パターン (lint/test)
        for (const pattern of QA_FAILURE_PATTERNS) {
          if (pattern.test(output)) {
            matchedPatterns.push(pattern.source);
          }
        }
      }
      // バックグラウンド検出
      isBackground = BACKGROUND_PATTERNS.some((p) => p.test(output));
      break;
    }

    case 'Edit':
    case 'Write': {
      for (const pattern of WRITE_FAILURE_PATTERNS) {
        if (pattern.test(output)) {
          matchedPatterns.push(pattern.source);
        }
      }
      break;
    }

    case 'Task': {
      // Task ツールの失敗/バックグラウンド検出
      for (const pattern of WRITE_FAILURE_PATTERNS) {
        if (pattern.test(output)) {
          matchedPatterns.push(pattern.source);
        }
      }
      isBackground = BACKGROUND_PATTERNS.some((p) => p.test(output));
      break;
    }

    case 'Grep':
    case 'Glob': {
      // 検索結果なし検出
      if (/no (?:matches|files|results)/i.test(output) || output.trim() === '') {
        matchedPatterns.push('no results');
      }
      break;
    }
  }

  return {
    failed: matchedPatterns.length > 0,
    patterns: matchedPatterns,
    isBackground,
  };
}

// ═══════════════════════════════════════════════════════════════════
// セッション統計 (原本の session-stats 簡素化バージョン)
// ═══════════════════════════════════════════════════════════════════

/**
 * セッション統計更新.
 * 原本は~/.claude/.session-stats.jsonに保存するが,
 * Hackathon Projectは.claude/state/session-stats.jsonに保存.
 */
function updateSessionStats(stateDir, toolName) {
  const statsPath = join(stateDir, 'session-stats.json');
  let stats = { tool_counts: {}, total_calls: 0, last_tool: '', updated_at: 0 };

  try {
    if (existsSync(statsPath)) {
      stats = JSON.parse(readFileSync(statsPath, 'utf-8'));
    }
  } catch {
    /* 破損ファイルは初期化 */
  }

  stats.tool_counts[toolName] = (stats.tool_counts[toolName] || 0) + 1;
  stats.total_calls = (stats.total_calls || 0) + 1;
  stats.last_tool = toolName;
  stats.updated_at = Date.now();

  try {
    writeFileSync(statsPath, JSON.stringify(stats, null, 2));
  } catch {
    /* 統計保存失敗は無視 */
  }

  return stats;
}

// ═══════════════════════════════════════════════════════════════════
// 検証メッセージ生成
// ═══════════════════════════════════════════════════════════════════

/**
 * ツール実行結果に基づく検証メッセージ生成.
 *
 * @param {string} toolName
 * @param {object} analysis - analyzeToolOutput() 結果
 * @param {object} stats - セッション統計
 * @returns {string|null} - 注入するメッセージまたは null (注入不要)
 */
function buildVerificationMessage(toolName, analysis, stats) {
  const parts = [];

  // 失敗検出時の警告
  if (analysis.failed) {
    if (toolName === 'Bash') {
      parts.push(`失敗検出: ${analysis.patterns.join(', ')}. エラーを分析して修正してください.`);
    } else if (toolName === 'Edit' || toolName === 'Write') {
      parts.push(`ファイル書き込み問題検出。権限とパスを確認してください。`);
    } else if (toolName === 'Grep' || toolName === 'Glob') {
      parts.push(`検索結果なし. パターンまたはパスを調整してください.`);
    }
  }

  // バックグラウンド作業検出
  if (analysis.isBackground) {
    parts.push(`バックグラウンド作業が検出されました。完了を待つか、他の作業を進めてください。`);
  }

  // 過度なツール使用警告 (原本と同一)
  if (toolName === 'Read' && (stats.tool_counts['Read'] || 0) > 10) {
    parts.push(
      `Read 呼び出しが ${stats.tool_counts['Read']}回です. Grep/Globで対象を絞ることを検討してください.`,
    );
  }

  if (toolName === 'Task' && (stats.tool_counts['Task'] || 0) > 5) {
    parts.push(
      `Task エージェントが ${stats.tool_counts['Task']}回生成されました。過度な並列実行に注意してください。`,
    );
  }

  if (parts.length === 0) return null;
  return parts.join(' ');
}

// ═══════════════════════════════════════════════════════════════════
// メイン実行
// ═══════════════════════════════════════════════════════════════════

async function main() {
  try {
    const data = await readStdin();
    const toolName = data.tool_name || data.toolName || '';
    const toolOutput = data.tool_output || data.toolOutput || '';
    const directory = data.directory || process.cwd();
    const stateDir = join(directory, '.claude', 'state');

    ensureStateDir(stateDir);

    // アクティブモード確認 (非アクティブなら最小限の処理のみ)
    const hasActiveMode = (() => {
      for (const mode of SUPPORTED_MODES) {
        const state = readState(stateDir, mode);
        if (state?.active && !isStale(state)) return true;
      }
      return false;
    })();

    // セッション統計更新 (アクティブモードの有無に関わらず常に実行)
    const stats = updateSessionStats(stateDir, toolName);

    // アクティブモードがなければ パススルー (統計のみ収集)
    if (!hasActiveMode) {
      return output({ continue: true });
    }

    // ツール出力分析
    const analysis = analyzeToolOutput(toolName, toolOutput);

    // 検証メッセージ生成
    const message = buildVerificationMessage(toolName, analysis, stats);

    if (!message) {
      return output({ continue: true });
    }

    return output({
      continue: true,
      hookSpecificOutput: {
        hookEventName: 'PostToolUse',
        additionalContext: message,
      },
    });
  } catch (error) {
    console.error(`[post-tool-verifier] Error: ${error.message}`);
    return output({ continue: true });
  }
}

main();
