'use client';

import { useReducer, useCallback } from 'react';
import type {
  GameState,
  GameAction,
  GameMode,
  KaijuProfile,
  AttackResult,
} from '@/features/battle/types/battle';
import { INITIAL_HP } from '@/shared/constants/kaiju-data';

const initialState: GameState = {
  phase: 'title',
  gameMode: 'pvp',
  battleSubPhase: 'ready',
  players: [null, null],
  currentTurn: 0,
  roundNumber: 1,
  battleLog: [],
  lastAttack: null,
  winner: null,
  selectingPlayer: 0,
};

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'START_GAME':
      return { ...initialState, phase: 'select', selectingPlayer: 0, gameMode: action.mode };

    case 'SELECT_KAIJU': {
      const newPlayers = [...state.players] as [
        (typeof state.players)[0],
        (typeof state.players)[1],
      ];
      /** hero_vs_kaiju モードではP1を'HERO'、P2を'KAIJU'と表示 */
      let playerName: string;
      if (state.gameMode === 'hero_vs_kaiju' && action.player === 0) {
        playerName = 'HERO';
      } else if (state.gameMode === 'hero_vs_kaiju' && action.player === 1) {
        playerName = 'KAIJU';
      } else if (state.gameMode === 'vsai' && action.player === 1) {
        playerName = 'AI';
      } else {
        playerName = `P${action.player + 1}`;
      }

      newPlayers[action.player] = {
        id: action.player,
        name: playerName,
        kaiju: action.kaiju,
        hp: INITIAL_HP,
        maxHp: INITIAL_HP,
      };

      if (action.player === 0) {
        return { ...state, players: newPlayers, selectingPlayer: 1 };
      }
      return {
        ...state,
        players: newPlayers,
        phase: 'battle',
        battleSubPhase: 'ready',
        currentTurn: 0,
        roundNumber: 1,
      };
    }

    case 'START_RECORDING':
      return { ...state, battleSubPhase: 'recording' };

    case 'STOP_RECORDING':
      return state;

    case 'SET_ANALYZING':
      return { ...state, battleSubPhase: 'analyzing' };

    case 'SET_AI_THINKING':
      return { ...state, battleSubPhase: 'ai_thinking' };

    case 'APPLY_ATTACK': {
      const { attack } = action;
      const defenderIdx = attack.player === 0 ? 1 : 0;
      const defender = state.players[defenderIdx];
      if (!defender) return state;

      const newHp = Math.max(0, defender.hp - attack.damage);
      const newPlayers = [...state.players] as typeof state.players;
      newPlayers[defenderIdx] = { ...defender, hp: newHp };

      const logEntry = {
        round: state.roundNumber,
        turn: attack.player,
        attack,
        remainingHp: [newPlayers[0]?.hp ?? 0, newPlayers[1]?.hp ?? 0] as [number, number],
        timestamp: Date.now(),
      };

      return {
        ...state,
        players: newPlayers,
        lastAttack: attack,
        battleLog: [...state.battleLog, logEntry],
        battleSubPhase: 'attacking',
      };
    }

    case 'NEXT_TURN': {
      const defenderIdx = state.currentTurn === 0 ? 1 : 0;
      const defender = state.players[defenderIdx];
      if (defender && defender.hp <= 0) {
        return { ...state, phase: 'result', winner: state.currentTurn, battleSubPhase: 'ready' };
      }

      const nextTurn = state.currentTurn === 0 ? 1 : 0;
      const nextRound = nextTurn === 0 ? state.roundNumber + 1 : state.roundNumber;

      return {
        ...state,
        currentTurn: nextTurn as 0 | 1,
        roundNumber: nextRound,
        battleSubPhase: 'ready',
        lastAttack: null,
      };
    }

    case 'END_BATTLE':
      return { ...state, phase: 'result', winner: action.winner };

    case 'PLAY_AGAIN':
      return { ...initialState, phase: 'select', selectingPlayer: 0, gameMode: state.gameMode };

    case 'BACK_TO_TITLE':
      return initialState;

    case 'UPDATE_KAIJU_IMAGE': {
      const newPlayers = [...state.players] as typeof state.players;
      const player = newPlayers[action.playerId];
      if (player) {
        newPlayers[action.playerId] = {
          ...player,
          kaiju: { ...player.kaiju, imageUrl: action.imageUrl },
        };
      }
      return { ...state, players: newPlayers };
    }

    default:
      return state;
  }
}

/** ゲーム状態管理フック */
export function useGameState() {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  const startGame = useCallback((mode: GameMode) => dispatch({ type: 'START_GAME', mode }), []);
  const selectKaiju = useCallback(
    (player: 0 | 1, kaiju: KaijuProfile) => dispatch({ type: 'SELECT_KAIJU', player, kaiju }),
    [],
  );
  const startRecording = useCallback(() => dispatch({ type: 'START_RECORDING' }), []);
  const setAnalyzing = useCallback(() => dispatch({ type: 'SET_ANALYZING' }), []);
  const setAIThinking = useCallback(() => dispatch({ type: 'SET_AI_THINKING' }), []);
  const applyAttack = useCallback(
    (attack: AttackResult) => dispatch({ type: 'APPLY_ATTACK', attack }),
    [],
  );
  const nextTurn = useCallback(() => dispatch({ type: 'NEXT_TURN' }), []);
  const playAgain = useCallback(() => dispatch({ type: 'PLAY_AGAIN' }), []);
  const backToTitle = useCallback(() => dispatch({ type: 'BACK_TO_TITLE' }), []);
  const updateKaijuImage = useCallback(
    (playerId: 0 | 1, imageUrl: string) =>
      dispatch({ type: 'UPDATE_KAIJU_IMAGE', playerId, imageUrl }),
    [],
  );

  return {
    state,
    startGame,
    selectKaiju,
    startRecording,
    setAnalyzing,
    applyAttack,
    nextTurn,
    playAgain,
    backToTitle,
    updateKaijuImage,
    setAIThinking,
  };
}
