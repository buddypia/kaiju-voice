#!/usr/bin/env node

/**
 * compact-context-preserver.mjs - PreCompact Hook
 *
 * Context 圧縮(compaction) 前に核心コンテキストを自動保存します.
 *
 * oh-my-opencodeのPreemptive Compaction パターン:
 * - 原本: context 78% 到達時に先制的圧縮 + 核心データ保存
 * - 適用: Claude CodeのPreCompact Hookで圧縮前コンテキスト注入
 *
 * 保存項目 (7個):
 * 1. 現在のブランチと最近のコミット
 * 2. アクティブモード 状態 (persistent/web-qa/turbo)
 * 3. 最近 変更 ファイル リスト
 * 4. 未完了 タスク 要約
 * 5. 最近 エラー 履歴
 * 6. plan ファイル 進行 状態
 * 7. 現在 作業 ディレクトリ コンテキスト
 */

import { existsSync, readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import { homedir } from 'os';

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

function safeExec(cmd, cwd) {
  try {
    return execSync(cmd, { cwd, timeout: 5000, encoding: 'utf-8' }).trim();
  } catch {
    return null;
  }
}

function readJsonFile(path) {
  try {
    if (!existsSync(path)) return null;
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return null;
  }
}

async function main() {
  try {
    const input = await readStdin();
    const data = JSON.parse(input);

    const directory = data.directory || process.cwd();
    const sessionId = data.session_id || data.sessionId || '';
    const sections = [];

    // 1. Git 状態 (ブランチ + 最近 コミット)
    const branch = safeExec('git branch --show-current', directory);
    if (branch) {
      const recentCommits = safeExec('git log --oneline -5 2>/dev/null', directory);
      let gitSection = `## Git 状態\n- ブランチ: ${branch}`;
      if (recentCommits) {
        gitSection += `\n- 最近 コミット:\n${recentCommits
          .split('\n')
          .map((c) => `  - ${c}`)
          .join('\n')}`;
      }
      sections.push(gitSection);
    }

    // 2. 最近 変更 ファイル
    const changedFiles = safeExec('git diff --name-only HEAD 2>/dev/null', directory);
    const stagedFiles = safeExec('git diff --name-only --staged 2>/dev/null', directory);
    const allChanged = new Set();
    if (changedFiles)
      changedFiles
        .split('\n')
        .filter((f) => f)
        .forEach((f) => allChanged.add(f));
    if (stagedFiles)
      stagedFiles
        .split('\n')
        .filter((f) => f)
        .forEach((f) => allChanged.add(f));

    if (allChanged.size > 0) {
      const files = [...allChanged].slice(0, 20);
      sections.push(
        `## 変更 ファイル (${allChanged.size}個)\n${files.map((f) => `- ${f}`).join('\n')}${
          allChanged.size > 20 ? `\n- ... (${allChanged.size - 20}個 追加)` : ''
        }`,
      );
    }

    // 3. アクティブモード
    const stateDir = join(directory, '.claude', 'state');
    const modes = [];

    for (const [file, label] of [
      ['persistent-state.json', 'persistent'],
      ['web-qa-state.json', 'qa'],
      ['turbo-state.json', 'turbo'],
    ]) {
      const state = readJsonFile(join(stateDir, file));
      if (state?.active) {
        const iter = state.iteration || state.cycle || state.reinforcement_count || 0;
        const max = state.max_iterations || state.max_cycles || state.max_reinforcements || '?';
        modes.push(`- **${label}**: アクティブ (${iter}/${max})`);
        if (state.prompt) modes.push(`  - 作業: ${state.prompt}`);
      }
    }

    if (modes.length > 0) {
      sections.push(`## アクティブモード\n${modes.join('\n')}`);
    }

    // 4. 未完了 タスク
    if (sessionId) {
      const taskDir = join(homedir(), '.claude', 'tasks', sessionId);
      if (existsSync(taskDir)) {
        const tasks = [];
        try {
          const files = readdirSync(taskDir).filter((f) => f.endsWith('.json'));
          for (const file of files) {
            const task = readJsonFile(join(taskDir, file));
            if (task && (task.status === 'pending' || task.status === 'in_progress')) {
              const icon = task.status === 'in_progress' ? '[進行中]' : '[待機]';
              tasks.push(`- ${icon} ${task.subject}`);
            }
          }
        } catch {
          /* skip */
        }

        if (tasks.length > 0) {
          sections.push(`## 未完了 タスク (${tasks.length}個)\n${tasks.join('\n')}`);
        }
      }
    }

    // 5. エラー 履歴
    for (const file of ['persistent-state.json', 'web-qa-state.json']) {
      const state = readJsonFile(join(stateDir, file));
      if (state?.error_history?.length > 0) {
        const modeName = file.replace('-state.json', '');
        const recent = state.error_history.slice(-3);
        sections.push(`## 最近 エラー (${modeName})\n${recent.map((e) => `- ${e}`).join('\n')}`);
      }
    }

    // 6. Plan ファイル 進行 状態
    const plansDir = join(directory, '.tmp', 'plans');
    if (existsSync(plansDir)) {
      try {
        const planFiles = readdirSync(plansDir).filter((f) => f.endsWith('.md'));
        for (const pf of planFiles.slice(0, 3)) {
          const content = readFileSync(join(plansDir, pf), 'utf-8');
          const checked = (content.match(/- \[[xX]\]/g) || []).length;
          const total = (content.match(/- \[[ xX]\]/g) || []).length;
          if (total > 0) {
            sections.push(
              `## Plan: ${pf}\n- 進捗率: ${checked}/${total} (${Math.round((checked / total) * 100)}%)`,
            );
          }
        }
      } catch {
        /* skip */
      }
    }

    // Context 出力
    if (sections.length > 0) {
      const context = [
        '# Compaction Context (自動 保存)',
        '',
        '> PreCompact Hookにより自動保存された核心コンテキストです。',
        '',
        ...sections,
      ].join('\n');

      console.log(
        JSON.stringify({
          hookSpecificOutput: {
            additionalContext: context,
          },
        }),
      );
    }
  } catch (error) {
    // Hook 失敗しても圧縮は正常進行 (non-blocking)
    console.error(`[compact-context-preserver] ${error.message}`);
  }
}

main();
