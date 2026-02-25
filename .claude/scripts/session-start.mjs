#!/usr/bin/env node

/**
 * Session Start Hook (SessionStart)
 *
 * Claude Code セッション開始時に実行されて前セッションのアクティブ状態を復元します.
 *
 * メカニズム:
 * 1. State ディレクトリでアクティブモード検索
 * 2. アクティブモード発見時に復元メッセージ生成
 * 3. 未完了 Task カウント含む
 * 4. hookSpecificOutput.additionalContextで復元メッセージ注入
 *
 * これが必要な理由:
 * - セッションがcontext compactionで再起動された時、AIは以前の状態を把握していない
 * - Stop hookがブロックしてもAIが「なぜ」ブロックされるか分からないと混乱発生
 * - Session start hookが以前の状態を復元する必要がありAIが正しく対応
 */

import { join } from 'path';
import { readState, isStale, ensureStateDir, isSessionOwned, writeState } from './lib/state.mjs';
import { readStdin, output, countIncompleteTasks } from './lib/utils.mjs';

// ═══════════════════════════════════════════════════════════════════
// モード別復元メッセージテンプレート (原本 session-start.mjs 移植)
// ═══════════════════════════════════════════════════════════════════

/**
 * Persistent モード復元メッセージ
 */
function persistentRestoreMessage(state) {
  const iteration = state.iteration ?? 0;
  const maxIter = state.max_iterations ?? 20;
  const prompt = state.original_prompt || state.prompt || '(元の作業情報なし)';

  let msg = `[PERSISTENT MODE RESTORED]\n`;
  msg += `前のセッションで有効化された persistent modeが復元されました.\n`;
  msg += `元の作業: ${prompt}\n`;
  msg += `進行: ${iteration}/${maxIter} iterations\n`;

  if (state.completion?.type === 'plan') {
    msg += `完了条件: 計画ファイル(${state.completion.plan_file})のすべてのチェックボックス完了\n`;
  } else {
    msg += `完了条件: <promise>DONE</promise> 出力または /cancel\n`;
  }

  msg += `\n前の作業を続行してください.`;
  return msg;
}

/**
 * QA モード復元メッセージ (state key: web-qa)
 */
function qaRestoreMessage(state) {
  const cycle = state.cycle ?? 0;
  const maxCycles = state.max_cycles ?? 10;
  const analyzeCommand = process.env.CLAUDE_QA_ANALYZE_CMD || 'npm run lint';
  const testCommand = process.env.CLAUDE_QA_TEST_CMD || 'npm test';

  let msg = `[QA MODE RESTORED]\n`;
  msg += `前のセッションで有効化された QA サイクルが復元されました.\n`;
  msg += `進行: Cycle ${cycle}/${maxCycles}\n`;

  if (state.last_failure) {
    msg += `最後の失敗: ${state.last_failure}\n`;
  }

  msg += `\n以下を実行してください:\n`;
  msg += `1. ${analyzeCommand} - 静的分析\n`;
  msg += `2. ${testCommand} - テスト\n`;
  msg += `3. 失敗時は修正後に再検証\n`;
  msg += `\n全て通過時 <promise>QA_COMPLETE</promise>を出力してください.`;
  return msg;
}

/**
 * Turbo モード復元メッセージ
 */
function turboRestoreMessage(state) {
  const count = state.reinforcement_count ?? 0;
  const maxCount = state.max_reinforcements ?? 30;
  const prompt = state.original_prompt || state.prompt || '';

  let msg = `[TURBO MODE RESTORED]\n`;
  msg += `前のセッションで有効化された turbo modeが復元されました.\n`;
  msg += `進行: #${count}/${maxCount} reinforcements\n`;

  if (prompt) {
    msg += `元の作業: ${prompt}\n`;
  }

  msg += `\n並列実行モードで作業を続けてください。`;
  return msg;
}

// ═══════════════════════════════════════════════════════════════════
// メイン実行
// ═══════════════════════════════════════════════════════════════════

async function main() {
  try {
    const data = await readStdin();
    const directory = data.directory || process.cwd();
    const stateDir = join(directory, '.claude', 'state');
    const sessionId = data.session_id || data.sessionId || '';

    ensureStateDir(stateDir);

    // ── アクティブモード収集 (BUG-9: セッションスコープ適用) ──
    const messages = [];
    const modes = ['persistent', 'web-qa', 'turbo'];
    const source = data.source || '';
    // compact/resumeは同一論理セッションの連続 → モード引き継ぎ許可
    const isSessionContinuation = source === 'compact' || source === 'resume';

    for (const mode of modes) {
      const state = readState(stateDir, mode);
      if (!state?.active) continue;
      if (isStale(state)) continue;

      // セッション所有権チェック
      if (!isSessionOwned(state, sessionId)) {
        if (isSessionContinuation) {
          // compact/resume: 前セッションのモードを現在セッションに引き継ぎ
          state.session_id = sessionId;
          writeState(stateDir, mode, state);
        } else {
          // startup/clear: 他セッションのモードは復元しない
          continue;
        }
      }

      switch (mode) {
        case 'persistent':
          messages.push(persistentRestoreMessage(state));
          break;
        case 'web-qa':
          messages.push(qaRestoreMessage(state));
          break;
        case 'turbo':
          messages.push(turboRestoreMessage(state));
          break;
      }
    }

    // ── 未完了 Task カウント ──
    const taskCount = countIncompleteTasks(sessionId);
    if (taskCount > 0) {
      messages.push(
        `[PENDING TASKS DETECTED]\n` +
          `以前のセッションで未完了 Taskが${taskCount}個発見されました.\n` +
          `これらのTaskを引き続き処理してください.`,
      );
    }

    // ── メッセージがなければパススルー ──
    if (messages.length === 0) {
      return output({ continue: true });
    }

    // ── 復元メッセージ注入 ──
    const additionalContext = `<session-restore>\n${messages.join('\n\n---\n\n')}\n</session-restore>`;

    return output({
      continue: true,
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext,
      },
    });
  } catch (error) {
    console.error(`[session-start] Error: ${error.message}`);
    return output({ continue: true });
  }
}

main();
