#!/usr/bin/env node

/**
 * edit-error-recovery.mjs - PostToolUse Edit Hook
 *
 * Edit 失敗を検出して自己復旧ガイダンスをClaudeに注入します.
 *
 * Self-Healing Loop (核心メカニズム):
 * ┌─────────────────────────────────────────────────────────┐
 * │ 1. ClaudeがWrite/Edit → dart-format Hookがファイル再フォーマット │
 * │ 2. Claudeがstale contentでEdit → 失敗                │
 * │ 3. がHookが検出 → "Read まず" ガイダンス注入           │
 * │ 4. ClaudeがRead → 最新フォーマット済みcontent確保 → 成功     │
 * └─────────────────────────────────────────────────────────┘
 *
 * oh-my-opencodeのedit-error-recovery パターンをClaude Code Hookで実装.
 */

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

/**
 * Edit 失敗 有無 判断
 * Claude CodeのEdit ツールは失敗時に特定エラーメッセージを返却
 */
function isEditFailure(output) {
  if (typeof output !== 'string') return false;

  const failurePatterns = [
    'is not unique',
    'was not found',
    'not found in',
    'no match',
    'does not exist',
    'multiple occurrences',
    'old_string',
    'did not match',
  ];

  const lower = output.toLowerCase();
  return failurePatterns.some((p) => lower.includes(p));
}

/**
 * 失敗タイプに応じた復旧ガイダンス生成
 */
function getRecoveryGuidance(output, filePath) {
  const lower = output.toLowerCase();

  // Case 1: old_stringが見つからない (最も一般的なケース)
  // 原因: dart formatがインデント/空白を変更したか、以前の編集で内容が変わった
  if (
    lower.includes('not found') ||
    lower.includes('no match') ||
    lower.includes('did not match')
  ) {
    return (
      `[Edit Recovery] "${filePath}" 編集失敗: old_stringが見つかりません.\n` +
      `考えられる原因: dart formatがファイルを再フォーマットした可能性があります.\n` +
      `解決: Read ツールで"${filePath}"の現在の内容を読んでから再度Editしてください.`
    );
  }

  // Case 2: old_stringが複数箇所で見つかった
  if (lower.includes('not unique') || lower.includes('multiple')) {
    return (
      `[Edit Recovery] "${filePath}" 編集失敗: old_stringが複数箇所で見つかりました.\n` +
      `解決: 周辺コードをより多く含めてold_stringを一意にするか、replace_allの使用を検討してください.`
    );
  }

  // Case 3: ファイルが存在しない
  if (lower.includes('does not exist')) {
    return (
      `[Edit Recovery] "${filePath}" 編集失敗: ファイルが存在しません.\n` +
      `解決: ファイルパスを確認してください. 新規ファイルならWriteツールを使用してください.`
    );
  }

  return null;
}

async function main() {
  try {
    const input = await readStdin();
    const data = JSON.parse(input);

    const output = data.tool_output || '';
    const filePath = data.tool_input?.file_path || 'unknown';

    // Edit 成功なら何もしない
    if (!isEditFailure(output)) return;

    const guidance = getRecoveryGuidance(output, filePath);

    if (guidance) {
      // Claudeに復旧ガイダンス注入 (v2.1: continue: true 追加 - BUG-5 修正)
      console.log(
        JSON.stringify({
          continue: true,
          hookSpecificOutput: {
            additionalContext: guidance,
          },
        }),
      );
    }
  } catch (error) {
    // Hook 失敗は non-critical
    console.error(`[edit-error-recovery] ${error.message}`);
  }
}

main();
