#!/usr/bin/env node

/**
 * Merge Guard - PreToolUse Hook (Bash matcher)
 *
 * `git merge` 実行前に staged changes の有無を確認し、
 * コミットされていない変更が merge により破壊されることを防止します。
 *
 * シナリオ:
 *   1. ユーザーがファイルを stage (git add)
 *   2. git commit 失敗 (pre-commit hook 拒否等)
 *   3. AI が git merge 実行 → staging area 破壊！
 *
 * この Hook が 3 を阻止します:
 *   - Bash コマンドに "git merge" が含まれれば発動
 *   - git diff --cached で staged changes を確認
 *   - staged changes があれば deny
 *
 * 依存性: なし (self-contained)
 * @matcher Bash
 */

import { execSync } from 'child_process';

// ── stdin/stdout helpers (zero-dependency) ──

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf-8'));
  } catch {
    return {};
  }
}

function output(data) {
  console.log(JSON.stringify(data));
}

// ── Core logic ──

/**
 * コマンドが git merge を含むか確認
 * "git merge", "git merge origin/master" 等にマッチ
 * "git merge --abort" は安全なため除外
 */
function isGitMerge(command) {
  if (!command) return false;
  if (/git\s+merge\s+--abort/.test(command)) return false;
  return /git\s+merge\b/.test(command);
}

/**
 * staged changes の有無を確認
 * @returns {string|null} staged ファイルリスト（なければ null）
 */
function getStagedChanges(cwd) {
  try {
    const result = execSync('git diff --cached --name-only', {
      cwd,
      encoding: 'utf-8',
      timeout: 5000,
    }).trim();
    return result || null;
  } catch {
    // git コマンド失敗時は安全方向（許可）
    return null;
  }
}

async function main() {
  try {
    const data = await readStdin();
    const toolInput = data.tool_input || {};
    const command = toolInput.command || '';
    const cwd = data.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();

    // git merge コマンドでなければ無条件通過
    if (!isGitMerge(command)) {
      return output({});
    }

    // staged changes 確認
    const staged = getStagedChanges(cwd);

    if (staged) {
      const fileCount = staged.split('\n').length;
      const fileList = staged.split('\n').slice(0, 5).join(', ');
      const suffix = fileCount > 5 ? ` 他 ${fileCount - 5} 件` : '';

      return output({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: [
            `⛔ MERGE BLOCKED: staged changes ${fileCount} 件検出 (${fileList}${suffix})`,
            '',
            'git merge は staging area を破壊します。',
            'まず git commit で変更内容をコミットしてください。',
            '',
            'コミット失敗時: 原因を解決してから再度コミットしてください。',
            'merge を先に実行すると staged 変更が消失します。',
          ].join('\n'),
        },
      });
    }

    // staged changes なし → merge 許可
    return output({});
  } catch (err) {
    // Hook エラー時は許可方向（デッドロック防止）
    return output({});
  }
}

main();
