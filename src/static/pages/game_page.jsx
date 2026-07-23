window.TW.GamePage = function GamePage({ app }) {
  const { GameScreen } = window.TW;
  const { isGuest, handleLogin, navigate } = app;
  return (
    <GameScreen
      isGuest={isGuest}
      onLogin={handleLogin}
      onLeave={() => navigate({ view: "tests", testId: null, mockExamId: null })}
      onGoRevision={() => navigate({ view: "revision", testId: null, mockExamId: null })}
    />
  );
};
