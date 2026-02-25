/**
 * State Management Module
 *
 * ralph-loop/storage.tsを Claude Code Hooksに合わせて再設計.
 * ファイル 基盤 状態 管理 (PluginのインメモリMapの代わり).
 *
 * 設計原則:
 * - 各モードは独立したJSON stateファイル
 * - 読み取り/書き込み/削除は全て原子的 (単一ファイル操作)
 * - Staleness チェックでゾンビ状態防止
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync, unlinkSync, renameSync } from 'fs';
import { join } from 'path';
import { randomBytes } from 'crypto';

/** Stale 判定基準: 24時間 (BUG-8 fix: 夜間/長期作業サポートのため 2時間→24時間) */
const DEFAULT_STALE_MS = 24 * 60 * 60 * 1000;

/** サポートされるモード一覧 (SSOT: 全スクリプトでこの定数を参照) */
export const SUPPORTED_MODES = ['persistent', 'web-qa', 'turbo'];

/**
 * State ファイル 読み取り
 * @param {string} stateDir - .claude/state ディレクトリ パス
 * @param {string} mode - モード名 (persistent, web-qa, turbo)
 * @returns {object|null}
 */
export function readState(stateDir, mode) {
  const path = join(stateDir, `${mode}-state.json`);
  try {
    if (!existsSync(path)) return null;
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return null;
  }
}

/**
 * State ファイル 書き込み (v2.1: アトミック書き込み - BUG-3 修正)
 *
 * 一時ファイルにまず書き込んだ後 renameSync()で置換.
 * POSIXでrenameはアトミックなのでrace condition 防止.
 *
 * @param {string} stateDir
 * @param {string} mode
 * @param {object} state
 * @returns {boolean}
 */
export function writeState(stateDir, mode, state) {
  const path = join(stateDir, `${mode}-state.json`);
  const tmpPath = `${path}.${randomBytes(4).toString('hex')}.tmp`;
  try {
    if (!existsSync(stateDir)) mkdirSync(stateDir, { recursive: true });
    writeFileSync(tmpPath, JSON.stringify(state, null, 2));
    renameSync(tmpPath, path);
    return true;
  } catch {
    // 一時ファイル 整理 試行
    try {
      if (existsSync(tmpPath)) unlinkSync(tmpPath);
    } catch {
      /* ignore */
    }
    return false;
  }
}

/**
 * State ファイル 削除 (= モード 非アクティブ化)
 * 原本の clearState() 対応
 */
export function clearState(stateDir, mode) {
  const path = join(stateDir, `${mode}-state.json`);
  try {
    if (existsSync(path)) unlinkSync(path);
    return true;
  } catch {
    return false;
  }
}

/**
 * Stateが古くなっているかチェック (ゾンビ状態防止)
 *
 * 原本 ralph-loopではインメモリ timestampで管理するが,
 * Claude Code Hooksは毎回実行がfresh processなので
 * state ファイルのtimestampで判断.
 */
export function isStale(state, thresholdMs = DEFAULT_STALE_MS) {
  if (!state) return true;

  const lastChecked = state.last_checked_at ? new Date(state.last_checked_at).getTime() : 0;
  const startedAt = state.started_at ? new Date(state.started_at).getTime() : 0;
  const recent = Math.max(lastChecked, startedAt);

  return recent === 0 || Date.now() - recent > thresholdMs;
}

/**
 * アクティブモード 探索
 * 優先順位: persistent > web-qa > turbo
 * (原本で ralph-loopがultraworkより優先するのと同一の概念)
 *
 * @returns {{ mode: string, state: object } | null}
 */
export function getActiveMode(stateDir) {
  for (const mode of SUPPORTED_MODES) {
    const state = readState(stateDir, mode);
    if (state?.active && !isStale(state)) {
      return { mode, state };
    }
  }
  return null;
}

/**
 * セッションスコープ アクティブモード 探索 (v2.3: BUG-9 クロスセッション干渉修正)
 *
 * session_idが一致するモードのみ返却.
 * stateにsession_idがなければ (レガシー) すべてのセッションにマッチング (下位互換).
 *
 * @param {string} stateDir
 * @param {string} sessionId - 現在 セッション ID
 * @returns {{ mode: string, state: object } | null}
 */
export function getActiveModeForSession(stateDir, sessionId) {
  for (const mode of SUPPORTED_MODES) {
    const state = readState(stateDir, mode);
    if (state?.active && !isStale(state) && isSessionOwned(state, sessionId)) {
      return { mode, state };
    }
  }
  return null;
}

/**
 * 特定モード stateが現在セッションに属するか確認 (BUG-9 修正)
 *
 * - stateにsession_id なし (レガシー): すべてのセッションマッチング (下位互換)
 * - sessionIdが不明 (空文字列): すべてのセッションマッチング (安全フォールバック)
 * - 両方あり: 一致 判定 比較
 *
 * @param {object} state - モード state オブジェクト
 * @param {string} sessionId - 現在 セッション ID
 * @returns {boolean}
 */
export function isSessionOwned(state, sessionId) {
  if (!state?.session_id) return true;
  if (!sessionId) return true;
  return state.session_id === sessionId;
}

/**
 * 同一エラー 繰り返し チェック (v2.2: 部分 マッチング 追加 - BUG-2 修正)
 * 原本 todo-continuation-enforcerのabort detectionと類似した目的.
 *
 * 2段階検査:
 * 1. 完全一致: すべての最近エラーが同一文字列
 * 2. 核心失敗パターン繰り返し: エラー文字列で失敗コンポーネントを抽出して
 *    同一コンポーネントがすべての最近エラーに存在すると構造的問題と判断
 *    例: ["analyze:false,test:true", "analyze:false,test:false"] → analyze 繰り返し失敗
 */
export function hasSameErrorRepeated(state, maxRepeats = 3) {
  const history = state?.error_history;
  if (!Array.isArray(history) || history.length < maxRepeats) return false;
  const recent = history.slice(-maxRepeats);

  // 1. 完全一致 (既存動作維持)
  if (recent.every((err) => err === recent[0])) return true;

  // 2. 核心失敗パターン繰り返し検査
  // "analyze: false", "test: FAIL" 等の失敗 コンポーネント 抽出
  const failurePattern = /(\w+)\s*:\s*(false|FAIL|fail|error|null)/g;
  const firstFailures = [];
  let match;
  while ((match = failurePattern.exec(recent[0])) !== null) {
    firstFailures.push(match[1].toLowerCase());
  }

  // 同一核心失敗がすべての最近エラーに存在すると構造的問題
  if (firstFailures.length > 0) {
    return firstFailures.some((key) => {
      const pattern = new RegExp(`${key}\\s*:\\s*(false|FAIL|fail|error|null)`, 'i');
      return recent.every((err) => pattern.test(err));
    });
  }

  return false;
}

/**
 * State ディレクトリ 確保
 */
export function ensureStateDir(stateDir) {
  if (!existsSync(stateDir)) mkdirSync(stateDir, { recursive: true });
}
