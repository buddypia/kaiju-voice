#!/usr/bin/env node

/**
 * oh-my-claude-code Keyword Detector Hook (UserPromptSubmit) v2.1
 *
 * oh-my-opencodeのkeyword-detector.mjsをClaude Code Hooks に移植.
 * Claude Code Hooks APIのUserPromptSubmitイベントで実行.
 *
 * v2.1 変更 (BUG-1 修正):
 * - 前処理強化: removeCodeBlocks() → cleanPromptForMatching()
 * - 2層パターン: intentPatterns (動詞形) + mentionPatterns (名詞形)
 * - 否定文脈分析: negativeContext + GLOBAL_NEGATIVE_CONTEXT
 * - JS \b 韓国語 限界対応: 韓国語パターンで \b 除去
 *
 * メカニズム (原本と同一):
 * 1. stdin JSON → プロンプト抽出 (多様なJSON構造対応)
 * 2. 前処理後キーワード regex マッチング (韓国語/英語)
 * 3. 競合解決 (優先順位基盤, 原本の resolveConflicts 移植)
 * 4. State ファイル生成 (lib/state.mjs 共有ライブラリ使用)
 * 5. hookSpecificOutput.additionalContextでSkill 呼び出し注入
 *
 * サポートキーワード (優先順位順):
 * 0. cancel/キャンセル: すべてのアクティブモード終了 (排他的)
 * 1. persistent/完了まで: 完了まで止まらない
 * 2. turbo/ターボ: 並列実行モード + autopilot
 * 3. research-pilot/リサーチ: Product Discovery (feature-pilot 前段)
 * 4. feature-pilot/新機能: 機能開発オーケストレーター
 * 5. web-qa/QA: lint/test 繰り返し検証サイクル
 * 6. security/セキュリティ: セキュリティ検査
 * 7. bug-fix/バグ: バグ修正
 * 8. deep-explain/説明: 深層分析
 * 9. analyze-pipeline/何作るか: パイプライン分析
 * 10. competitive-tracker/競合他社比較: ベンチマーク追跡
 * 11. manual-generator/マニュアル: マニュアル更新/生成
 *
 * @see oss-sources/oh-my-claudecode/scripts/keyword-detector.mjs (原本)
 */

import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { writeState, clearState, readState, ensureStateDir, isSessionOwned } from './lib/state.mjs';
import { readStdin, output } from './lib/utils.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ═══════════════════════════════════════════════════════════════════
// 前処理: cleanPromptForMatching() (v2.1 新規)
//
// 既存 removeCodeBlocks() 拡張. 説明/引用/技術用語文脈を除去して
// false positiveを事前ブロック.
// ═══════════════════════════════════════════════════════════════════

/**
 * プロンプトでキーワードマッチング前にノイズを除去.
 *
 * 除去 対象:
 * 1. フェンスドコードブロック (```...```)
 * 2. インラインコード (`...`)
 * 3. マークダウンテーブル行 (| col | col |)
 * 4. マークダウン引用文 (> ...)
 * 5. 括弧内容: (キャンセル機能), 「中断処理」, [cancel] 等
 * 6. ボールド/イタリック内部: **キャンセル**, *中断*
 * 7. ファイルパス/技術用語: cancel-skill.md, persistent-mode.mjs 等
 * 8. JSON/設定リテラル: "cancel", 'persistent-mode'
 */
function cleanPromptForMatching(text) {
  return (
    text
      // 1. フェンスドコードブロック (```...```)
      .replace(/```[\s\S]*?```/g, '')
      // 2. インラインコード (`...`)
      .replace(/`[^`]+`/g, '')
      // 3. マークダウンテーブル行
      .replace(/^\|.*\|$/gm, '')
      // 4. マークダウン引用文
      .replace(/^>\s+.*/gm, '')
      // 5. 括弧内容 (韓国語括弧含む)
      .replace(/\([^)]*\)/g, '')
      .replace(/「[^」]*」/g, '')
      .replace(/\[[^\]]*\]/g, '')
      // 6. ボールド/イタリック内部 (** または * で囲まれたテキスト)
      .replace(/\*\*[^*]+\*\*/g, '')
      .replace(/\*[^*]+\*/g, '')
      // 7. ファイルパスパターン (拡張子含む)
      .replace(/[\w\-./]+\.\w{2,4}\b/g, '')
      // 8. JSON/設定リテラル (引用符で囲まれた値)
      .replace(/"[^"]*"/g, '')
      .replace(/'[^']*'/g, '')
  );
}

// ═══════════════════════════════════════════════════════════════════
// グローバル否定文脈 (v2.1 新規)
//
// 全キーワードに共通適用. 説明/質問/参照文脈を検出.
// ═══════════════════════════════════════════════════════════════════

const GLOBAL_NEGATIVE_CONTEXT = [
  // 説明/参照文脈
  /について/,
  /に関して/,
  /に関する/,
  // 引用/定義文脈
  /という/,
  /といった/,
  /とは\s/,
  // 質問文脈
  /なのか/,
  /ですか/,
  /でしょうか/,
  // 可能性/義務文脈
  /できる/,
  /すべき/,
  // 状況/シナリオ説明文脈
  /場合/,
  /状況/,
  /シナリオ/,
];

// ═══════════════════════════════════════════════════════════════════
// キーワード定義 (優先順位順序 = 配列順序) - v2.1 2層構造
//
// intentPatterns: 動詞形/命令形 → 即時有効化 (高確信度)
// mentionPatterns: 名詞形 → negativeContext チェック後に決定
// negativeContext: キーワード別否定文脈 (説明/引用なら拒否)
// ═══════════════════════════════════════════════════════════════════

const KEYWORD_DEFINITIONS = [
  // ── Priority 0: Cancel (最優先、排他的) ──
  {
    name: 'cancel',
    skill: 'cancel',
    intentPatterns: [
      /キャンセルして/,
      /キャンセル\s*して\s*(ください|くれ)/,
      /中断して/,
      /中断\s*して\s*(ください|くれ)/,
      /\/cancel/i,
      /中止/,
      /止めて/,
      /\b(cancel|cancelomc|stopomc)\b/i,
    ],
    mentionPatterns: [/キャンセル/, /中断/],
    negativeContext: [
      /キャンセル[はがのをにも]/,
      /中断[はがのをにも]/,
      /キャンセル\s*(機能|処理|ロジック|ボタン|動作|パターン|方法|過程|手順|有無)/,
      /中断\s*(機能|処理|ロジック|ボタン|動作|パターン|方法|過程|手順|有無)/,
    ],
    exclusive: true,
    createsState: false,
  },

  // ── Priority 1: Persistent Mode ──
  {
    name: 'persistent',
    skill: 'persistent-mode',
    intentPatterns: [
      /完了まで\s*(して|完成|進行|作業|実装|開発|修正|直して|作って|処理|実行|繰り返し|完了)/,
      /完了まで\s*(して|進行|繰り返し|実行|継続|実装|開発)/,
      /止まらないで/,
      /中断しないで/,
      /諦めないで/,
      /\b(don'?t\s+stop|must\s+complete|until\s+done)\b/i,
    ],
    mentionPatterns: [
      // BUG-1 fix: bare "完了まで" → 作業動詞文脈必須 (誤発動防止)
      /完了まで.{0,15}(して|し|完成|実装|進行|作業|修正|繰り返し|直し|作り|開発|処理|実行|継続|完了)/,
      /完了まで.{0,15}(して|し|進行|繰り返し|実行|継続|完成|実装|開発)/,
      /\b(persistent|ralph)\b/i,
    ],
    negativeContext: [/完了までの/, /完了までは/],
    createsState: true,
    stateFile: 'persistent',
    defaultState: {
      active: true,
      iteration: 0,
      max_iterations: 20,
      error_history: [],
    },
  },

  // ── Priority 2: Turbo Mode ──
  {
    name: 'turbo',
    skill: 'turbo-mode',
    intentPatterns: [
      /ターボ\s*(モード|で)/,
      /ターボで\s*して/,
      /\b(turbo)\b/i,
      /\b(autopilot|auto[\s-]?pilot)\b/i,
      /\b(ultrawork|ulw)\b/i,
      /並列で\s*実行/,
      /同時に\s*実行/,
      /\bbuild\s+me\s+/i,
      /\bcreate\s+me\s+/i,
      /\bmake\s+me\s+/i,
      /\bhandle\s+it\s+all\b/i,
    ],
    mentionPatterns: [/ターボ/],
    negativeContext: [/ターボ[はがのを]/, /ターボ\s*(モード|機能|設定)[はがのをに]/],
    createsState: true,
    stateFile: 'turbo',
    defaultState: {
      active: true,
      reinforcement_count: 0,
      max_reinforcements: 30,
    },
  },

  // ── Priority 3: Research Pilot (feature-pilot 前段) ──
  {
    name: 'research-pilot',
    skill: 'research-pilot',
    intentPatterns: [
      /リサーチ\s*(して|してください|しよう|開始)/,
      /妥当性\s*(検証|確認|分析)\s*(して|してください)/,
      /調査\s*(して|してください|しよう|開始)/,
      /ゼロベース(で|から)\s*(リサーチ|調査|分析|検討|開始)/,
      /フルスクラッチ(で|から)\s*(リサーチ|調査|分析|検討|開始)/,
      /最初から\s*(リサーチ|調査|分析|検討|設計)/,
      /\b(research[\s-]?pilot)\b/i,
      /\b(product\s+discovery)\b/i,
      /\b(feasibility)\s+(check|study|analysis)\b/i,
    ],
    mentionPatterns: [
      /リサーチ/,
      /妥当性/,
      /ゼロベース/,
      /フルスクラッチ/,
      /最初から/,
      /\b(feasibility|discovery)\b/i,
    ],
    negativeContext: [
      /リサーチ[はがのをにも]/,
      /妥当性[はがのをにも]/,
      /リサーチ\s*(結果|文書|記録|キャッシュ|ファイル)[はがのをに]/,
      /妥当性\s*(検証|確認|分析)[はがのをに]/,
    ],
    createsState: false,
  },

  // ── Priority 4: Feature Pilot ──
  {
    name: 'feature-pilot',
    skill: 'feature-pilot',
    intentPatterns: [
      /新\s*機能\s*(追加|開発|作って|実装)/,
      /機能\s*(追加|開発)\s*(して|してください)/,
      /実装して\s*(ください|くれ)/,
      /開発して\s*(ください|くれ)/,
      /\b(feature[\s-]?pilot)\b/i,
    ],
    mentionPatterns: [/新\s*機能/, /機能\s*追加/, /機能\s*開発/],
    negativeContext: [/機能[はがのをにも]/, /機能\s*(リスト|一覧|現況|状態|文書)/],
    createsState: false,
  },

  // ── Priority 5: QA (Web QA cycle) ──
  {
    name: 'web-qa',
    intentPatterns: [
      /QA\s*(サイクル|回して|実行|開始)/,
      /品質\s*検査\s*(して|回して|開始)/,
      /テスト\s*回して/,
      /テスト\s*実行して/,
      /lint\s*(回して|実行して|してください)/i,
      /eslint\s*(回して|実行して|してください)/i,
      /\b(web[\s-]?qa)\b/i,
      /テスト\s*通過.{0,5}まで/,
    ],
    mentionPatterns: [/QA\s*サイクル/, /品質\s*検査/, /\b(web[\s-]?qa)\b/i],
    negativeContext: [/QA[はがのを]/, /QA\s*(モード|サイクル|機能)[はがのをに]/],
    createsState: true,
    stateFile: 'web-qa',
    defaultState: {
      active: true,
      cycle: 0,
      max_cycles: 10,
      all_passing: false,
      last_failure: null,
      error_history: [],
    },
  },

  // ── Priority 6: Security Scan ──
  {
    name: 'security',
    skill: 'security-scan',
    intentPatterns: [
      /セキュリティ\s*検査\s*(して|回して|開始)/,
      /セキュリティ\s*スキャン/,
      /RLS\s*確認\s*(して|してください)/,
      /シークレット\s*チェック/,
      /\b(security[\s-]?scan)\b/i,
    ],
    mentionPatterns: [/セキュリティ\s*検査/, /セキュリティ\s*スキャン/],
    negativeContext: [
      /セキュリティ[はがのをにも]/,
      /セキュリティ\s*(政策|ルール|設定|機能|検査)[はがのをに]/,
    ],
    createsState: false,
  },

  // ── Priority 7: Bug Fix ──
  {
    name: 'bug-fix',
    skill: 'bug-fix',
    intentPatterns: [
      /バグ\s*修正\s*(して|してください)/,
      /バグ\s*直して/,
      /エラー\s*修正\s*(して|してください)/,
      /\b(fix\s+bug|bug[\s-]?fix)\b/i,
      /動かない/,
      /動作\s*しない/,
      /クラッシュ/,
    ],
    mentionPatterns: [/バグ\s*修正/, /エラー\s*修正/],
    negativeContext: [
      /バグ[はがのをにも]/,
      /エラー[はがのをにも]/,
      /バグ\s*(修正|レポート|リスト|パターン|タイプ)[はがのをに]/,
    ],
    createsState: false,
  },

  // ── Priority 8: Deep Explain ──
  {
    name: 'deep-explain',
    skill: 'deep-explain',
    intentPatterns: [
      /\b(deep[\s-]?explain)\b/i,
      /深層\s*分析\s*(して|してください)/,
      /深層\s*説明\s*(して|してください)/,
    ],
    mentionPatterns: [/深層\s*分析/, /深層\s*説明/],
    negativeContext: [/分析[はがのをにも]/, /説明[はがのをにも]/],
    createsState: false,
  },

  // ── Priority 8: Analyze Pipeline ──
  {
    name: 'analyze-pipeline',
    skill: 'analyze-what-to-build',
    intentPatterns: [
      /何\s*作るか/,
      /何を\s*作る/,
      /次\s*機能\s*(何|なに|どんな|おすすめ|分析|教えて)/,
      /パイプライン\s*分析\s*(して|してください|回して)/,
      /ポートフォリオ\s*分析\s*(して|してください)/,
      /\b(what\s+to\s+build|analyze[\s-]?what[\s-]?to[\s-]?build)\b/i,
    ],
    mentionPatterns: [/何\s*作る/, /次\s*機能/, /パイプライン\s*分析/, /ポートフォリオ\s*分析/],
    negativeContext: [
      /パイプライン[はがのをにも]/,
      /ポートフォリオ[はがのをにも]/,
      /(パイプライン|ポートフォリオ)\s*分析[はがのをにも]/,
    ],
    createsState: false,
  },

  // ── Priority 9: Competitive Tracker ──
  {
    name: 'competitive-tracker',
    skill: 'competitive-tracker',
    intentPatterns: [
      /競合他社\s*比較\s*(して|してください|回して)/,
      /ベンチマーク\s*(回して|して|してください)/,
      /業界\s*標準\s*(チェック|確認|比較)\s*(して|してください)/,
      /ポートフォリオ\s*(チェック|確認)\s*(して|してください)/,
      /ギャップ\s*追跡\s*(して|してください)/,
      /ギャップ\s*分析\s*(して|してください)/,
      /\b(competitive[\s-]?track)/i,
    ],
    mentionPatterns: [
      /競合他社\s*比較/,
      /ベンチマーク/,
      /業界\s*標準/,
      /ポートフォリオ\s*チェック/,
      /ギャップ\s*追跡/,
    ],
    negativeContext: [
      /競合他社[はがのをにも]/,
      /ベンチマーク[はがのをにも]/,
      /業界\s*標準[はがのをにも]/,
    ],
    createsState: false,
  },

  // ── Priority 10: Manual Generator ──
  {
    name: 'manual-generator',
    skill: 'manual-generator',
    intentPatterns: [
      /マニュアル\s*更新\s*(して|してください)/,
      /マニュアル\s*更新\s*(して|してください)/,
      /マニュアル\s*生成\s*(して|してください)/,
      /\b(manual\s+update)\b/i,
    ],
    mentionPatterns: [/マニュアル\s*更新/, /マニュアル\s*更新/, /マニュアル\s*生成/],
    negativeContext: [/マニュアル[はがのをにも]/, /マニュアル\s*(更新|更新|生成)[はがのをにも]/],
    createsState: false,
  },
];

// 優先順位順序 (インデックス = 優先順位)
const PRIORITY_ORDER = KEYWORD_DEFINITIONS.map((k) => k.name);

// ═══════════════════════════════════════════════════════════════════
// プロンプト抽出 (原本 extractPrompt() 忠実移植)
// ═══════════════════════════════════════════════════════════════════

/**
 * 様々なJSON構造からプロンプト抽出.
 * Claude Code Hooks APIの入力形式が変更されても対応.
 *
 * @param {object} data - stdinでパースされたJSON
 * @returns {string}
 */
function extractPrompt(data) {
  if (typeof data === 'string') {
    try {
      data = JSON.parse(data);
    } catch {
      return data;
    }
  }
  if (data.prompt) return data.prompt;
  if (data.message?.content) return data.message.content;
  if (Array.isArray(data.parts)) {
    return data.parts
      .filter((p) => p.type === 'text')
      .map((p) => p.text)
      .join(' ');
  }
  return '';
}

// ═══════════════════════════════════════════════════════════════════
// 2層キーワードマッチング (v2.1 新規)
//
// Layer 1: intentPatterns → 即時有効化 (動詞/命令形)
// Layer 2: mentionPatterns → negativeContext チェック後に決定
// ═══════════════════════════════════════════════════════════════════

/**
 * キーワードマッチング結果を返却.
 *
 * @param {string} cleanPrompt - 前処理されたプロンプト
 * @param {string} originalPrompt - 原本プロンプト (否定文脈チェック用)
 * @returns {{ keyword: object, matchType: 'intent'|'mention' }[]}
 */
function matchKeywords(cleanPrompt, originalPrompt) {
  const matches = [];

  for (const keyword of KEYWORD_DEFINITIONS) {
    // Layer 1: intentPatterns (動詞/命令形) → 即時有効化
    const intentMatch = keyword.intentPatterns.some((p) => p.test(cleanPrompt));
    if (intentMatch) {
      matches.push({ keyword, matchType: 'intent' });
      continue;
    }

    // Layer 2: mentionPatterns (名詞形) → 否定文脈チェック
    const mentionMatch = keyword.mentionPatterns.some((p) => p.test(cleanPrompt));
    if (mentionMatch) {
      // キーワード別否定文脈チェック
      const negativeHit = keyword.negativeContext.some((p) => p.test(originalPrompt));
      if (negativeHit) continue; // 説明/引用文脈 → 拒否

      // グローバル否定文脈チェック
      const globalNegativeHit = GLOBAL_NEGATIVE_CONTEXT.some((p) => p.test(originalPrompt));
      if (globalNegativeHit) continue; // 説明/質問/参照文脈 → 拒否

      matches.push({ keyword, matchType: 'mention' });
    }
  }

  return matches;
}

// ═══════════════════════════════════════════════════════════════════
// 競合解決 (原本 resolveConflicts() 忠実移植, v2.1 拡張)
// ═══════════════════════════════════════════════════════════════════

/**
 * マッチングされたキーワード間の競合を解決.
 *
 * ルール (原本ベース):
 * - cancelは排他的 (他の全マッチング無視)
 * - feature-pilot + bug-fix 同時 → feature-pilot 優先 (BUG_FIX パイプライン内蔵)
 * - persistent + 他のモード → 両方アクティブ (persistentがラッパー)
 * - turbo + feature-pilot → 両方アクティブ (turboが実行エンジン)
 *
 * v2.1 追加:
 * - intent マッチングが mention マッチングより優先
 *
 * @param {Array} matches - matchKeywords() 結果配列
 * @returns {Array} 解決されたキーワードオブジェクト配列
 */
function resolveConflicts(matches) {
  const names = matches.map((m) => m.keyword.name);

  // Cancelは排他的 (原本と同一)
  if (names.includes('cancel')) {
    return [matches.find((m) => m.keyword.name === 'cancel').keyword];
  }

  let resolved = matches.map((m) => m.keyword);

  // research-pilotとfeature-pilot 同時 → research-pilot 優先
  // (research-pilotがfeature-pilotの前段 Discovery 段階のため上位オーケストレーター優先)
  if (names.includes('research-pilot') && names.includes('feature-pilot')) {
    resolved = resolved.filter((k) => k.name !== 'feature-pilot');
  }

  // feature-pilotとbug-fix 同時 → feature-pilot 優先
  if (names.includes('feature-pilot') && names.includes('bug-fix')) {
    resolved = resolved.filter((k) => k.name !== 'bug-fix');
  }

  // analyze-pipelineとcompetitive-tracker 同時 → analyze-pipeline 優先
  // (analyze-pipelineがcompetitive-trackerをStage 1で内部呼び出しするため上位オーケストレーター優先)
  if (names.includes('analyze-pipeline') && names.includes('competitive-tracker')) {
    resolved = resolved.filter((k) => k.name !== 'competitive-tracker');
  }

  // 重複除去 (同じキーワードが intent+mention 両側でマッチングされる可能性あり)
  const seen = new Set();
  resolved = resolved.filter((k) => {
    if (seen.has(k.name)) return false;
    seen.add(k.name);
    return true;
  });

  // 優先順位順ソート (原本と同一パターン)
  resolved.sort((a, b) => PRIORITY_ORDER.indexOf(a.name) - PRIORITY_ORDER.indexOf(b.name));

  return resolved;
}

// ═══════════════════════════════════════════════════════════════════
// Skill 呼び出しメッセージ (原本 createSkillInvocation() 忠実移植)
// ═══════════════════════════════════════════════════════════════════

/**
 * 単一Skill呼び出しメッセージ生成.
 * Claudeに Skill ツールを即時呼び出しを指示.
 */
function createSkillInvocation(keyword, originalPrompt) {
  return `[MAGIC KEYWORD: ${keyword.name.toUpperCase()}]

You MUST invoke the skill using the Skill tool:

Skill: ${keyword.skill}

User request:
${originalPrompt}

IMPORTANT: Invoke the skill IMMEDIATELY. Do not proceed without loading the skill instructions.`;
}

/**
 * 複数Skill呼び出しメッセージ生成.
 * 順序通りに全スキルを呼び出すよう指示.
 */
function createMultiSkillInvocation(keywords, originalPrompt) {
  if (keywords.length === 0) return '';
  if (keywords.length === 1) {
    return createSkillInvocation(keywords[0], originalPrompt);
  }

  const skillBlocks = keywords
    .map((k, i) => {
      return `### Skill ${i + 1}: ${k.name.toUpperCase()}
Skill: ${k.skill}`;
    })
    .join('\n\n');

  return `[MAGIC KEYWORDS DETECTED: ${keywords.map((k) => k.name.toUpperCase()).join(', ')}]

You MUST invoke ALL of the following skills using the Skill tool, in order:

${skillBlocks}

User request:
${originalPrompt}

IMPORTANT: Invoke ALL skills listed above. Start with the first skill IMMEDIATELY.
After it completes, invoke the next skill in order. Do not skip any skill.`;
}

// ═══════════════════════════════════════════════════════════════════
// Hook 出力 (原本 createHookOutput() 忠実移植)
// ═══════════════════════════════════════════════════════════════════

/**
 * Claude Code Hooks API 規格の出力生成.
 *
 * hookSpecificOutput.additionalContext:
 * - UserPromptSubmit フックで使用
 * - Claudeの現在のターンに追加コンテキストとして注入
 * - このメッセージがSkill呼び出しを強制する
 *
 * @param {string} additionalContext - 注入するコンテキスト文字列
 * @returns {object} Hook API 規格 JSON
 */
function createHookOutput(additionalContext) {
  return {
    continue: true,
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext,
    },
  };
}

// ═══════════════════════════════════════════════════════════════════
// メイン実行
// ═══════════════════════════════════════════════════════════════════

async function main() {
  try {
    const data = await readStdin();

    const directory = data.directory || process.cwd();
    const stateDir = join(directory, '.claude', 'state');

    const prompt = extractPrompt(data);
    if (!prompt) {
      return output({ continue: true });
    }

    // 明示的 /skill-name 呼び出しはSkillシステムに委任 (原本と同一)
    if (prompt.trim().startsWith('/')) {
      return output({ continue: true });
    }

    // 前処理後キーワードマッチング (v2.1: cleanPromptForMatching + 2層マッチング)
    const cleanPrompt = cleanPromptForMatching(prompt);

    // ── 2層キーワードマッチング ──
    const matches = matchKeywords(cleanPrompt, prompt);

    // マッチングなし → パススルー
    if (matches.length === 0) {
      return output({ continue: true });
    }

    // ── 競合解決 ──
    const resolved = resolveConflicts(matches);

    // ── Cancel 処理 (BUG-9: 現在セッションのモードのみ削除) ──
    if (resolved.length > 0 && resolved[0].name === 'cancel') {
      const currentSessionId = data.session_id || '';
      for (const mode of ['persistent', 'web-qa', 'turbo']) {
        const modeState = readState(stateDir, mode);
        if (!modeState || isSessionOwned(modeState, currentSessionId)) {
          clearState(stateDir, mode);
        }
      }
      return output(createHookOutput(createSkillInvocation(resolved[0], prompt)));
    }

    // ── 状態ファイル生成 ──
    ensureStateDir(stateDir);
    for (const keyword of resolved) {
      if (!keyword.createsState) continue;

      // 既にアクティブ状態なら再生成しない (冪等性)
      const existing = readState(stateDir, keyword.stateFile);
      if (existing?.active) continue;

      const state = {
        ...keyword.defaultState,
        started_at: new Date().toISOString(),
        original_prompt: prompt.substring(0, 500),
        last_checked_at: new Date().toISOString(),
        activated_by: 'keyword-detector',
        session_id: data.session_id || '',
      };

      writeState(stateDir, keyword.stateFile, state);
    }

    // ── persistent + turbo 自動連携 (原本の ralph + ultrawork 連携) ──
    const hasPersistent = resolved.some((m) => m.name === 'persistent');
    const hasTurbo = resolved.some((m) => m.name === 'turbo');
    if (hasPersistent && !hasTurbo) {
      const existing = readState(stateDir, 'turbo');
      if (!existing?.active) {
        const turboKeyword = KEYWORD_DEFINITIONS.find((k) => k.name === 'turbo');
        writeState(stateDir, 'turbo', {
          ...turboKeyword.defaultState,
          started_at: new Date().toISOString(),
          original_prompt: prompt.substring(0, 500),
          last_checked_at: new Date().toISOString(),
          activated_by: 'keyword-detector:persistent-auto',
          session_id: data.session_id || '',
        });
      }
    }

    // ── Skill 呼び出しメッセージ生成 + 出力 ──
    return output(createHookOutput(createMultiSkillInvocation(resolved, prompt)));
  } catch (error) {
    // エラー時はパススルー (原本と同一: フックがClaudeを絶対にブロックしてはならない)
    console.error(`[keyword-detector] Error: ${error.message}`);
    return output({ continue: true });
  }
}

main();
