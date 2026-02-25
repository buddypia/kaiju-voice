#!/usr/bin/env node

/**
 * oh-my-claude-code - Unified Stop/SubagentStop Handler (v2.0)
 *
 * oh-my-opencodeの3大メカニズムをClaude Code Hooks Stop APIに
 * 根本的に再設計してポーティング:
 *
 * ┌─────────────────────────┐    ┌──────────────────────────┐
 * │ oh-my-opencode (Plugin) │    │ Claude Code Hooks (v2.0) │
 * ├─────────────────────────┤    ├──────────────────────────┤
 * │ ralph-loop              │ → │ stop-handler.mjs         │
 * │  ├ session.idle event   │    │  ├ Stop event            │
 * │  ├ transcript parsing   │    │  ├ transcript_path パース  │
 * │  ├ <promise>DONE</...>  │    │  ├ <promise>DONE</...>   │
 * │  └ session.prompt()     │    │  └ decision: "block"     │
 * │ todo-continuation       │    │                          │
 * │  ├ session.todo()       │ → │  ├ Task ファイル カウント       │
 * │  ├ countdown + inject   │    │  └ block reasonに含む   │
 * │  └ abort detection      │    │                          │
 * │ stop-continuation-guard │ → │  ├ isUserAbort() チェック     │
 * │  └ stoppedSessions Set  │    │  └ stop_hook_active チェック │
 * └─────────────────────────┘    └──────────────────────────┘
 *
 * 核心的差異:
 * - 原本: Pluginのsession.prompt()でcontinuation 注入
 * - ポーティング: Stop Hookの{"decision":"block","reason":"..."} で代替
 *   → reasonがClaudeに continuation prompt 役割を果たす
 *
 * サポートモード: persistent, qa(web-qa state), turbo
 *
 * 使用法: settings.jsonのStop/SubagentStop Hookに登録
 */

import {
  readState,
  writeState,
  clearState,
  isStale,
  getActiveModeForSession,
  hasSameErrorRepeated,
  ensureStateDir,
} from './lib/state.mjs';
import { detectCompletionMarker, detectQaCompletion } from './lib/transcript.mjs';
import {
  readStdin,
  output,
  isContextLimitStop,
  isUserAbort,
  parsePlanProgress,
  countIncompleteTasks,
} from './lib/utils.mjs';
import { join } from 'path';

/** 同一エラー繰り返し許容回数 */
const SAME_ERROR_THRESHOLD = 3;

/** error_history 最大保管数 (メモリ/ファイル肥大化防止) */
const MAX_ERROR_HISTORY = 10;

const DEFAULT_ANALYZE_COMMAND = process.env.CLAUDE_QA_ANALYZE_CMD || 'npm run lint';
const DEFAULT_TEST_COMMAND = process.env.CLAUDE_QA_TEST_CMD || 'npm test';

/**
 * error_historyにエラーシグネチャ追加 (bounded push)
 * @param {object} state - state オブジェクト (in-place 修正)
 * @param {string} signature - エラーシグネチャ文字列
 */
function pushError(state, signature) {
  if (!Array.isArray(state.error_history)) {
    state.error_history = [];
  }
  state.error_history.push(signature);
  if (state.error_history.length > MAX_ERROR_HISTORY) {
    state.error_history = state.error_history.slice(-MAX_ERROR_HISTORY);
  }
}

async function main() {
  try {
    const data = await readStdin();

    const projectDir = process.env.CLAUDE_PROJECT_DIR || data.cwd || process.cwd();
    const stateDir = join(projectDir, '.claude', 'state');
    const sessionId = data.session_id || '';
    const transcriptPath = data.transcript_path || '';
    const isStopHookActive = data.stop_hook_active || false;

    ensureStateDir(stateDir);

    // ═══════════════════════════════════════════════════════════════
    // Safety Gate 1: Context Limit → 絶対にブロック禁止
    // 原本 ralph-loopでもcontext 関連エラー時 loop 中断
    // ═══════════════════════════════════════════════════════════════
    if (isContextLimitStop(data)) {
      return output({});
    }

    // ═══════════════════════════════════════════════════════════════
    // Safety Gate 2: ユーザーキャンセル → 即時尊重
    // 原本 stop-continuation-guard + session.error(AbortError) 対応
    // ═══════════════════════════════════════════════════════════════
    if (isUserAbort(data)) {
      return output({});
    }

    // ═══════════════════════════════════════════════════════════════
    // Mode Detection
    // ═══════════════════════════════════════════════════════════════
    const active = getActiveModeForSession(stateDir, sessionId);

    if (!active) {
      // アクティブモードなし → 正常終了
      return output({});
    }

    const { mode, state } = active;

    // ═══════════════════════════════════════════════════════════════
    // Safety Gate 3: stop_hook_active チェック
    // Claude Codeが既に Stop Hookによって一度継続された状態.
    // アクティブモードがなければ許可 (上で処理済み).
    // アクティブモードがあれば正常ロジック進行 (max_iterationsがセーフガード).
    // ═══════════════════════════════════════════════════════════════
    // (stop_hook_activeは無限ループ防止のためにのみ存在するが,
    //  我々のiteration/cycle カウンターが既にセーフガード役割を果たす)

    // ═══════════════════════════════════════════════════════════════
    // Safety Gate 4: 同一エラー繰り返し検出
    // 原本 ralph-loopにはないが、構造的問題の早期検出のため追加
    // ═══════════════════════════════════════════════════════════════
    if (hasSameErrorRepeated(state, SAME_ERROR_THRESHOLD)) {
      return output({
        decision: 'block',
        reason:
          `[${formatMode(mode)} - 中断] 同一エラーが ${SAME_ERROR_THRESHOLD}回 繰り返し.\n` +
          `構造的問題と判断. /cancelでモードを終了し 根本 原因を分析してください.`,
      });
    }

    // ═══════════════════════════════════════════════════════════════
    // Mode-Specific Handler Dispatch
    // ═══════════════════════════════════════════════════════════════
    switch (mode) {
      case 'persistent':
        return handlePersistent(stateDir, state, projectDir, transcriptPath, sessionId);
      case 'web-qa':
        return handleWebQa(stateDir, state, projectDir, transcriptPath, sessionId);
      case 'turbo':
        return handleTurbo(stateDir, state, projectDir, transcriptPath, sessionId);
      default:
        return output({});
    }
  } catch (error) {
    // エラー時は安全に終了を許可 (deadlock 絶対 防止)
    console.error(`[stop-handler] Error: ${error.message}`);
    return output({});
  }
}

// ═══════════════════════════════════════════════════════════════════
// Persistent Mode Handler
//
// 原本 ralph-loopの核心ロジック ポーティング:
// 1. Completion marker (<promise>DONE</promise>) 検索 → 自動 終了
// 2. Plan チェックボックス 完了 チェック → 自動 終了
// 3. Max iterations → 終了を許可 (原本と同一)
// 4. 未完了 時 → block + continuation prompt
// ═══════════════════════════════════════════════════════════════════
function handlePersistent(stateDir, state, projectDir, transcriptPath, sessionId) {
  const iteration = state.iteration ?? 1;
  const maxIter = state.max_iterations ?? 20;
  const completionPromise = state.completion_promise || 'DONE';

  // ── Completion Marker 検査 (ralph-loop 核心メカニズム) ──
  if (detectCompletionMarker(transcriptPath, completionPromise)) {
    clearState(stateDir, 'persistent');
    console.error(
      `[stop-handler] Persistent: completion marker "${completionPromise}" detected at iteration ${iteration}. Auto-cleanup.`,
    );
    return output({});
  }

  // ── Plan 基盤 完了 チェック ──
  if (state.completion?.type === 'plan') {
    const planFile = join(projectDir, state.completion.plan_file);
    const progress = parsePlanProgress(planFile);

    if (progress === null) {
      return output({
        decision: 'block',
        reason:
          `[PERSISTENT ${iteration}/${maxIter}] 計画ファイル未生成.\n` +
          `位置: ${state.completion.plan_file}\n` +
          `- [ ] チェックボックス付きの計画ファイルを生成してください.`,
      });
    }

    if (progress.total === 0) {
      return output({
        decision: 'block',
        reason:
          `[PERSISTENT ${iteration}/${maxIter}] 計画ファイルにチェックボックスなし.\n` +
          `位置: ${state.completion.plan_file}`,
      });
    }

    if (progress.completed >= progress.total) {
      clearState(stateDir, 'persistent');
      console.error(
        `[stop-handler] Persistent plan complete: ${progress.completed}/${progress.total}. Auto-cleanup.`,
      );
      return output({});
    }
  }

  // ── Max iterations → 終了を許可 ──
  // 原本 ralph-loopと同一: max 到達時 state 整理 + 終了を許可
  if (iteration >= maxIter) {
    clearState(stateDir, 'persistent');
    console.error(`[stop-handler] Persistent: max iterations (${maxIter}) reached. Allowing stop.`);
    return output({});
  }

  // ── Increment + Block ──
  state.iteration = iteration + 1;
  state.last_checked_at = new Date().toISOString();
  const writeOk = writeState(stateDir, 'persistent', state);
  if (!writeOk) {
    // writeState 失敗時 blockすると iteration 未増加→ 無限ループ危険
    console.error(
      '[stop-handler] Persistent: writeState failed. Allowing stop to prevent infinite loop.',
    );
    return output({});
  }

  const taskCount = countIncompleteTasks(sessionId);

  let reason = `[PERSISTENT ${iteration + 1}/${maxIter}]`;

  if (state.completion?.type === 'plan') {
    const planFile = join(projectDir, state.completion.plan_file);
    const progress = parsePlanProgress(planFile);
    if (progress && progress.total > 0) {
      const pct = Math.round((progress.completed / progress.total) * 100);
      reason += ` 進捗率: ${progress.completed}/${progress.total} (${pct}%)`;
      if (progress.uncheckedItems.length > 0) {
        const preview = progress.uncheckedItems.slice(0, 5);
        reason += `\n\n未完了:\n${preview.map((item) => `  - [ ] ${item}`).join('\n')}`;
        if (progress.uncheckedItems.length > 5) {
          reason += `\n  ... (+${progress.uncheckedItems.length - 5}個)`;
        }
      }
      reason += `\n\n全項目完了時に自動終了します。`;
    }
  } else {
    // Phase 表示 (keyword-detectorが設定した phase フィールド)
    if (state.phase) {
      reason += ` [Phase: ${state.phase}]`;
    }
    reason += ' 作業が完了していません。続行してください。';
    if (taskCount > 0) reason += `\n未完了 Task: ${taskCount}個`;
    // original_prompt (keyword-detector) または prompt (skill) 表示
    const originalPrompt = state.original_prompt || state.prompt;
    if (originalPrompt) reason += `\n元の作業: ${originalPrompt}`;
    reason += `\n\n完了 時 <promise>${completionPromise}</promise>を出力してください.`;
  }

  return output({ decision: 'block', reason });
}

// ═══════════════════════════════════════════════════════════════════
// QA Mode Handler (legacy state key: web-qa)
//
// 原本 Ultrawork Verification + ralph-loop 組み合わせ:
// 1. Transcriptでanalyze/test 結果 パース (NEW)
// 2. Completion marker (<promise>QA_COMPLETE</promise>) 検索 (NEW)
// 3. State ファイルのall_passing チェック (既存 Fallback)
// 4. 未完了時 → 具体的な 失敗 情報と一緒に block
// ═══════════════════════════════════════════════════════════════════
function handleWebQa(stateDir, state, projectDir, transcriptPath, sessionId) {
  const cycle = state.cycle ?? 1;
  const maxCycles = state.max_cycles ?? 10;

  // ── Transcript 基盤 完了 検出 (核心新機能) ──
  const qaResult = detectQaCompletion(transcriptPath);

  if (qaResult.complete) {
    clearState(stateDir, 'web-qa');
    console.error(
      `[stop-handler] QA: transcript confirms completion ` +
        `(analyze=${qaResult.analyzeResult}, test=${qaResult.testResult}) at cycle ${cycle}.`,
    );
    return output({});
  }

  // ── Completion Marker チェック ──
  if (detectCompletionMarker(transcriptPath, 'QA_COMPLETE')) {
    clearState(stateDir, 'web-qa');
    console.error(`[stop-handler] QA: completion marker detected at cycle ${cycle}.`);
    return output({});
  }

  // ── State ファイル all_passing チェック (既存方式, Fallback) ──
  if (state.all_passing) {
    clearState(stateDir, 'web-qa');
    console.error(`[stop-handler] QA: all_passing=true in state file.`);
    return output({});
  }

  // ── Max cycles → 終了を許可 ──
  if (cycle >= maxCycles) {
    clearState(stateDir, 'web-qa');
    console.error(`[stop-handler] QA: max cycles (${maxCycles}) reached. Allowing stop.`);
    return output({});
  }

  // ── Error History 追跡 (Safety Gate 4 アクティブ化) ──
  if (qaResult.analyzeResult !== null || qaResult.testResult !== null) {
    const sig = `analyze:${qaResult.analyzeResult},test:${qaResult.testResult}`;
    pushError(state, sig);
  }

  // ── Increment + Block ──
  state.cycle = cycle + 1;
  state.last_checked_at = new Date().toISOString();
  const writeOk = writeState(stateDir, 'web-qa', state);
  if (!writeOk) {
    // writeState 失敗 時 blockすると iteration 未増加→ 無限ループ危険
    console.error('[stop-handler] QA: writeState failed. Allowing stop to prevent infinite loop.');
    return output({});
  }

  let reason = `[QA - Cycle ${cycle + 1}/${maxCycles}]`;

  // Transcript 分析 結果をreasonに含む (原本の continuation promptに該当)
  if (qaResult.analyzeResult === null && qaResult.testResult === null) {
    reason += ' 静的分析とテストをまだ実行していません。';
  } else {
    if (qaResult.analyzeResult === false) reason += '\n  analyze: FAIL';
    else if (qaResult.analyzeResult === null) reason += '\n  analyze: 未実行';
    else reason += '\n  analyze: PASS';

    if (qaResult.testResult === false) reason += '\n  test: FAIL';
    else if (qaResult.testResult === null) reason += '\n  test: 未実行';
    else reason += '\n  test: PASS';
  }

  reason += '\n\n実行順序:';
  reason += `\n1. ${DEFAULT_ANALYZE_COMMAND} - 静的分析`;
  reason += `\n2. ${DEFAULT_TEST_COMMAND} - テスト`;
  reason += '\n3. 失敗時はコード修正後に再検証';
  reason += '\n\n全て通過時 <promise>QA_COMPLETE</promise>を出力してください.';

  if (state.last_failure) {
    reason += `\n\n前回の失敗: ${state.last_failure}`;
  }

  return output({ decision: 'block', reason });
}

// ═══════════════════════════════════════════════════════════════════
// Turbo Mode Handler
//
// 原本 todo-continuation-enforcerの簡素化 ポーティング:
// - incomplete todo count → Claude Code Task count
// - countdown + inject → block + reason
// ═══════════════════════════════════════════════════════════════════
function handleTurbo(stateDir, state, projectDir, transcriptPath, sessionId) {
  const count = (state.reinforcement_count ?? 0) + 1;
  const maxCount = state.max_reinforcements ?? 30;

  // ── Max reinforcements → 終了を許可 ──
  if (count > maxCount) {
    clearState(stateDir, 'turbo');
    console.error(`[stop-handler] Turbo: max reinforcements (${maxCount}) reached. Allowing stop.`);
    return output({});
  }

  const taskCount = countIncompleteTasks(sessionId);

  state.reinforcement_count = count;
  state.last_checked_at = new Date().toISOString();
  const writeOk = writeState(stateDir, 'turbo', state);
  if (!writeOk) {
    console.error(
      '[stop-handler] Turbo: writeState failed. Allowing stop to prevent infinite loop.',
    );
    return output({});
  }

  let reason = `[TURBO #${count}/${maxCount}]`;

  if (taskCount > 0) {
    reason += ` 未完了 Task: ${taskCount}個. 作業を続けてください。`;
  } else if (count >= 3) {
    reason += ' 全作業完了時 /cancelで終了してください.';
  } else {
    reason += ' 作業を続けてください。';
  }

  // original_prompt 表示 (keyword-detectorが設定)
  const originalPrompt = state.original_prompt || state.prompt;
  if (originalPrompt) {
    reason += `\n元の作業: ${originalPrompt}`;
  }

  return output({ decision: 'block', reason });
}

// ═══════════════════════════════════════════════════════════════════
// Utility
// ═══════════════════════════════════════════════════════════════════
function formatMode(mode) {
  const map = {
    persistent: 'PERSISTENT',
    'web-qa': 'QA',
    turbo: 'TURBO',
  };
  return map[mode] || mode.toUpperCase();
}

main();
