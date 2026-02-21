import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGameState } from '@/features/game/hooks/useGameState';
import { KAIJU_PRESETS, INITIAL_HP } from '@/shared/constants/kaiju-data';
import type { AttackResult } from '@/features/battle/types/battle';

describe('useGameState', () => {
  it('初期状態は title フェーズ', () => {
    const { result } = renderHook(() => useGameState());
    expect(result.current.state.phase).toBe('title');
  });

  it('START_GAME で select フェーズに遷移', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    expect(result.current.state.phase).toBe('select');
    expect(result.current.state.selectingPlayer).toBe(0);
  });

  it('P1 怪獣選択後 P2 の番になる', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.selectKaiju(0, KAIJU_PRESETS[0]));

    expect(result.current.state.selectingPlayer).toBe(1);
    expect(result.current.state.players[0]).not.toBeNull();
    expect(result.current.state.players[0]!.kaiju.id).toBe('01');
  });

  it('P2 怪獣選択後 battle フェーズに遷移', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.selectKaiju(0, KAIJU_PRESETS[0]));
    act(() => result.current.selectKaiju(1, KAIJU_PRESETS[1]));

    expect(result.current.state.phase).toBe('battle');
    expect(result.current.state.players[0]).not.toBeNull();
    expect(result.current.state.players[1]).not.toBeNull();
    expect(result.current.state.currentTurn).toBe(0);
  });

  it('APPLY_ATTACK でダメージが反映される', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.selectKaiju(0, KAIJU_PRESETS[0]));
    act(() => result.current.selectKaiju(1, KAIJU_PRESETS[1]));

    const attack: AttackResult = {
      player: 0,
      voiceAnalysis: {
        intensity: 80,
        creativity: 70,
        emotion: 90,
        language: 'ja',
        transcript: 'テスト攻撃',
        attackType: 'special',
      },
      damage: 50,
      isCritical: false,
      attackName: '「テスト攻撃」',
    };

    act(() => result.current.applyAttack(attack));

    expect(result.current.state.players[1]!.hp).toBe(INITIAL_HP - 50);
    expect(result.current.state.battleLog).toHaveLength(1);
    expect(result.current.state.battleSubPhase).toBe('attacking');
  });

  it('NEXT_TURN でターンが切り替わる', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.selectKaiju(0, KAIJU_PRESETS[0]));
    act(() => result.current.selectKaiju(1, KAIJU_PRESETS[1]));

    const attack: AttackResult = {
      player: 0,
      voiceAnalysis: {
        intensity: 50,
        creativity: 50,
        emotion: 50,
        language: 'ja',
        transcript: '',
        attackType: 'physical',
      },
      damage: 30,
      isCritical: false,
      attackName: 'テスト攻撃',
    };

    act(() => result.current.applyAttack(attack));
    act(() => result.current.nextTurn());

    expect(result.current.state.currentTurn).toBe(1);
  });

  it('HP 0 で result フェーズに遷移', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.selectKaiju(0, KAIJU_PRESETS[0]));
    act(() => result.current.selectKaiju(1, KAIJU_PRESETS[1]));

    const killAttack: AttackResult = {
      player: 0,
      voiceAnalysis: {
        intensity: 100,
        creativity: 100,
        emotion: 100,
        language: 'mixed',
        transcript: '最強の叫び',
        attackType: 'ultimate',
      },
      damage: INITIAL_HP,
      isCritical: true,
      attackName: '「最強の叫び」',
    };

    act(() => result.current.applyAttack(killAttack));
    act(() => result.current.nextTurn());

    expect(result.current.state.phase).toBe('result');
    expect(result.current.state.winner).toBe(0);
  });

  it('PLAY_AGAIN で select フェーズにリセット', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.playAgain());

    expect(result.current.state.phase).toBe('select');
    expect(result.current.state.players[0]).toBeNull();
  });

  it('BACK_TO_TITLE で title フェーズに戻る', () => {
    const { result } = renderHook(() => useGameState());
    act(() => result.current.startGame('pvp'));
    act(() => result.current.backToTitle());

    expect(result.current.state.phase).toBe('title');
  });
});
