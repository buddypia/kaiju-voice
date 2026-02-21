import { describe, it, expect } from 'vitest';
import { calculateDamage } from '@/features/battle/hooks/useBattleEngine';
import type { VoiceAnalysis, Player } from '@/features/battle/types/battle';

const makeAnalysis = (overrides: Partial<VoiceAnalysis> = {}): VoiceAnalysis => ({
  intensity: 50,
  creativity: 50,
  emotion: 50,
  language: 'ja',
  transcript: 'テスト叫び',
  attackType: 'physical',
  ...overrides,
});

const makePlayer = (id: 0 | 1, element: string, atk = 10, def = 10): Player => ({
  id,
  name: `P${id + 1}`,
  kaiju: {
    id: `0${id + 1}`,
    name: 'TestKaiju',
    nameJa: 'テスト怪獣',
    element: element as Player['kaiju']['element'],
    category: 'kaiju',
    description: 'テスト用怪獣',
    imageUrl: null,
    baseAttack: atk,
    baseDefense: def,
  },
  hp: 200,
  maxHp: 200,
});

describe('calculateDamage', () => {
  it('通常攻撃のダメージが計算される', () => {
    const analysis = makeAnalysis();
    const attacker = makePlayer(0, 'fire');
    const defender = makePlayer(1, 'fire');

    const result = calculateDamage(analysis, attacker, defender);

    expect(result.damage).toBeGreaterThan(0);
    expect(result.player).toBe(0);
    expect(result.attackName).toBe('「テスト叫び」');
  });

  it('special 攻撃は倍率 1.3x', () => {
    const physical = calculateDamage(
      makeAnalysis({ attackType: 'physical' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );
    const special = calculateDamage(
      makeAnalysis({ attackType: 'special' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );

    expect(special.damage).toBeGreaterThan(physical.damage);
  });

  it('ultimate 攻撃は倍率 1.8x', () => {
    const physical = calculateDamage(
      makeAnalysis({ attackType: 'physical' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );
    const ultimate = calculateDamage(
      makeAnalysis({ attackType: 'ultimate' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );

    expect(ultimate.damage).toBeGreaterThan(physical.damage);
  });

  it('属性有利 (fire vs ice) で倍率 1.5x', () => {
    const neutral = calculateDamage(makeAnalysis(), makePlayer(0, 'fire'), makePlayer(1, 'fire'));
    const advantage = calculateDamage(makeAnalysis(), makePlayer(0, 'fire'), makePlayer(1, 'ice'));

    expect(advantage.damage).toBeGreaterThan(neutral.damage);
  });

  it('mixed 言語ボーナス 1.2x', () => {
    const ja = calculateDamage(
      makeAnalysis({ language: 'ja' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );
    const mixed = calculateDamage(
      makeAnalysis({ language: 'mixed' }),
      makePlayer(0, 'fire'),
      makePlayer(1, 'fire'),
    );

    expect(mixed.damage).toBeGreaterThan(ja.damage);
  });

  it('ダメージ最低値は 1', () => {
    const analysis = makeAnalysis({ intensity: 1, creativity: 1, emotion: 1 });
    const attacker = makePlayer(0, 'fire', 1, 10);
    const defender = makePlayer(1, 'fire', 10, 100);

    const result = calculateDamage(analysis, attacker, defender);

    expect(result.damage).toBeGreaterThanOrEqual(1);
  });

  it('transcript 空の場合は属性技名が生成される', () => {
    const analysis = makeAnalysis({ transcript: '' });
    const attacker = makePlayer(0, 'fire');
    const defender = makePlayer(1, 'ice');

    const result = calculateDamage(analysis, attacker, defender);

    expect(result.attackName.length).toBeGreaterThan(0);
  });
});
