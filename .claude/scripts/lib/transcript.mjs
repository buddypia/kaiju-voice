/**
 * Transcript Parsing Module
 *
 * Claude Code Hooksのtranscript_pathを読んで:
 * 1) 完了マーカー(<promise>...</promise>) 検出
 * 2) QA 完了 状態(静的分析 + テスト) 検出
 * 3) コード変更後の静的分析 結果 検出
 *
 * 既存 Flutter 専用実装から, Web/Node プロジェクトでも動作するように
 * ファイル拡張子と出力パターンを拡張した.
 * (レガシー互換のために Dart パターンも一緒にサポート)
 */

import { existsSync, readFileSync, statSync, openSync, readSync, closeSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

/** 大容量 transcript 対応: 最大 1MBのみ 読み取り */
const MAX_READ_BYTES = 1 * 1024 * 1024;

/** 追跡 対象 ソース 拡張子 (Web + レガシー Dart) */
const TRACKED_SOURCE_EXTENSIONS = new Set([
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.mjs',
  '.cjs',
  '.css',
  '.scss',
  '.sass',
  '.less',
  '.html',
  '.vue',
  '.svelte',
  '.astro',
  '.json',
  '.dart', // backward compatibility
]);

/** 追跡 除外 パス */
const IGNORED_PATH_SEGMENTS = [
  '/node_modules/',
  '/dist/',
  '/build/',
  '/coverage/',
  '/.next/',
  '/.nuxt/',
  '/.svelte-kit/',
  '/out/',
  '/.turbo/',
];

/** 生成 成果物 ファイル名 パターン */
const GENERATED_FILE_PATTERNS = [
  /\.min\.(js|css)$/i,
  /\.bundle\.(js|css)$/i,
  /\.map$/i,
  /\.freezed\.dart$/i,
  /\.g\.dart$/i,
];

const ANALYZE_PASS_PATTERNS = [
  /\bno issues found\b/i,
  /\b0 issues? found\b/i,
  /\bno lint(?:ing)? (?:warnings? or )?errors?\b/i,
  /\blint(?:ing)? passed\b/i,
  /\b0 problems?\b/i,
  /eslint.*no warnings? or errors?/i,
  /\bfound 0 errors?\b/i,
  /\btype[\s-]?check(?:ing)? (?:passed|succeeded)\b/i,
];

const ANALYZE_FAIL_PATTERNS = [
  /\b[1-9]\d*\s+issues?\s+found\b/i,
  /\b[1-9]\d*\s+problems?\b/i,
  /\b✖\s*[1-9]\d*\s+problems?\b/i,
  /\beslint\b.*\b(error|failed)\b/i,
  /\blint(?:ing)? failed\b/i,
  /\btype[\s-]?check(?:ing)? failed\b/i,
  /\bfound [1-9]\d*\s+errors?\b/i,
];

const TEST_PASS_PATTERNS = [
  /\ball tests? passed\b/i,
  /\ball \d+ tests? passed\b/i,
  /\btest suites?:\s*\d+\s+passed,\s*0\s+failed\b/i,
  /\btests?:\s*\d+\s+passed,\s*0\s+failed\b/i,
  /\btest files?\s+\d+\s+passed\b/i,
];

const TEST_FAIL_PATTERNS = [
  /\bsome tests? failed\b/i,
  /\b[1-9]\d*\s+tests?\s+failed\b/i,
  /\btest suites?:\s*[1-9]\d*\s+failed\b/i,
  /\btests?:\s*[1-9]\d*\s+failed\b/i,
  /^\s*FAIL\b/i,
  /\bfailing\b/i,
];

/**
 * ~ パス 展開
 */
function resolvePath(path) {
  if (!path) return null;
  if (path.startsWith('~')) return join(homedir(), path.substring(1));
  return path;
}

/**
 * Transcript 内容 読み取り (大容量 ファイル 対応)
 */
function readTranscriptContent(resolvedPath) {
  const stat = statSync(resolvedPath);

  if (stat.size <= MAX_READ_BYTES) {
    return readFileSync(resolvedPath, 'utf-8');
  }

  const fd = openSync(resolvedPath, 'r');
  try {
    const buffer = Buffer.alloc(MAX_READ_BYTES);
    readSync(fd, buffer, 0, MAX_READ_BYTES, stat.size - MAX_READ_BYTES);

    let content = buffer.toString('utf-8');
    const firstNewline = content.indexOf('\n');
    if (firstNewline > 0) content = content.substring(firstNewline + 1);
    return content;
  } finally {
    closeSync(fd);
  }
}

function isIgnoredPath(fp) {
  const normalized = fp.replace(/\\/g, '/');
  return IGNORED_PATH_SEGMENTS.some((seg) => normalized.includes(seg));
}

function isGeneratedFile(fp) {
  return GENERATED_FILE_PATTERNS.some((pattern) => pattern.test(fp));
}

/**
 * Web/Node 中心の追跡 対象 ファイル 判定.
 * (レガシー Dartもサポート)
 */
function isTrackedSourceFile(fp) {
  if (!fp || typeof fp !== 'string') return false;
  if (isIgnoredPath(fp)) return false;
  if (isGeneratedFile(fp)) return false;

  const normalized = fp.replace(/\\/g, '/');
  const dotIndex = normalized.lastIndexOf('.');
  if (dotIndex === -1) return false;
  const ext = normalized.slice(dotIndex).toLowerCase();
  return TRACKED_SOURCE_EXTENSIONS.has(ext);
}

/**
 * Transcriptで最後のソース変更(Write/Edit)位置を検索する.
 *
 * Claude Code transcript 実際の形式:
 * - assistant.message.content[].{type:'tool_use', name:'Edit|Write', input.file_path}
 * レガシー/テスト形式:
 * - top-level tool_name/name + input.file_path
 */
function findLastCodeChangeIndex(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const entry = JSON.parse(lines[i]);

      if (entry.type === 'assistant') {
        const content = entry.message?.content;
        if (Array.isArray(content)) {
          for (const block of content) {
            if (block?.type === 'tool_use' && (block.name === 'Write' || block.name === 'Edit')) {
              const fp = block.input?.file_path || '';
              if (isTrackedSourceFile(fp)) return i;
            }
          }
        }
      }

      const toolName = entry.tool_name || entry.name || '';
      const filePath = entry.input?.file_path || entry.tool_input?.file_path || '';
      if ((toolName === 'Write' || toolName === 'Edit') && isTrackedSourceFile(filePath)) {
        return i;
      }
    } catch {
      continue;
    }
  }
  return -1;
}

function hasPattern(line, patterns) {
  return patterns.some((pattern) => pattern.test(line));
}

function parseAnalyzeResult(line) {
  if (hasPattern(line, ANALYZE_FAIL_PATTERNS)) return false;
  if (hasPattern(line, ANALYZE_PASS_PATTERNS)) return true;
  return null;
}

function parseTestResult(line) {
  if (hasPattern(line, TEST_FAIL_PATTERNS)) return false;

  if (hasPattern(line, TEST_PASS_PATTERNS)) return true;

  if (/0\s+failed/i.test(line) && /(test|suite|spec|jest|vitest)/i.test(line)) {
    return true;
  }

  return null;
}

/**
 * Completion Marker 検索.
 * user タイプ エントリはスキップ (完了マーカーは assistantのみ 出力).
 */
export function detectCompletionMarker(transcriptPath, marker) {
  const path = resolvePath(transcriptPath);
  if (!path || !existsSync(path)) return false;

  try {
    const content = readTranscriptContent(path);
    const escaped = marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`<promise>\\s*${escaped}\\s*</promise>`, 'is');

    const lines = content.split('\n').filter((l) => l.trim());
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        if (entry.type === 'user') continue;
        if (pattern.test(line)) return true;
      } catch {
        continue;
      }
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * QA 完了 検出 (静的分析 + テスト).
 *
 * 2-pass 方式:
 * 1) 最後 コード 変更 位置 検出
 * 2) その以後のanalyze/test 結果のみ 有効 処理
 */
export function detectQaCompletion(transcriptPath) {
  const NOT_FOUND = {
    complete: false,
    analyzeResult: null,
    testResult: null,
    reason: 'Transcript not available',
  };

  const path = resolvePath(transcriptPath);
  if (!path || !existsSync(path)) return NOT_FOUND;

  try {
    const content = readTranscriptContent(path);
    const lines = content.split('\n').filter((l) => l.trim());

    const lastCodeChangeIdx = findLastCodeChangeIndex(lines);
    const searchFrom = Math.max(lastCodeChangeIdx, 0);

    let analyzeResult = null;
    let testResult = null;

    for (let i = lines.length - 1; i >= searchFrom; i--) {
      const line = lines[i];

      if (analyzeResult === null) {
        const parsed = parseAnalyzeResult(line);
        if (parsed !== null) analyzeResult = parsed;
      }

      if (testResult === null) {
        const parsed = parseTestResult(line);
        if (parsed !== null) testResult = parsed;
      }

      if (analyzeResult !== null && testResult !== null) break;
    }

    const complete = analyzeResult === true && testResult === true;
    return {
      complete,
      analyzeResult,
      testResult,
      reason: complete
        ? 'All checks passed'
        : `analyze: ${analyzeResult ?? 'not run'}, test: ${testResult ?? 'not run'}`,
    };
  } catch {
    return NOT_FOUND;
  }
}

/**
 * レガシー互換用 alias.
 */
export function detectFlutterQaCompletion(transcriptPath) {
  return detectQaCompletion(transcriptPath);
}

/**
 * コード変更後 analyze 状態 検出 (analyze-guard用).
 */
export function detectAnalyzeStatus(transcriptPath) {
  const path = resolvePath(transcriptPath);
  if (!path || !existsSync(path)) {
    return {
      hasCodeChange: false,
      hasDartCodeChange: false, // backward compatibility
      analyzeResult: null,
    };
  }

  try {
    const content = readTranscriptContent(path);
    const lines = content.split('\n').filter((l) => l.trim());

    const lastCodeChangeIdx = findLastCodeChangeIndex(lines);
    if (lastCodeChangeIdx === -1) {
      return {
        hasCodeChange: false,
        hasDartCodeChange: false,
        analyzeResult: null,
      };
    }

    let analyzeResult = null;
    for (let i = lines.length - 1; i >= lastCodeChangeIdx; i--) {
      const parsed = parseAnalyzeResult(lines[i]);
      if (parsed !== null) {
        analyzeResult = parsed;
        break;
      }
    }

    // hasDartCodeChange: 後方互換フィールド (Webプロジェクトでは常にfalse)
    return {
      hasCodeChange: true,
      hasDartCodeChange: false,
      analyzeResult,
    };
  } catch {
    return {
      hasCodeChange: false,
      hasDartCodeChange: false,
      analyzeResult: null,
    };
  }
}

/**
 * Transcript 最後 N行 読み取り (デバッグ/分析用)
 */
export function readTranscriptTail(transcriptPath, maxLines = 20) {
  const path = resolvePath(transcriptPath);
  if (!path || !existsSync(path)) return [];

  try {
    const content = readTranscriptContent(path);
    const lines = content.split('\n').filter((l) => l.trim());
    const entries = [];

    for (let i = Math.max(0, lines.length - maxLines); i < lines.length; i++) {
      try {
        entries.push(JSON.parse(lines[i]));
      } catch {
        continue;
      }
    }

    return entries;
  } catch {
    return [];
  }
}
