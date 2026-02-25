/**
 * Common Utilities Module
 *
 * Hook スクリプトが共有するユーティリティ関数.
 * stdin 読み取り, stdout 出力、安全チェック等.
 */

import { existsSync, readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

/**
 * stdinでJSONデータ読み取り
 * Claude Code Hooksはstdinでイベントデータを伝達.
 *
 * @returns {Promise<object>}
 */
export async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf-8');
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

/**
 * stdoutでJSON 結果 出力
 * Hook 結果は 必ず stdout JSONで伝達.
 *
 * @param {object} data - 出力するデータ
 */
export function output(data) {
  console.log(JSON.stringify(data));
}

/**
 * Context Limitによる Stop 検出
 * Contextが満杯になった場合は絶対にブロックしない (deadlock 防止)
 *
 * 原本 ralph-loopでは session.error イベントで処理するが,
 * Claude Code Hooksでは Stop 入力のメタデータで判断.
 */
export function isContextLimitStop(data) {
  const reason = (data.stop_reason || data.stopReason || '').toLowerCase();
  const endTurnReason = (data.end_turn_reason || data.endTurnReason || '').toLowerCase();

  const patterns = [
    'context_limit',
    'context_window',
    'context_exceeded',
    'context_full',
    'max_context',
    'token_limit',
    'max_tokens',
    'conversation_too_long',
    'input_too_long',
  ];

  return patterns.some((p) => reason.includes(p) || endTurnReason.includes(p));
}

/**
 * ユーザーキャンセル 検出
 * 原本の session.error(MessageAbortedError) + stop-continuation-guard 対応
 */
export function isUserAbort(data) {
  if (data.user_requested || data.userRequested) return true;

  const reason = (data.stop_reason || data.stopReason || '').toLowerCase();
  const exact = ['aborted', 'abort', 'cancel', 'interrupt'];
  const sub = ['user_cancel', 'user_interrupt', 'ctrl_c', 'manual_stop'];

  return exact.some((p) => reason === p) || sub.some((p) => reason.includes(p));
}

/**
 * Markdown Plan ファイル チェックボックス パース
 * - [ ] = 未完了, - [x] または - [X] = 完了
 * コード ブロック(```) 内部 無視
 *
 * @param {string} planFilePath
 * @returns {{ total: number, completed: number, uncheckedItems: string[] } | null}
 */
export function parsePlanProgress(planFilePath) {
  if (!existsSync(planFilePath)) return null;

  try {
    const content = readFileSync(planFilePath, 'utf-8');
    const lines = content.split('\n');
    let inCodeBlock = false;
    let total = 0;
    let completed = 0;
    const uncheckedItems = [];

    for (const line of lines) {
      if (line.trim().startsWith('```')) {
        inCodeBlock = !inCodeBlock;
        continue;
      }
      if (inCodeBlock) continue;

      const match = line.match(/^(\s*)- \[([ xX])\]\s+(.+)/);
      if (match) {
        total++;
        if (match[2].toLowerCase() === 'x') {
          completed++;
        } else {
          uncheckedItems.push(match[3].trim());
        }
      }
    }

    return { total, completed, uncheckedItems };
  } catch {
    return null;
  }
}

/**
 * Claude Code Task システムで未完了 作業 カウント
 * 原本 todo-continuation-enforcerのgetIncompleteCount() 対応
 *
 * Claude CodeのTask ファイルは ~/.claude/tasks/{sessionId}/ に保存.
 */
export function countIncompleteTasks(sessionId) {
  if (!sessionId || typeof sessionId !== 'string') return 0;
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,255}$/.test(sessionId)) return 0;

  const taskDir = join(homedir(), '.claude', 'tasks', sessionId);
  if (!existsSync(taskDir)) return 0;

  let count = 0;
  try {
    const files = readdirSync(taskDir).filter((f) => f.endsWith('.json') && f !== '.lock');
    for (const file of files) {
      try {
        const content = readFileSync(join(taskDir, file), 'utf-8');
        const task = JSON.parse(content);
        if (task.status === 'pending' || task.status === 'in_progress') count++;
      } catch {
        /* skip malformed */
      }
    }
  } catch {
    /* skip */
  }
  return count;
}
