export type CommentaryEventType = 'battle_start' | 'attack' | 'critical' | 'low_hp' | 'ko';

export interface CommentaryEvent {
  event: CommentaryEventType;
  attacker?: string;
  defender?: string;
  attackName?: string;
  damage?: number;
  remainingHp?: number;
  maxHp?: number;
  winner?: string;
  loser?: string;
  element1?: string;
  element2?: string;
  totalRounds?: number;
}

export interface CommentaryState {
  text: string;
  isLoading: boolean;
  isSpeaking: boolean;
  /** Gemini Live APIによるネイティブ音声出力中か */
  isLiveVoice: boolean;
}
