#!/usr/bin/env node

/**
 * Hookメカニズム統合テスト
 *
 * 5大メカニズムの動作を検証:
 * 1. ralph-loop → stop-handler.mjs (Persistent/QA/Turbo)
 * 2. todo-continuation-enforcer → stop-handler.mjs (Task カウント)
 * 3. stop-continuation-guard → stop-handler.mjs (Safety Gates)
 * 4. Sisyphus agent → pre-tool-enforcer.mjs (状態 リマインダー)
 * 5. Atlas hook → qa-write-guard.mjs (Write 保護)
 *
 * 使用法: node .claude/scripts/test-hooks.mjs
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';

// ── モジュールインポート (最上位) ──
import {
  readState,
  writeState,
  clearState,
  isStale,
  getActiveMode,
  hasSameErrorRepeated,
  ensureStateDir,
} from './lib/state.mjs';
import { detectCompletionMarker, detectQaCompletion } from './lib/transcript.mjs';
import { isContextLimitStop, isUserAbort, parsePlanProgress } from './lib/utils.mjs';

// ═══════════════════════════════════════════════════════════════════
// テストユーティリティ
// ═══════════════════════════════════════════════════════════════════

const PROJECT_DIR = process.cwd();
const SCRIPTS_DIR = join(PROJECT_DIR, '.claude', 'scripts');

function createTestDir() {
  const dir = join(tmpdir(), `hook-test-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  mkdirSync(dir, { recursive: true });
  mkdirSync(join(dir, '.claude', 'state'), { recursive: true });
  return dir;
}

function cleanupTestDir(dir) {
  try {
    rmSync(dir, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}

function runHook(scriptName, stdinData, env = {}) {
  const scriptPath = join(SCRIPTS_DIR, scriptName);
  const input = JSON.stringify(stdinData);
  try {
    const result = execSync(`echo '${input.replace(/'/g, "'\\''")}' | node "${scriptPath}"`, {
      cwd: PROJECT_DIR,
      encoding: 'utf-8',
      timeout: 10000,
      env: { ...process.env, ...env },
    });
    const lines = result
      .trim()
      .split('\n')
      .filter((l) => l.trim());
    return JSON.parse(lines[lines.length - 1]);
  } catch (error) {
    if (error.stdout) {
      const lines = error.stdout
        .trim()
        .split('\n')
        .filter((l) => l.trim());
      if (lines.length > 0) {
        try {
          return JSON.parse(lines[lines.length - 1]);
        } catch {
          /* fall through */
        }
      }
    }
    throw new Error(`Hook ${scriptName} failed: ${error.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════
// 1. lib/state.mjs 単体テスト
// ═══════════════════════════════════════════════════════════════════

describe('lib/state.mjs - State Management', () => {
  let testDir;

  beforeEach(() => {
    testDir = join(tmpdir(), `state-test-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    mkdirSync(testDir, { recursive: true });
  });

  it('writeState + readState: 基本 CRUD', () => {
    const state = { active: true, iteration: 1, max_iterations: 10 };
    const ok = writeState(testDir, 'persistent', state);
    assert.equal(ok, true, 'writeState 成功');

    const read = readState(testDir, 'persistent');
    assert.deepEqual(read, state, 'readState 結果 一致');
    cleanupTestDir(testDir);
  });

  it('readState: 存在しないモード → null', () => {
    const result = readState(testDir, 'nonexistent');
    assert.equal(result, null);
    cleanupTestDir(testDir);
  });

  it('clearState: ファイル 削除', () => {
    writeState(testDir, 'turbo', { active: true });
    assert.ok(existsSync(join(testDir, 'turbo-state.json')));
    clearState(testDir, 'turbo');
    assert.ok(!existsSync(join(testDir, 'turbo-state.json')));
    cleanupTestDir(testDir);
  });

  it('clearState: 存在しないファイル削除 → エラーなし', () => {
    const ok = clearState(testDir, 'nonexistent');
    assert.equal(ok, true);
    cleanupTestDir(testDir);
  });

  it('isStale: 最近 state → false', () => {
    assert.equal(isStale({ last_checked_at: new Date().toISOString() }), false);
  });

  it('isStale: 25時間前の state → true', () => {
    const old = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    assert.equal(isStale({ last_checked_at: old }), true);
  });

  it('isStale: 24時間境界 - 1秒前 → false (boundary)', () => {
    const justInside = new Date(Date.now() - (24 * 60 * 60 * 1000 - 1000)).toISOString();
    assert.equal(isStale({ last_checked_at: justInside }), false);
  });

  it('isStale: 24時間境界 + 1秒後 → true (boundary)', () => {
    const justOutside = new Date(Date.now() - (24 * 60 * 60 * 1000 + 1000)).toISOString();
    assert.equal(isStale({ last_checked_at: justOutside }), true);
  });

  it('isStale: null → true', () => {
    assert.equal(isStale(null), true);
  });

  it('isStale: timestampなし → true', () => {
    assert.equal(isStale({}), true);
  });

  it('getActiveMode: persistent 優先', () => {
    writeState(testDir, 'persistent', { active: true, last_checked_at: new Date().toISOString() });
    writeState(testDir, 'turbo', { active: true, last_checked_at: new Date().toISOString() });
    assert.equal(getActiveMode(testDir).mode, 'persistent');
    cleanupTestDir(testDir);
  });

  it('getActiveMode: persistent がなければ web-qa', () => {
    writeState(testDir, 'web-qa', { active: true, last_checked_at: new Date().toISOString() });
    writeState(testDir, 'turbo', { active: true, last_checked_at: new Date().toISOString() });
    assert.equal(getActiveMode(testDir).mode, 'web-qa');
    cleanupTestDir(testDir);
  });

  it('getActiveMode: アクティブなし → null', () => {
    assert.equal(getActiveMode(testDir), null);
    cleanupTestDir(testDir);
  });

  it('getActiveMode: stale状態無視', () => {
    const old = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    writeState(testDir, 'persistent', { active: true, last_checked_at: old });
    assert.equal(getActiveMode(testDir), null);
    cleanupTestDir(testDir);
  });

  it('hasSameErrorRepeated: 同一エラー 3回 → true', () => {
    assert.equal(hasSameErrorRepeated({ error_history: ['e', 'e', 'e'] }, 3), true);
  });

  it('hasSameErrorRepeated: 異なるエラー混合 → false', () => {
    assert.equal(hasSameErrorRepeated({ error_history: ['a', 'b', 'a'] }, 3), false);
  });

  it('hasSameErrorRepeated: 不足した履歴 → false', () => {
    assert.equal(hasSameErrorRepeated({ error_history: ['e', 'e'] }, 3), false);
  });

  it('hasSameErrorRepeated: null → false', () => {
    assert.equal(hasSameErrorRepeated(null, 3), false);
    assert.equal(hasSameErrorRepeated({}, 3), false);
  });

  it('ensureStateDir: ディレクトリ 生成', () => {
    const newDir = join(testDir, 'sub');
    assert.ok(!existsSync(newDir));
    ensureStateDir(newDir);
    assert.ok(existsSync(newDir));
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 2. lib/transcript.mjs 単体テスト
// ═══════════════════════════════════════════════════════════════════

describe('lib/transcript.mjs - Transcript Parsing', () => {
  let testDir;

  beforeEach(() => {
    testDir = join(
      tmpdir(),
      `transcript-test-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    );
    mkdirSync(testDir, { recursive: true });
  });

  it('detectCompletionMarker: DONE マーカー検出', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'Working...' }),
        JSON.stringify({ type: 'assistant', content: '<promise>DONE</promise>' }),
      ].join('\n'),
    );
    assert.equal(detectCompletionMarker(tPath, 'DONE'), true);
    cleanupTestDir(testDir);
  });

  it('detectCompletionMarker: user メッセージ スキップ', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(tPath, JSON.stringify({ type: 'user', content: '<promise>DONE</promise>' }));
    assert.equal(detectCompletionMarker(tPath, 'DONE'), false);
    cleanupTestDir(testDir);
  });

  it('detectCompletionMarker: マーカーなし → false', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(tPath, JSON.stringify({ type: 'assistant', content: 'Still working' }));
    assert.equal(detectCompletionMarker(tPath, 'DONE'), false);
    cleanupTestDir(testDir);
  });

  it('detectCompletionMarker: ファイル なし → false', () => {
    assert.equal(detectCompletionMarker('/nonexistent/path', 'DONE'), false);
  });

  it('detectCompletionMarker: QA_COMPLETE マーカー', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      JSON.stringify({ type: 'assistant', content: '<promise>QA_COMPLETE</promise>' }),
    );
    assert.equal(detectCompletionMarker(tPath, 'QA_COMPLETE'), true);
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: analyze+test 全て通過', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true);
    assert.equal(r.analyzeResult, true);
    assert.equal(r.testResult, true);
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: analyze 失敗', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: '3 issues found' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, false);
    assert.equal(r.analyzeResult, false);
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: コード変更後 stale 結果 (2-pass)', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
        JSON.stringify({
          type: 'tool_use',
          tool_name: 'Edit',
          input: { file_path: 'src/app/page.tsx' },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, false, 'コード変更後 stale 結果は 無視');
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: ファイル なし', () => {
    const r = detectQaCompletion('/nonexistent');
    assert.equal(r.complete, false);
    assert.equal(r.analyzeResult, null);
  });

  it('detectQaCompletion: assistant メッセージの"Edit" 言及 → 2-pass false positive 防止', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
        JSON.stringify({
          type: 'assistant',
          content: 'I used "Edit" to modify src/app/page.tsx successfully.',
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, 'assistant メッセージは コード 変更とみなさない');
    assert.equal(r.analyzeResult, true);
    assert.equal(r.testResult, true);
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: 実際の tool_use エントリのみ コード 変更で検出', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
        JSON.stringify({
          type: 'tool_use',
          tool_name: 'Edit',
          input: { file_path: 'src/features/game/components/GameBoard.tsx' },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, false, '実際の tool_use 後のstale 結果は 無視');
    cleanupTestDir(testDir);
  });

  it('detectQaCompletion: .min.js tool_useは コード 変更 無視', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
        JSON.stringify({
          type: 'tool_use',
          tool_name: 'Write',
          input: { file_path: 'dist/bundle.min.js' },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, '.min.jsは生成ファイルのため無視');
    cleanupTestDir(testDir);
  });

  // ═══════════════════════════════════════════════════════════
  // 実際の Claude Code transcript 形式 テスト (プロダクション検証)
  //
  // Claude Codeの実際の transcriptは tool_useを
  // assistant.message.content[] 内部にネストします:
  //   { type: "assistant", message: { content: [
  //     { type: "tool_use", name: "Edit", input: { file_path: "..." } }
  //   ]}}
  // ═══════════════════════════════════════════════════════════

  it('実際の形式: assistant.message.content[] 内部 tool_use 検出', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
        // 実際 Claude Code 形式のEdit tool_use
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              { type: 'text', text: '修正します.' },
              {
                type: 'tool_use',
                id: 'toolu_01ABC',
                name: 'Edit',
                input: {
                  file_path: '/Users/test/src/app/page.tsx',
                  old_string: 'old',
                  new_string: 'new',
                },
              },
            ],
          },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, false, '実際 形式でコード変更後 stale 結果 無視');
    assert.equal(r.analyzeResult, null, 'コード 変更 以後 analyze 未実行');
    assert.equal(r.testResult, null, 'コード 変更 以後 test 未実行');
    cleanupTestDir(testDir);
  });

  it('実際 形式: コード変更後 再検証 通と→ complete', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        // 以前 結果 (stale)
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        // コード 変更
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 'toolu_01',
                name: 'Edit',
                input: {
                  file_path: 'src/features/game/utils.ts',
                  old_string: 'a',
                  new_string: 'b',
                },
              },
            ],
          },
        }),
        // 変更 後 再検証 (有効)
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, 'コード変更後 再検証 通過');
    assert.equal(r.analyzeResult, true);
    assert.equal(r.testResult, true);
    cleanupTestDir(testDir);
  });

  it('実際 形式: assistantのテキスト "Edit" 言及 → false positive 防止', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
        // テキストでEditとファイルパスを言及するのみ tool_useではない
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              { type: 'text', text: 'I used Edit tool to modify src/app/page.tsx successfully.' },
            ],
          },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, 'テキスト 言及はコード 変更がではない');
    cleanupTestDir(testDir);
  });

  it('実際 形式: .min.js Write → コード 変更 無視', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 'toolu_02',
                name: 'Write',
                input: {
                  file_path: 'dist/app.min.js',
                  content: '// minified',
                },
              },
            ],
          },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, '.min.jsは生成ファイルのため無視');
    cleanupTestDir(testDir);
  });

  it('実際 形式: .map Write → コード 変更 無視', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 'toolu_03',
                name: 'Write',
                input: {
                  file_path: 'dist/app.js.map',
                  content: '// sourcemap',
                },
              },
            ],
          },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, true, '.mapはソースマップファイルのため無視');
    cleanupTestDir(testDir);
  });

  it('実際 形式: 混合 content ブロック (text + tool_use) 検出', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed! No issues found!' }] },
        }),
        // 一つのassistant メッセージにtext + tool_useが一緒に ある 場合
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              { type: 'text', text: 'コードを 修正します。' },
              {
                type: 'tool_use',
                id: 'toolu_04',
                name: 'Edit',
                input: {
                  file_path: 'src/components/Widget.tsx',
                  old_string: 'x',
                  new_string: 'y',
                },
              },
              {
                type: 'tool_use',
                id: 'toolu_05',
                name: 'Edit',
                input: {
                  file_path: 'src/shared/lib/utils.ts',
                  old_string: 'a',
                  new_string: 'b',
                },
              },
            ],
          },
        }),
      ].join('\n'),
    );
    const r = detectQaCompletion(tPath);
    assert.equal(r.complete, false, '混合 ブロックでもtool_use 検出');
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3. lib/utils.mjs 単体テスト
// ═══════════════════════════════════════════════════════════════════

describe('lib/utils.mjs - Utility Functions', () => {
  let testDir;

  beforeEach(() => {
    testDir = join(tmpdir(), `utils-test-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    mkdirSync(testDir, { recursive: true });
  });

  it('isContextLimitStop: context_limit → true', () => {
    assert.equal(isContextLimitStop({ stop_reason: 'context_limit' }), true);
  });

  it('isContextLimitStop: max_tokens → true', () => {
    assert.equal(isContextLimitStop({ stop_reason: 'max_tokens' }), true);
  });

  it('isContextLimitStop: end_turn_reason 検出', () => {
    assert.equal(isContextLimitStop({ end_turn_reason: 'context_window_exceeded' }), true);
  });

  it('isContextLimitStop: 一般 終了 → false', () => {
    assert.equal(isContextLimitStop({ stop_reason: 'end_turn' }), false);
  });

  it('isContextLimitStop: 空の データ → false', () => {
    assert.equal(isContextLimitStop({}), false);
  });

  it('isUserAbort: user_requested=true → true', () => {
    assert.equal(isUserAbort({ user_requested: true }), true);
  });

  it('isUserAbort: stop_reason=aborted → true', () => {
    assert.equal(isUserAbort({ stop_reason: 'aborted' }), true);
  });

  it('isUserAbort: stop_reason=cancel → true', () => {
    assert.equal(isUserAbort({ stop_reason: 'cancel' }), true);
  });

  it('isUserAbort: user_cancel 含む → true', () => {
    assert.equal(isUserAbort({ stop_reason: 'user_cancel_requested' }), true);
  });

  it('isUserAbort: 一般 終了 → false', () => {
    assert.equal(isUserAbort({ stop_reason: 'end_turn' }), false);
  });

  it('isUserAbort: 空の データ → false', () => {
    assert.equal(isUserAbort({}), false);
  });

  it('parsePlanProgress: チェックボックス パース', () => {
    const f = join(testDir, 'plan.md');
    writeFileSync(f, '- [x] Task 1\n- [ ] Task 2\n- [X] Task 3\n- [ ] Task 4\n');
    const r = parsePlanProgress(f);
    assert.equal(r.total, 4);
    assert.equal(r.completed, 2);
    assert.deepEqual(r.uncheckedItems, ['Task 2', 'Task 4']);
    cleanupTestDir(testDir);
  });

  it('parsePlanProgress: コード ブロック 内部 無視', () => {
    const f = join(testDir, 'plan.md');
    writeFileSync(f, '- [x] Real\n```\n- [ ] In code\n```\n- [ ] Also real\n');
    const r = parsePlanProgress(f);
    assert.equal(r.total, 2);
    assert.equal(r.completed, 1);
    cleanupTestDir(testDir);
  });

  it('parsePlanProgress: ファイル なし → null', () => {
    assert.equal(parsePlanProgress('/nonexistent'), null);
  });

  it('parsePlanProgress: チェックボックス なし', () => {
    const f = join(testDir, 'empty.md');
    writeFileSync(f, 'No checkboxes');
    const r = parsePlanProgress(f);
    assert.equal(r.total, 0);
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 4. stop-handler.mjs 結合テスト (3大 メカニズム)
// ═══════════════════════════════════════════════════════════════════

describe('stop-handler.mjs - 3大 メカニズム 統合', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  // ── Safety Gates ──

  it('Safety Gate: context_limit → ブロック 禁止', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { stop_reason: 'context_limit', cwd: testDir },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    cleanupTestDir(testDir);
  });

  it('Safety Gate: user abort → 即時尊重', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { user_requested: true, cwd: testDir },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    cleanupTestDir(testDir);
  });

  it('Safety Gate: アクティブモードなし → 正常終了', () => {
    const r = runHook('stop-handler.mjs', { cwd: testDir }, { CLAUDE_PROJECT_DIR: testDir });
    assert.ok(!r.decision);
    cleanupTestDir(testDir);
  });

  it('Safety Gate: 同一エラー 3回 → block + 中断', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      error_history: ['e', 'e', 'e'],
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook('stop-handler.mjs', { cwd: testDir }, { CLAUDE_PROJECT_DIR: testDir });
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('中断'));
    cleanupTestDir(testDir);
  });

  // ── Persistent (ralph-loop) ──

  it('Persistent: 未完了 → block + continuation', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      original_prompt: 'テスト',
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('PERSISTENT'));
    assert.ok(r.reason.includes('2/20'));
    assert.ok(r.reason.includes('<promise>'));
    assert.equal(readState(stateDir, 'persistent').iteration, 2);
    cleanupTestDir(testDir);
  });

  it('Persistent: max iterations → 終了 + state 整理', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 20,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    assert.equal(readState(stateDir, 'persistent'), null);
    cleanupTestDir(testDir);
  });

  it('Persistent: <promise>DONE</promise> → 自動 終了', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(tPath, JSON.stringify({ type: 'assistant', content: '<promise>DONE</promise>' }));
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 3,
      max_iterations: 20,
      completion_promise: 'DONE',
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: tPath },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    assert.equal(readState(stateDir, 'persistent'), null);
    cleanupTestDir(testDir);
  });

  it('Persistent: plan 全て 完了 → 自動 終了', () => {
    writeFileSync(join(testDir, 'plan.md'), '- [x] T1\n- [x] T2\n- [x] T3\n');
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 5,
      max_iterations: 20,
      completion: { type: 'plan', plan_file: 'plan.md' },
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    cleanupTestDir(testDir);
  });

  it('Persistent: plan 未完了 → block + 進捗率', () => {
    writeFileSync(join(testDir, 'plan.md'), '- [x] T1\n- [ ] T2\n- [ ] T3\n');
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 2,
      max_iterations: 20,
      completion: { type: 'plan', plan_file: 'plan.md' },
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('1/3'));
    cleanupTestDir(testDir);
  });

  // ── Web QA ──

  it('Web QA: 未完了 → block + 案内', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      max_cycles: 10,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('[QA'));
    assert.ok(r.reason.includes('lint') || r.reason.includes('静的分析'));
    assert.equal(readState(stateDir, 'web-qa').cycle, 2);
    cleanupTestDir(testDir);
  });

  it('Web QA: max cycles → 終了', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 10,
      max_cycles: 10,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    assert.equal(readState(stateDir, 'web-qa'), null);
    cleanupTestDir(testDir);
  });

  it('Web QA: transcript 完了 検出 → 自動 終了', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({ type: 'assistant', content: 'No issues found!' }),
        JSON.stringify({ type: 'assistant', content: 'All tests passed!' }),
      ].join('\n'),
    );
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 3,
      max_cycles: 10,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: tPath },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    assert.equal(readState(stateDir, 'web-qa'), null);
    cleanupTestDir(testDir);
  });

  it('Web QA: error_history 累積 (Safety Gate 4 アクティブ化)', () => {
    // transcriptにanalyze fail 結果のみ ある状態で3回 繰り返し
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [JSON.stringify({ type: 'assistant', content: '3 issues found' })].join('\n'),
    );
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      max_cycles: 10,
      error_history: [],
      last_checked_at: new Date().toISOString(),
    });
    // 1回目 実行
    runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: tPath },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    const s1 = readState(stateDir, 'web-qa');
    assert.ok(s1.error_history.length >= 1, 'error_historyに追加された');
    assert.ok(s1.error_history[0].includes('analyze:false'), '失敗 時シグニチャ 記録');
    cleanupTestDir(testDir);
  });

  it('Web QA: 同一エラー 3回 → Safety Gate 4 中断', () => {
    // error_historyに同一時間シグニチャ 3個 事前に 設定
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 4,
      max_cycles: 10,
      error_history: [
        'analyze:false,test:null',
        'analyze:false,test:null',
        'analyze:false,test:null',
      ],
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('中断'), 'Safety Gate 4 作動');
    cleanupTestDir(testDir);
  });

  it('Web QA: all_passing=true → 終了 (Fallback)', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 2,
      max_cycles: 10,
      all_passing: true,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    cleanupTestDir(testDir);
  });

  it('Web QA: 実際 形式 - コード変更後 stale → block', () => {
    const tPath = join(testDir, 'transcript.jsonl');
    writeFileSync(
      tPath,
      [
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'No issues found!' }] },
        }),
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'text', text: 'All tests passed!' }] },
        }),
        // 実際 Claude Code 形式のEdit
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 'toolu_01',
                name: 'Edit',
                input: {
                  file_path: 'src/app/page.tsx',
                  old_string: 'a',
                  new_string: 'b',
                },
              },
            ],
          },
        }),
      ].join('\n'),
    );
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      max_cycles: 10,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: tPath },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block', '実際 形式でstale 結果 → block');
    assert.ok(
      r.reason.includes('未実行') || r.reason.includes('[QA'),
      'コード変更後 再検証 必要 案内',
    );
    cleanupTestDir(testDir);
  });

  // ── Turbo ──

  it('Turbo: 未完了 → block + 案内', () => {
    writeState(stateDir, 'turbo', {
      active: true,
      reinforcement_count: 0,
      max_reinforcements: 30,
      original_prompt: '並列 作業',
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('TURBO'));
    assert.ok(r.reason.includes('1/30'));
    assert.ok(r.reason.includes('並列 作業'));
    assert.equal(readState(stateDir, 'turbo').reinforcement_count, 1);
    cleanupTestDir(testDir);
  });

  it('Turbo: max reinforcements → 終了', () => {
    writeState(stateDir, 'turbo', {
      active: true,
      reinforcement_count: 30,
      max_reinforcements: 30,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(!r.decision);
    assert.equal(readState(stateDir, 'turbo'), null);
    cleanupTestDir(testDir);
  });

  // ── モード 優先順位 ──

  it('モード 優先順位: persistent > turbo', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    writeState(stateDir, 'turbo', {
      active: true,
      reinforcement_count: 0,
      max_reinforcements: 30,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('PERSISTENT'));
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 5. keyword-detector.mjs 結合テスト
// ═══════════════════════════════════════════════════════════════════

describe('keyword-detector.mjs - キーワード 検出', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  it('韓国語: "最後まで" → persistent', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: '最後まで 完了してください',
      directory: testDir,
    });
    assert.ok(r.hookSpecificOutput.additionalContext.includes('PERSISTENT'));
    assert.ok(readState(stateDir, 'persistent')?.active);
    cleanupTestDir(testDir);
  });

  it('英語: "turbo" → turbo', () => {
    const r = runHook('keyword-detector.mjs', { prompt: 'turbo mode please', directory: testDir });
    assert.ok(r.hookSpecificOutput.additionalContext.includes('TURBO'));
    assert.ok(readState(stateDir, 'turbo')?.active);
    cleanupTestDir(testDir);
  });

  it('韓国語: "キャンセル" → cancel + 状態 整理', () => {
    writeState(stateDir, 'persistent', { active: true, last_checked_at: new Date().toISOString() });
    writeState(stateDir, 'turbo', { active: true, last_checked_at: new Date().toISOString() });
    const r = runHook('keyword-detector.mjs', {
      prompt: 'キャンセルしてください',
      directory: testDir,
    });
    assert.ok(r.hookSpecificOutput.additionalContext.includes('CANCEL'));
    assert.equal(readState(stateDir, 'persistent'), null);
    assert.equal(readState(stateDir, 'turbo'), null);
    cleanupTestDir(testDir);
  });

  it('競合解決: feature-pilot + bug-fix → feature-pilot 優先', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'feature-pilotでバグ 修正してください',
      directory: testDir,
    });
    const ctx = r.hookSpecificOutput.additionalContext;
    assert.ok(ctx.includes('FEATURE-PILOT'));
    assert.ok(!ctx.includes('Skill: bug-fix'), 'bug-fix スキルは呼び出しされない ない');
    cleanupTestDir(testDir);
  });

  it('persistent + turbo 自動連携', () => {
    runHook('keyword-detector.mjs', { prompt: '最後まで してください', directory: testDir });
    assert.ok(readState(stateDir, 'persistent')?.active);
    assert.ok(readState(stateDir, 'turbo')?.active);
    cleanupTestDir(testDir);
  });

  it('コード ブロック 内 キーワード 無視', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: '見てください:\n```\nconst persistent = true;\n```\n終わり',
      directory: testDir,
    });
    assert.ok(!r.hookSpecificOutput, 'コード ブロック 内 キーワード 無視');
    cleanupTestDir(testDir);
  });

  it('マークダウン テーブル 内 キーワード 無視', () => {
    const tableText =
      'メカニズム 比較:\n| 原本 | ポーティング |\n|------|------|\n| ralph-loop | persistent |\n| ultrawork | turbo |\n分析 終わり';
    const r = runHook('keyword-detector.mjs', {
      prompt: tableText,
      directory: testDir,
    });
    assert.ok(!r.hookSpecificOutput, 'マークダウン テーブル 内 persistent/turbo 無視');
    cleanupTestDir(testDir);
  });

  it('マークダウン引用文 内 キーワード 無視', () => {
    const quoteText = '参考:\n> persistent modeは 継続 モードです\n以上です';
    const r = runHook('keyword-detector.mjs', {
      prompt: quoteText,
      directory: testDir,
    });
    assert.ok(!r.hookSpecificOutput, '引用文 内 persistent 無視');
    cleanupTestDir(testDir);
  });

  it('スラッシュ時 コマンド パススルー', () => {
    const r = runHook('keyword-detector.mjs', { prompt: '/commit', directory: testDir });
    assert.equal(r.continue, true);
    assert.ok(!r.hookSpecificOutput);
    cleanupTestDir(testDir);
  });

  it('一般 プロンプト → パススルー', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'が関数 説明してください',
      directory: testDir,
    });
    assert.equal(r.continue, true);
    cleanupTestDir(testDir);
  });

  it('冪等性: 既に アクティブであれば 再生成 しない', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 5,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    runHook('keyword-detector.mjs', { prompt: '最後まで してください', directory: testDir });
    assert.equal(readState(stateDir, 'persistent').iteration, 5, '既存 state 維持');
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 6. qa-write-guard.mjs (Atlas ポーティング)
// ═══════════════════════════════════════════════════════════════════

describe('qa-write-guard.mjs - Write 保護', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  it('QA 非アクティブ → すべての Write 許可', () => {
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Write',
        tool_input: { file_path: '/tests/app.test.ts', content: '' },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(r.hookSpecificOutput?.permissionDecision !== 'deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: .d.ts → deny (生成ファイル)', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Edit',
        tool_input: { file_path: '/src/types/user.d.ts' },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.hookSpecificOutput.permissionDecision, 'deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: .min.js → deny (生成ファイル)', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Edit',
        tool_input: { file_path: '/dist/bundle.min.js' },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.hookSpecificOutput.permissionDecision, 'deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: テスト ファイル 空にする → deny', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    const target = join(testDir, 'tests', 'widget.test.ts');
    mkdirSync(join(testDir, 'tests'), { recursive: true });
    writeFileSync(target, 'existing test content long enough to be considered existing');
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Write',
        tool_input: { file_path: target, content: '// empty' },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.hookSpecificOutput.permissionDecision, 'deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: assertion 大量 削除 → deny', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    // 条件: expectCountOld > 0, expectCountNew === 0, oldStr.length > newStr.length * 2
    // 改行 なしが十分に 長い old_stringでテスト (shell escape 安全)
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Edit',
        tool_input: {
          file_path: '/tests/auth.test.ts',
          old_string:
            'expect(result, isTrue); expect(user.name, equals(test)); expect(user.id, equals(1)); expect(valid, isFalse);',
          new_string: '// tests removed',
        },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.hookSpecificOutput?.permissionDecision, 'deny', 'assertion 大量 削除 時 deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: 一般 コード Edit → 許可', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Edit',
        tool_input: { file_path: '/src/app/page.tsx', old_string: 'a', new_string: 'b' },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(r.hookSpecificOutput?.permissionDecision !== 'deny');
    cleanupTestDir(testDir);
  });

  it('QA アクティブ: テスト Write (十分な 内容) → 許可', () => {
    writeState(stateDir, 'web-qa', {
      active: true,
      cycle: 1,
      last_checked_at: new Date().toISOString(),
    });
    const content =
      "import { describe, it, expect } from 'vitest';\ndescribe('test', () => {\n  it('works', () => { expect(1).toBe(1); });\n});";
    const r = runHook(
      'qa-write-guard.mjs',
      {
        tool_name: 'Write',
        tool_input: { file_path: '/tests/new.test.ts', content },
        cwd: testDir,
      },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.ok(r.hookSpecificOutput?.permissionDecision !== 'deny');
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 7. pre-tool-enforcer.mjs (Sisyphus)
// ═══════════════════════════════════════════════════════════════════

describe('pre-tool-enforcer.mjs - Sisyphus リマインダー', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  it('アクティブモードなし → パススルー', () => {
    const r = runHook('pre-tool-enforcer.mjs', { tool_name: 'Read', directory: testDir });
    assert.equal(r.continue, true);
    assert.ok(!r.hookSpecificOutput);
    cleanupTestDir(testDir);
  });

  it('Persistent アクティブ → 状態 + ヒント', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 3,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook('pre-tool-enforcer.mjs', { tool_name: 'Bash', directory: testDir });
    assert.equal(r.continue, true);
    const ctx = r.hookSpecificOutput.additionalContext;
    assert.ok(ctx.includes('PERSISTENT 3/20'));
    assert.ok(ctx.includes('並列'));
    cleanupTestDir(testDir);
  });

  it('複数 モード → すべての 状態 表示', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 2,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    writeState(stateDir, 'turbo', {
      active: true,
      reinforcement_count: 5,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook('pre-tool-enforcer.mjs', { tool_name: 'Edit', directory: testDir });
    const ctx = r.hookSpecificOutput.additionalContext;
    assert.ok(ctx.includes('PERSISTENT'));
    assert.ok(ctx.includes('TURBO'));
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 8. session-start.mjs
// ═══════════════════════════════════════════════════════════════════

describe('session-start.mjs - セッション 復元', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  it('アクティブモードなし → パススルー', () => {
    const r = runHook('session-start.mjs', { directory: testDir });
    assert.equal(r.continue, true);
    assert.ok(!r.hookSpecificOutput);
    cleanupTestDir(testDir);
  });

  it('Persistent アクティブ → 復元 メッセージ', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 5,
      max_iterations: 20,
      original_prompt: '機能 実装',
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook('session-start.mjs', { directory: testDir });
    const ctx = r.hookSpecificOutput.additionalContext;
    assert.ok(ctx.includes('PERSISTENT MODE RESTORED'));
    assert.ok(ctx.includes('機能 実装'));
    cleanupTestDir(testDir);
  });

  it('Stale 状態 → 無視', () => {
    const old = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    writeState(stateDir, 'persistent', { active: true, iteration: 5, last_checked_at: old });
    const r = runHook('session-start.mjs', { directory: testDir });
    assert.ok(!r.hookSpecificOutput);
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 9. エラー 耐性 (Deadlock 防止)
// ═══════════════════════════════════════════════════════════════════

describe('エラー 耐性 - Deadlock 防止', () => {
  it('stop-handler: 不正な JSON → 安全 終了', () => {
    try {
      const r = execSync(`echo 'bad' | node "${join(SCRIPTS_DIR, 'stop-handler.mjs')}"`, {
        encoding: 'utf-8',
        timeout: 10000,
      });
      const p = JSON.parse(r.trim().split('\n').pop());
      assert.ok(!p.decision);
    } catch (e) {
      if (e.stdout) {
        const p = JSON.parse(e.stdout.trim().split('\n').pop());
        assert.ok(!p.decision);
      }
    }
  });

  it('keyword-detector: 空の stdin → パススルー', () => {
    const r = runHook('keyword-detector.mjs', {});
    assert.equal(r.continue, true);
  });

  it('pre-tool-enforcer: 不完全 データ → パススルー', () => {
    const r = runHook('pre-tool-enforcer.mjs', {});
    assert.equal(r.continue, true);
  });

  it('qa-write-guard: 不完全 データ → 許可', () => {
    const r = runHook('qa-write-guard.mjs', {});
    assert.ok(r.hookSpecificOutput?.permissionDecision !== 'deny');
  });

  it('stop-handler: writeState 失敗 時 安全 終了 (読み取り専用 ディレクトリ)', () => {
    const badDir = join(tmpdir(), 'hook-test-readonly-' + Date.now());
    mkdirSync(badDir, { recursive: true });
    const badStateDir = join(badDir, '.claude', 'state');
    mkdirSync(badStateDir, { recursive: true });
    // アクティブ 状態 まず 作成
    writeState(badStateDir, 'persistent', {
      active: true,
      iteration: 1,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    // v2.1: ディレクトリを読み取り専用で変更 → atomic writeのtmp ファイル 生成 失敗 誘導
    // (ファイル chmodは atomic writeのrenameに影響 なし)
    try {
      execSync(`chmod 555 "${badStateDir}"`);
      const r = runHook(
        'stop-handler.mjs',
        { cwd: badDir, transcript_path: '' },
        { CLAUDE_PROJECT_DIR: badDir },
      );
      // writeState 失敗 時 blockせずに 安全 終了する必要がある する
      assert.ok(!r.decision, 'writeState 失敗 時 安全 終了 (block しない)');
    } finally {
      execSync(`chmod 755 "${badStateDir}"`);
      cleanupTestDir(badDir);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// 10. v2.1 BUG-1: keyword-detector False Positive 防止
// ═══════════════════════════════════════════════════════════════════

describe('v2.1 BUG-1: keyword-detector False Positive 防止', () => {
  let testDir;

  beforeEach(() => {
    testDir = createTestDir();
  });

  // ── True Positive (マッチングされるべき する) ──

  it('True Positive: "キャンセルしてください" → CANCEL', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'キャンセルしてください',
      directory: testDir,
    });
    assert.ok(r.hookSpecificOutput?.additionalContext?.includes('CANCEL'));
    cleanupTestDir(testDir);
  });

  it('True Positive: "バグ 修正してください" → BUG-FIX', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'バグ 修正してください',
      directory: testDir,
    });
    assert.ok(r.hookSpecificOutput?.additionalContext?.includes('BUG-FIX'));
    cleanupTestDir(testDir);
  });

  it('True Positive: "最後まで してください" → PERSISTENT', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: '最後まで してください',
      directory: testDir,
    });
    assert.ok(r.hookSpecificOutput?.additionalContext?.includes('PERSISTENT'));
    cleanupTestDir(testDir);
  });

  it('True Positive: "止まらないで" → PERSISTENT', () => {
    const r = runHook('keyword-detector.mjs', { prompt: '止まらないで', directory: testDir });
    assert.ok(r.hookSpecificOutput?.additionalContext?.includes('PERSISTENT'));
    cleanupTestDir(testDir);
  });

  it('True Positive: "ターボ モードで" → TURBO', () => {
    const r = runHook('keyword-detector.mjs', { prompt: 'ターボ モードで', directory: testDir });
    assert.ok(r.hookSpecificOutput?.additionalContext?.includes('TURBO'));
    cleanupTestDir(testDir);
  });

  // ── False Positive (マッチングされれば できない) ──

  it('False Positive 防止: "キャンセル 機能の 動作をテストしてください" → CANCEL ではない', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'キャンセル 機能の 動作をテストしてください',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('CANCEL'),
      'キャンセル 機能 説明はCANCELを発同時キーであれば できない',
    );
    cleanupTestDir(testDir);
  });

  it('False Positive 防止: "キャンセルというは キーワードがfalse positiveを引き起こす" → CANCEL ではない', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'キャンセルというは キーワードがfalse positiveを引き起こす',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('CANCEL'),
      '"キャンセルというは" 引用文脈はCANCELを発同時キーであれば できない',
    );
    cleanupTestDir(testDir);
  });

  it('False Positive 防止: "(キャンセル, 中断, cancel)" → CANCEL ではない (括弧 内)', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: '次 キーワードを確認してください: (キャンセル, 中断, cancel)',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('CANCEL'),
      '括弧 内 キーワードは 無視されるべき する',
    );
    cleanupTestDir(testDir);
  });

  it('False Positive 防止: "**キャンセル** スキルが正しく 作動するか" → CANCEL ではない (太字 内)', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: '**キャンセル** スキルが正しく 作動するか 確認してください',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('CANCEL'),
      '太字 内 キーワードは 無視されるべき する',
    );
    cleanupTestDir(testDir);
  });

  it('False Positive 防止: "persistent-modeにについて 説明" → PERSISTENT ではない', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'persistent-modeにについて 説明をしてください',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('PERSISTENT'),
      'ファイル名 + "にについて" 文脈はPERSISTENTを発同時キーであれば できない',
    );
    cleanupTestDir(testDir);
  });

  it('False Positive 防止: "バグ 修正 スキルはどのような 場合に使用するのか" → BUG-FIX ではない', () => {
    const r = runHook('keyword-detector.mjs', {
      prompt: 'バグ 修正 スキルはどのような 場合に使用するのか',
      directory: testDir,
    });
    assert.ok(
      !r.hookSpecificOutput?.additionalContext?.includes('BUG-FIX'),
      '"場合" + 助詞文脈はBUG-FIXを発同時キーであれば できない',
    );
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 11. v2.1 BUG-2: Nullish Coalescing (??) テスト
// ═══════════════════════════════════════════════════════════════════

describe('v2.1 BUG-2: Nullish Coalescing (??)', () => {
  let testDir, stateDir;

  beforeEach(() => {
    testDir = createTestDir();
    stateDir = join(testDir, '.claude', 'state');
  });

  it('iteration=0 → 0 維持 (1がではない)', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 0,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    // iteration=0 → block reasonに"1/20" 表示 (0+1=1)
    assert.ok(r.reason.includes('1/20'), 'iteration 0は正しく 維持されるべき する');
    // stateでiterationが1で増加したか 確認 (0+1=1)
    assert.equal(readState(stateDir, 'persistent').iteration, 1);
    cleanupTestDir(testDir);
  });

  it('max_iterations=0 → 即時終了 (0はmax 到達)', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      iteration: 0,
      max_iterations: 0,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    // iteration(0) >= maxIter(0) → 終了を許可
    assert.ok(!r.decision, 'max_iterations=0は即時終了');
    cleanupTestDir(testDir);
  });

  it('iteration=undefined → 基本値 1 適用', () => {
    writeState(stateDir, 'persistent', {
      active: true,
      max_iterations: 20,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    assert.ok(r.reason.includes('2/20'), 'undefined → 基本値 1 → 増が後 2');
    cleanupTestDir(testDir);
  });

  it('reinforcement_count=0 → 0 維持 (turbo)', () => {
    writeState(stateDir, 'turbo', {
      active: true,
      reinforcement_count: 0,
      max_reinforcements: 30,
      last_checked_at: new Date().toISOString(),
    });
    const r = runHook(
      'stop-handler.mjs',
      { cwd: testDir, transcript_path: '' },
      { CLAUDE_PROJECT_DIR: testDir },
    );
    assert.equal(r.decision, 'block');
    // reinforcement_count=0 → count=(0+1)=1 → "1/30"
    assert.ok(r.reason.includes('1/30'), 'reinforcement_count=0は正しく 維持');
    cleanupTestDir(testDir);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 12. v2.1 BUG-3: アトミック State 書き込み
// ═══════════════════════════════════════════════════════════════════

describe('v2.1 BUG-3: アトミック State 書き込み', () => {
  let testDir;

  beforeEach(() => {
    testDir = join(tmpdir(), `atomic-test-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    mkdirSync(testDir, { recursive: true });
  });

  it('writeState: 一時的 ファイルが残らない ない', () => {
    writeState(testDir, 'persistent', { active: true, iteration: 1 });
    const files = execSync(`ls "${testDir}"`).toString().trim().split('\n');
    const tmpFiles = files.filter((f) => f.includes('.tmp'));
    assert.equal(tmpFiles.length, 0, '一時的 ファイルが残ってがあれば できない');
    cleanupTestDir(testDir);
  });

  it('writeState: アトミック 書き込み 後 CRUD 互換', () => {
    const state = { active: true, iteration: 5, max_iterations: 20 };
    const ok = writeState(testDir, 'web-qa', state);
    assert.equal(ok, true);
    const read = readState(testDir, 'web-qa');
    assert.deepEqual(read, state);
    cleanupTestDir(testDir);
  });
});
