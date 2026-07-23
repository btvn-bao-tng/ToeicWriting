window.TW.ActionsPage = function ActionsPage({ app }) {
  const { TestActions } = window.TW;
  const { currentPayload, handleStartPractice, handleStartMock, navigate } = app;
  return (
    <TestActions
      test={currentPayload.test}
      onBack={() => navigate({ view: "tests", testId: null, mockExamId: null })}
      onPractice={handleStartPractice}
      onMockExam={handleStartMock}
    />
  );
};
