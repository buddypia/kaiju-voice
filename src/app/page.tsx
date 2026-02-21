'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useGameState } from '@/features/game/hooks/useGameState';
import { TitleScreen } from '@/features/game/components/TitleScreen';
import { SelectScreen } from '@/features/game/components/SelectScreen';
import { BattleScreen } from '@/features/game/components/BattleScreen';
import { ResultScreen } from '@/features/game/components/ResultScreen';

const pageVariants = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 1.02 },
};
const pageTransition = { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const };

/** メインページ: ゲームフェーズに応じた画面の切替 */
export default function HomePage() {
  const {
    state,
    startGame,
    selectKaiju,
    startRecording,
    setAnalyzing,
    setAIThinking,
    applyAttack,
    nextTurn,
    playAgain,
    backToTitle,
    updateKaijuImage,
  } = useGameState();

  const renderScreen = () => {
    if (state.phase === 'title') {
      return (
        <motion.div
          key="title"
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
          className="w-full h-full"
        >
          <TitleScreen onStart={startGame} />
        </motion.div>
      );
    }

    if (state.phase === 'select') {
      return (
        <motion.div
          key="select"
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
          className="w-full h-full"
        >
          <SelectScreen
            selectingPlayer={state.selectingPlayer}
            gameMode={state.gameMode}
            onSelectKaiju={selectKaiju}
          />
        </motion.div>
      );
    }

    if (state.phase === 'battle') {
      const p0 = state.players[0];
      const p1 = state.players[1];
      if (!p0 || !p1) return null;

      return (
        <motion.div
          key="battle"
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
          className="w-full h-full"
        >
          <BattleScreen
            players={[p0, p1]}
            currentTurn={state.currentTurn}
            roundNumber={state.roundNumber}
            lastAttack={state.lastAttack}
            battleSubPhase={state.battleSubPhase}
            battleLog={state.battleLog}
            gameMode={state.gameMode}
            onStartRecording={startRecording}
            onSetAnalyzing={setAnalyzing}
            onSetAIThinking={setAIThinking}
            onApplyAttack={applyAttack}
            onNextTurn={nextTurn}
            updateKaijuImage={updateKaijuImage}
          />
        </motion.div>
      );
    }

    if (state.phase === 'result') {
      const winnerIdx = state.winner;
      if (winnerIdx === null) return null;
      const winner = state.players[winnerIdx];
      const loser = state.players[winnerIdx === 0 ? 1 : 0];
      if (!winner || !loser) return null;

      return (
        <motion.div
          key="result"
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
          className="w-full h-full"
        >
          <ResultScreen
            winner={winner}
            loser={loser}
            battleLog={state.battleLog}
            onPlayAgain={playAgain}
            onBackToTitle={backToTitle}
          />
        </motion.div>
      );
    }

    return null;
  };

  return <AnimatePresence mode="wait">{renderScreen()}</AnimatePresence>;
}
