#!/usr/bin/env node

/**
 * analyze-guard.mjs - Stop Hook
 *
 * コード変更後の静的分析(lint/analyze)が実行/通過されていない場合
 * Claudeに静的分析実行を指示する軽量Stop Hook.
 *
 * 核心原則:
 * ┌─────────────────────────────────────────────────────────┐
 * │ 静的分析コマンドをフックから直接実行しない (アンチパターン)     │
 * │ → Transcript パースで状態のみ 確認 (数十ms)              │
 * │ → Claudeに "直接実行しろ"と指示                        │
 * │ → ClaudeがBashツールで lint/analyze 実行 + エラー 修正    │
 * └─────────────────────────────────────────────────────────┘
 *
 * 動作 フロー:
 * 1. Stop イベント → Safety Gate 通過
 * 2. Transcriptで最後 ソース 変更 + analyze 結果 パース
 * 3. 変更 後 analyze 未通過 → block + 修正 指示
 * 4. Claudeがanalyze 実行 → エラー 修正 → 再度 Stop
 * 5. stop_hook_active=true → 許可 (無限ループ防止)
 *
 * アクティブモード(persistent/qa/turbo)では スキップ:
 * → stop-handler.mjsに委任 (重複 ブロック 防止)
 */

import { detectAnalyzeStatus } from './lib/transcript.mjs';
import { readStdin, output, isContextLimitStop, isUserAbort } from './lib/utils.mjs';
import {
  readState,
  isStale,
  ensureStateDir,
  isSessionOwned,
  SUPPORTED_MODES,
} from './lib/state.mjs';
import { join } from 'path';

async function main() {
  try {
    const data = await readStdin();

    // ═══════════════════════════════════════════════════════════
    // Safety Gate 1: Context Limit → 絶対にブロック禁止
    // ═══════════════════════════════════════════════════════════
    if (isContextLimitStop(data)) return output({});

    // ═══════════════════════════════════════════════════════════
    // Safety Gate 2: ユーザーキャンセル → 即時尊重
    // ═══════════════════════════════════════════════════════════
    if (isUserAbort(data)) return output({});

    // ═══════════════════════════════════════════════════════════
    // Safety Gate 3: 既に Stop Hookにより 一度 継続された
    // → 無限ループ防止. 1回 block 後には 許可.
    // ═══════════════════════════════════════════════════════════
    if (data.stop_hook_active) return output({});

    // ═══════════════════════════════════════════════════════════
    // Safety Gate 4: アクティブモード → stop-handlerに委任
    // persistent/qa/turbo モードは 独自の analyze チェックがある.
    // 重複 ブロックを防止するために スキップ.
    // ═══════════════════════════════════════════════════════════
    const projectDir = process.env.CLAUDE_PROJECT_DIR || data.cwd || process.cwd();
    const stateDir = join(projectDir, '.claude', 'state');
    const sessionId = data.session_id || '';
    ensureStateDir(stateDir);

    for (const mode of SUPPORTED_MODES) {
      const state = readState(stateDir, mode);
      if (state?.active && !isStale(state) && isSessionOwned(state, sessionId)) return output({});
    }

    // ═══════════════════════════════════════════════════════════
    // Transcript 分析: コード 変更 + analyze 状態
    // ═══════════════════════════════════════════════════════════
    const transcriptPath = data.transcript_path || '';
    const { hasCodeChange, analyzeResult } = detectAnalyzeStatus(transcriptPath);
    const changed = Boolean(hasCodeChange);

    // コード 変更 なし → 許可
    if (!changed) return output({});

    // analyze 通過→ 許可
    if (analyzeResult === true) return output({});

    // ═══════════════════════════════════════════════════════════
    // Block: analyze 未実行 または 失敗
    // ═══════════════════════════════════════════════════════════
    const analyzeCommand = process.env.CLAUDE_QA_ANALYZE_CMD || 'npm run lint';
    let reason = '[Analyze Guard] ソース ファイルが変更されましたが ';

    if (analyzeResult === false) {
      reason += '静的分析でエラーが発見されました.\n';
      reason += `エラーを修正し ${analyzeCommand}を再度実行して通過を確認してください.`;
    } else {
      reason += '静的分析が実行されていません.\n';
      reason += `${analyzeCommand}を実行し, エラーががあれば 修正した後に再度実行してください.`;
    }

    return output({ decision: 'block', reason });
  } catch (error) {
    // Hook エラー時は安全に終了を許可 (deadlock 絶対 防止)
    console.error(`[analyze-guard] ${error.message}`);
    return output({});
  }
}

main();
