window.TW.MockPage = function MockPage({ app }) {
  const { MockExamScreen } = window.TW;
  const { currentPayload, route, setStatus, navigate, isGuest, handleLogin } = app;

  if (isGuest) {
    return (
      <div className="rounded-[18px] border border-hairline bg-parchment p-10 text-center">
        <p className="mb-4 text-[17px] text-ink-80">Mock exams require login. Log in to start a timed mock exam.</p>
        <button
          type="button"
          onClick={handleLogin}
          className="rounded-full bg-action px-6 py-2.5 text-[17px] font-normal text-white active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus"
        >
          Login with Gmail
        </button>
      </div>
    );
  }

  return (
    <MockExamScreen
      currentPayload={currentPayload}
      initialMockExamId={route.mockExamId}
      onStatus={setStatus}
      onLeave={() => navigate({ view: "actions", testId: currentPayload.test.study4_test_id, mockExamId: null })}
      onStartMockExam={(id) => navigate({ view: "mock", testId: currentPayload.test.study4_test_id, mockExamId: id })}
      onNewMockExam={() => navigate({ view: "mock", testId: currentPayload.test.study4_test_id, mockExamId: null })}
    />
  );
};
