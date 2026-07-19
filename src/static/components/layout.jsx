window.TW.Header = function Header({ status, user, onLogout, onLogin }) {
  return (
    <header className="sticky top-0 z-20 bg-black text-white">
      <div className="mx-auto flex min-h-[44px] max-w-5xl items-center justify-between gap-4 px-4">
        <h1 className="text-[15px] font-semibold tracking-tight text-white">TOEIC SW Writing</h1>
        <div className="flex items-center gap-3 text-[12px] text-white/60">
          <span className="hidden font-medium text-white/50 sm:inline">{status}</span>
          {user ? (
            <>
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[12px] font-medium text-white/80">{user.username}</span>
              <button
                className="rounded-full border border-white/20 px-3 py-1 text-[12px] text-white/80 active:scale-95 hover:text-white"
                type="button"
                onClick={onLogout}
              >
                Logout
              </button>
            </>
          ) : (
            <button
              className="rounded-full bg-action px-3 py-1 text-[12px] font-medium text-white active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus"
              type="button"
              onClick={onLogin}
            >
              Login with Gmail
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

window.TW.EmptyState = function EmptyState({ children, error = false }) {
  return (
    <div className={`rounded-[18px] border p-6 text-[15px] ${error ? "border-red-200 bg-red-50 text-red-800" : "border-hairline bg-white text-ink-48"}`}>
      {children}
    </div>
  );
};

window.TW.TestList = function TestList({ tests, selectedId, onSelect }) {
  const { PILL_CLASS } = window.TW.classes;
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">Choose a test</h2>
        <p className="text-[17px] text-ink-48">Select a TOEIC SW Writing test to start practicing or take a mock exam.</p>
      </div>
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {tests.map((test) => {
          const selected = test.study4_test_id === selectedId;
          return (
            <button
              key={test.study4_test_id}
              type="button"
              onClick={() => onSelect(test.study4_test_id)}
              className={`rounded-[18px] border bg-white p-6 text-left transition active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus focus-visible:ring-offset-2 ${selected ? "border-action" : "border-hairline hover:border-ink-48"}`}
            >
              <strong className="block text-[17px] font-semibold text-ink">{test.title}</strong>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} min</span>
                <span className={PILL_CLASS}>{test.question_count} questions</span>
                <span className={PILL_CLASS}>{test.access_status}</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};

window.TW.TestActions = function TestActions({ test, onBack, onPractice, onMockExam }) {
  const { PILL_CLASS, LINK, CARD } = window.TW.classes;
  return (
    <section className="space-y-6">
      <button type="button" onClick={onBack} className={`text-[14px] ${LINK}`}>
        ← Back to tests
      </button>
      <section className={`${CARD} p-6 sm:p-8`}>
        <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">{test.title}</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} minutes</span>
          <span className={PILL_CLASS}>{test.question_count} questions</span>
          <span className={PILL_CLASS}>{test.access_status}</span>
        </div>
        <p className="mt-5 text-[17px] text-ink-48">Choose how you want to work with this test.</p>
        <div className="mt-7 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={onPractice}
            className="min-h-[68px] rounded-[18px] bg-action px-5 py-4 text-left text-white transition active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus focus-visible:ring-offset-2"
          >
            <span className="block text-[18px] font-light">Practice</span>
            <span className="mt-1 block text-[14px] font-normal text-white/80">Score each question as you go</span>
          </button>
          <button
            type="button"
            onClick={onMockExam}
            className="min-h-[68px] rounded-[18px] border border-hairline bg-white px-5 py-4 text-left text-ink transition active:scale-95 hover:border-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus focus-visible:ring-offset-2"
          >
            <span className="block text-[18px] font-light">Mock Exam</span>
            <span className="mt-1 block text-[14px] font-normal text-ink-48">Answer all, then score to 0–200</span>
          </button>
        </div>
      </section>
    </section>
  );
};
