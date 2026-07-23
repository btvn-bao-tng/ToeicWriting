window.TW.RevisionPage = function RevisionPage({ app }) {
  const { RevisionScreen } = window.TW;
  const { isGuest, handleLogin, navigate } = app;
  return (
    <RevisionScreen
      isGuest={isGuest}
      onLogin={handleLogin}
      onPlayGame={() => navigate({ view: "game", testId: null, mockExamId: null })}
    />
  );
};
