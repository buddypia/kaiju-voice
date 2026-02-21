#!/usr/bin/env node
/**
 * @fileoverview ui-flow.json → コード + 図表 自動生成スクリプト
 *
 * 生成ファイル:
 *   1. src/shared/lib/session-machine.generated.ts  — XState v5 マシン
 *   2. src/shared/lib/panel-registry.generated.ts   — Panel + Phase + SSE Map
 *   3. src/shared/types/ui-flow.generated.ts        — 型定義
 *   4. docs/ui-flow/generated/statechart.mmd        — Mermaid 状態遷移図
 *   5. docs/ui-flow/generated/panel-matrix.md       — パネル×フェーズ マトリクス
 *
 * Usage:
 *   node scripts/generate-from-ssot.mjs          # 生成
 *   node scripts/generate-from-ssot.mjs --check  # 鮮度チェック（CI用）
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const UI_FLOW_PATH = resolve(ROOT, 'docs/ui-flow/ui-flow.json');

const isCheckMode = process.argv.includes('--check');

// ─── ヘルパー ───────────────────────────────────────
/** 生成ファイルヘッダー */
function header(version) {
  return `/* eslint-disable */
/**
 * @generated
 * DO NOT EDIT MANUALLY — ui-flow.json から自動生成
 * 再生成: make codegen
 * Source: docs/ui-flow/ui-flow.json v${version}
 */
`;
}

/** camelCase → UPPER_SNAKE_CASE */
function toUpperSnake(str) {
  return str
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .replace(/-/g, '_')
    .toUpperCase();
}

/** sse_mapping のキーから対応するマシンイベントを導出 */
function deriveMachineEvent(sseName, statechartEvents) {
  const sseUpper = `SSE_${toUpperSnake(sseName)}`;
  if (statechartEvents.has(sseUpper)) return sseUpper;

  const upper = toUpperSnake(sseName);
  if (statechartEvents.has(upper)) return upper;

  return null;
}

// ─── メイン ─────────────────────────────────────────
function main() {
  const uiFlow = JSON.parse(readFileSync(UI_FLOW_PATH, 'utf-8'));
  const { version, statechart, panels, phases, sse_mapping } = uiFlow;

  // statechart の全イベントを収集
  const statechartEvents = new Set();
  for (const stateNode of Object.values(statechart.states)) {
    if (stateNode.on) {
      for (const eventName of Object.keys(stateNode.on)) {
        statechartEvents.add(eventName);
      }
    }
  }

  const outputs = new Map();

  // 1. 型定義生成
  outputs.set(
    resolve(ROOT, 'src/shared/types/ui-flow.generated.ts'),
    generateTypes(version, statechart, panels, phases, sse_mapping),
  );

  // 2. XState マシン生成
  outputs.set(
    resolve(ROOT, 'src/shared/lib/session-machine.generated.ts'),
    generateSessionMachine(version, statechart),
  );

  // 3. Panel Registry 生成
  outputs.set(
    resolve(ROOT, 'src/shared/lib/panel-registry.generated.ts'),
    generatePanelRegistry(version, panels, phases, sse_mapping, statechartEvents),
  );

  // 4. Mermaid 図生成
  outputs.set(
    resolve(ROOT, 'docs/ui-flow/generated/statechart.mmd'),
    generateMermaidDiagram(statechart),
  );

  // 5. Panel Matrix 生成
  outputs.set(
    resolve(ROOT, 'docs/ui-flow/generated/panel-matrix.md'),
    generatePanelMatrix(version, panels, phases),
  );

  if (isCheckMode) {
    let stale = false;
    for (const [filePath, expected] of outputs) {
      if (!existsSync(filePath)) {
        console.error(`MISSING: ${filePath}`);
        stale = true;
        continue;
      }
      const actual = readFileSync(filePath, 'utf-8');
      if (actual !== expected) {
        console.error(`STALE: ${filePath}`);
        stale = true;
      }
    }
    if (stale) {
      console.error('\n❌ Generated files are out of date. Run: make codegen');
      process.exit(1);
    }
    console.log('✅ All generated files are up-to-date');
    return;
  }

  // 書き込み
  for (const [filePath, content] of outputs) {
    const dir = dirname(filePath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(filePath, content, 'utf-8');
    console.log(`  ✓ ${filePath.replace(ROOT + '/', '')}`);
  }
  console.log(`\n✅ Generated ${outputs.size} files from ui-flow.json v${version}`);
}

// ─── 型定義生成 ─────────────────────────────────────
function generateTypes(version, statechart, panels, phases, sseMapping) {
  const stateNames = Object.keys(statechart.states);
  const panelIds = Object.keys(panels);
  const phaseNames = Object.keys(phases);
  const sseEventTypes = Object.keys(sseMapping);

  // statechart の全イベント名を収集
  const allEvents = new Set();
  for (const stateNode of Object.values(statechart.states)) {
    if (stateNode.on) {
      for (const eventName of Object.keys(stateNode.on)) {
        allEvents.add(eventName);
      }
    }
  }

  return `${header(version)}
/** セッション状態 — statechart.states のキー */
export type SessionState = ${stateNames.map((s) => `'${s}'`).join(' | ')};

/** マシンイベント型 — statechart で定義された全イベント */
export type MachineEventType = ${[...allEvents].map((e) => `'${e}'`).join(' | ')};

/** マシンイベント */
export type MachineEvent = { readonly type: MachineEventType };

/** パネルID — panels のキー */
export type PanelId = ${panelIds.map((p) => `'${p}'`).join(' | ')};

/** フェーズ名 — phases のキー (SessionState と同一) */
export type PhaseName = ${phaseNames.map((p) => `'${p}'`).join(' | ')};

/** SSEイベントタイプ — sse_mapping のキー */
export type SSEEventType = ${sseEventTypes.map((e) => `'${e}'`).join(' | ')};

/** SSE Event Map エントリ */
export interface SSEEventMapEntry {
  readonly machineEvent: MachineEventType | null;
  readonly targetPanel: PanelId;
  readonly statusChange: SessionState | null;
}

/** Phase Layout エントリ */
export interface PhaseLayoutEntry {
  readonly layout: string;
  readonly activePanels: readonly PanelId[];
  readonly autoScrollRef: string | null;
}
`;
}

// ─── XState マシン生成 ──────────────────────────────
function generateSessionMachine(version, statechart) {
  const allEvents = new Set();
  for (const stateNode of Object.values(statechart.states)) {
    if (stateNode.on) {
      for (const eventName of Object.keys(stateNode.on)) {
        allEvents.add(eventName);
      }
    }
  }

  const eventTypeUnion = [...allEvents].map((e) => `{ type: '${e}' }`).join(' | ');

  // ステートノード構築
  const stateEntries = Object.entries(statechart.states).map(([name, node]) => {
    const transitions = node.on
      ? Object.entries(node.on)
          .map(([event, config]) => {
            const target = typeof config === 'string' ? config : config.target;
            return `      ${event}: { target: '${target}' }`;
          })
          .join(',\n')
      : '';

    return `    ${name}: {${transitions ? `\n      on: {\n${transitions},\n      },\n    ` : ' '}}`;
  });

  return `${header(version)}
import { setup } from 'xstate';

/** セッション状態マシン — ui-flow.json の statechart から生成 */
export const sessionMachine = setup({
  types: {
    events: {} as ${eventTypeUnion},
  },
}).createMachine({
  id: '${statechart.id}',
  initial: '${statechart.initial}',
  states: {
${stateEntries.join(',\n')},
  },
});
`;
}

// ─── Panel Registry 生成 ────────────────────────────
function generatePanelRegistry(version, panels, phases, sseMapping, statechartEvents) {
  // SSE Event Map
  const sseEntries = Object.entries(sseMapping)
    .map(([name, config]) => {
      const machineEvent =
        config.status_change === null ? null : deriveMachineEvent(name, statechartEvents);
      const machineEventStr = machineEvent ? `'${machineEvent}'` : 'null';
      const statusChange = config.status_change ? `'${config.status_change}'` : 'null';
      return `  '${name}': { machineEvent: ${machineEventStr}, targetPanel: '${config.target_panel}', statusChange: ${statusChange} }`;
    })
    .join(',\n');

  // Phase Layout
  const phaseEntries = Object.entries(phases)
    .map(([name, config]) => {
      const panelsArr = config.active_panels.map((p) => `'${p}'`).join(', ');
      const scrollRef = config.auto_scroll_ref ? `'${config.auto_scroll_ref}'` : 'null';
      return `  '${name}': { layout: '${config.layout}', activePanels: [${panelsArr}] as const, autoScrollRef: ${scrollRef} }`;
    })
    .join(',\n');

  // Panel定義
  const panelEntries = Object.entries(panels)
    .map(([id, config]) => {
      return `  '${id}': { feature: '${config.feature}', component: '${config.component}', visibilityType: '${config.visibility.type}' }`;
    })
    .join(',\n');

  return `${header(version)}
import type { SSEEventType, SSEEventMapEntry, PhaseName, PhaseLayoutEntry, PanelId } from '@/shared/types/ui-flow.generated';

/** SSEイベント → マシンイベント + ターゲットパネル マッピング */
export const SSE_EVENT_MAP: Record<SSEEventType, SSEEventMapEntry> = {
${sseEntries},
} as const;

/** フェーズ → レイアウト + アクティブパネル + 自動スクロール */
export const PHASE_LAYOUT: Record<PhaseName, PhaseLayoutEntry> = {
${phaseEntries},
} as const;

/** パネル定義 */
export const PANEL_REGISTRY: Record<PanelId, { readonly feature: string; readonly component: string; readonly visibilityType: string }> = {
${panelEntries},
} as const;
`;
}

// ─── Mermaid 状態遷移図 ─────────────────────────────
function generateMermaidDiagram(statechart) {
  const lines = ['stateDiagram-v2'];
  lines.push(`  [*] --> ${statechart.initial}`);

  for (const [name, node] of Object.entries(statechart.states)) {
    if (node.meta?.description) {
      lines.push(`  ${name} : ${name}\\n${node.meta.description}`);
    }
    if (node.on) {
      for (const [event, config] of Object.entries(node.on)) {
        const target = typeof config === 'string' ? config : config.target;
        lines.push(`  ${name} --> ${target} : ${event}`);
      }
    }
  }

  return lines.join('\n') + '\n';
}

// ─── Panel Matrix 生成 ──────────────────────────────
function generatePanelMatrix(version, panels, phases) {
  const panelIds = Object.keys(panels);
  const phaseNames = Object.keys(phases);

  const lines = [
    `<!-- @generated — ui-flow.json v${version} から自動生成 -->`,
    '# Panel × Phase 可視性マトリクス',
    '',
    `| Panel | ${phaseNames.join(' | ')} |`,
    `| --- | ${phaseNames.map(() => ':---:').join(' | ')} |`,
  ];

  for (const panelId of panelIds) {
    const cells = phaseNames.map((phase) => {
      return phases[phase].active_panels.includes(panelId) ? '●' : '−';
    });
    lines.push(`| ${panelId} | ${cells.join(' | ')} |`);
  }

  return lines.join('\n') + '\n';
}

// ─── 実行 ───────────────────────────────────────────
main();
