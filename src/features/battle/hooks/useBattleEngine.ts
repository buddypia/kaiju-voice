import type { VoiceAnalysis, AttackResult, Player } from '../types/battle';
import { ELEMENT_MATCHUP } from '@/shared/constants/kaiju-data';

/** ダメージ計算ロジック (SPEC FR-00103 準拠) */
export function calculateDamage(
  analysis: VoiceAnalysis | { error: string },
  attacker: Player,
  defender: Player,
): AttackResult {
  if ('error' in analysis || !analysis.intensity) {
    console.error('分析エラーのためデフォルトダメージを適用', analysis);
    return {
      player: attacker.id,
      voiceAnalysis: {
        intensity: 50,
        creativity: 50,
        emotion: 50,
        language: 'ja',
        transcript: '（声にならない叫び）',
        attackType: 'physical',
      },
      damage: 10,
      isCritical: false,
      attackName: '普通の叫び',
    };
  }

  const basePower = (analysis.intensity + analysis.creativity + analysis.emotion) / 3;

  const typeMultiplier =
    analysis.attackType === 'ultimate' ? 1.8 : analysis.attackType === 'special' ? 1.3 : 1.0;

  const langBonus = analysis.language === 'mixed' ? 1.2 : 1.0;

  const elementBonus = ELEMENT_MATCHUP[attacker.kaiju.element][defender.kaiju.element];

  const statRatio = attacker.kaiju.baseAttack / defender.kaiju.baseDefense;

  let damage = Math.round(basePower * typeMultiplier * langBonus * elementBonus * statRatio);

  let isCritical = false;
  if (analysis.creativity > 80 && Math.random() < 0.2) {
    damage *= 2;
    isCritical = true;
  }

  damage = Math.max(1, damage);

  const attackName = generateAttackName(analysis, attacker);

  return {
    player: attacker.id,
    voiceAnalysis: analysis,
    damage,
    isCritical,
    attackName,
  };
}

/** 攻撃名を生成 */
function generateAttackName(analysis: VoiceAnalysis, attacker: Player): string {
  if (analysis.transcript.length > 0) {
    return `「${analysis.transcript}」`;
  }

  const elementAttacks: Record<string, string[]> = {
    fire: ['ファイヤーブレス', '灼熱の咆哮', '炎の叫び'],
    ice: ['フリーズボイス', '氷結の絶叫', '凍てつく咆哮'],
    thunder: ['サンダーボルト', '雷鳴の叫び', '稲妻の咆哮'],
    earth: ['アースクエイク', '大地の怒り', '岩砕の咆哮'],
    void: ['ヴォイドスクリーム', '虚無の共鳴', '暗黒の咆哮'],
    light: ['ホーリーレイ', '光の裁き', '聖なる咆哮'],
  };

  const attacks = elementAttacks[attacker.kaiju.element] ?? ['叫び'];
  return attacks[Math.floor(Math.random() * attacks.length)];
}
