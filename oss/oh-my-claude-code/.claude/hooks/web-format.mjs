#!/usr/bin/env node

/**
 * web-format.mjs (legacy filename: dart-format.mjs)
 *
 * PostToolUse(Write/Edit) 後に変更ファイル1つのみフォーマットする.
 * Web ファイルは Prettierを優先使用し、未インストール環境では安全にスキップする.
 *
 * 動作:
 * 1. stdinでPostToolUseイベントJSON受信
 * 2. tool_input.file_path 抽出
 * 3. Web フォーマット対象拡張子なら prettier --write 実行
 * 4. prettier 未インストール/失敗は non-criticalで無視
 */

import { execSync } from 'child_process';
import { existsSync } from 'fs';

const FORMATTABLE_EXTENSIONS = new Set([
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.mjs',
  '.cjs',
  '.json',
  '.css',
  '.scss',
  '.sass',
  '.less',
  '.html',
  '.md',
  '.mdx',
  '.yaml',
  '.yml',
]);

function getExtension(filePath) {
  const normalized = String(filePath || '').replace(/\\/g, '/');
  const dot = normalized.lastIndexOf('.');
  if (dot === -1) return '';
  return normalized.slice(dot).toLowerCase();
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

function runPrettier(filePath) {
  execSync(`npx --no-install prettier --write "${filePath}"`, {
    timeout: 10000,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
}

async function main() {
  try {
    const input = await readStdin();
    const data = JSON.parse(input);

    const filePath = data.tool_input?.file_path;
    if (!filePath) return;
    if (!existsSync(filePath)) return;

    const ext = getExtension(filePath);
    if (!FORMATTABLE_EXTENSIONS.has(ext)) return;

    // バンドル/マップ生成物はフォーマットしない
    if (/\.min\.(js|css)$/i.test(filePath) || /\.map$/i.test(filePath)) return;

    try {
      runPrettier(filePath);
    } catch (err) {
      const msg = String(err?.message || '');
      if (/prettier/i.test(msg) || /command not found/i.test(msg) || /ENOENT/i.test(msg)) {
        return;
      }
      throw err;
    }
  } catch (error) {
    // フォーマット失敗は non-critical - 無視して続行
    console.error(`[web-format] ${error.message}`);
  }
}

main();
