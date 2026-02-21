/** 怪獣の属性 */
export type KaijuElement = 'fire' | 'ice' | 'thunder' | 'earth' | 'void' | 'light';

/** キャラクターカテゴリ */
export type CharacterCategory = 'kaiju' | 'hero';

/** ゲームモード */
export type GameMode = 'pvp' | 'vsai' | 'hero_vs_kaiju';

/** ゲームフェーズ */
export type GamePhase = 'title' | 'select' | 'battle' | 'result';

/** バトルサブフェーズ */
export type BattleSubPhase =
  | 'ready'
  | 'recording'
  | 'analyzing'
  | 'attacking'
  | 'waiting'
  | 'ai_thinking';

/** 怪獣プロフィール */
export interface KaijuProfile {
  id: string;
  name: string;
  nameJa: string;
  element: KaijuElement;
  category: CharacterCategory;
  description: string;
  imageUrl: string | null;
  baseAttack: number;
  baseDefense: number;
}

/** プレイヤー */
export interface Player {
  id: 0 | 1;
  name: string;
  kaiju: KaijuProfile;
  hp: number;
  maxHp: number;
}

/** 音声分析結果 */
export interface VoiceAnalysis {
  intensity: number;
  creativity: number;
  emotion: number;
  language: 'ja' | 'en' | 'mixed';
  transcript: string;
  attackType: 'physical' | 'special' | 'ultimate';
}

/** 攻撃結果 */
export interface AttackResult {
  player: 0 | 1;
  voiceAnalysis: VoiceAnalysis;
  damage: number;
  isCritical: boolean;
  attackName: string;
}

/** バトルログエントリ */
export interface BattleLogEntry {
  round: number;
  turn: 0 | 1;
  attack: AttackResult;
  remainingHp: [number, number];
  timestamp: number;
}

/** ゲーム全体の状態 */
export interface GameState {
  phase: GamePhase;
  gameMode: GameMode;
  battleSubPhase: BattleSubPhase;
  players: [Player | null, Player | null];
  currentTurn: 0 | 1;
  roundNumber: number;
  battleLog: BattleLogEntry[];
  lastAttack: AttackResult | null;
  winner: 0 | 1 | null;
  selectingPlayer: 0 | 1;
}

/** AI対戦の攻撃生成リクエスト */
export interface AIAttackRequest {
  aiKaiju: { name: string; nameJa: string; element: KaijuElement };
  opponentKaiju: { name: string; nameJa: string; element: KaijuElement };
  aiHp: number;
  opponentHp: number;
  maxHp: number;
  roundNumber: number;
}

/** AI対戦の攻撃生成レスポンス */
export interface AIAttackResponse {
  shoutText: string;
  intensity: number;
  creativity: number;
  emotion: number;
  attackType: 'physical' | 'special' | 'ultimate';
}

/** ゲームアクション */
export type GameAction =
  | { type: 'START_GAME'; mode: GameMode }
  | { type: 'SELECT_KAIJU'; player: 0 | 1; kaiju: KaijuProfile }
  | { type: 'START_RECORDING' }
  | { type: 'STOP_RECORDING' }
  | { type: 'SET_ANALYZING' }
  | { type: 'SET_AI_THINKING' }
  | { type: 'APPLY_ATTACK'; attack: AttackResult }
  | { type: 'NEXT_TURN' }
  | { type: 'END_BATTLE'; winner: 0 | 1 }
  | { type: 'PLAY_AGAIN' }
  | { type: 'BACK_TO_TITLE' }
  | { type: 'UPDATE_KAIJU_IMAGE'; playerId: 0 | 1; imageUrl: string };
