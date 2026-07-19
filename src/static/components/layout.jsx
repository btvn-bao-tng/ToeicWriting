window.TW.Header = function Header({ status, user, onLogout }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-12 max-w-5xl items-center justify-between gap-4 px-4 py-2 max-[860px]:min-h-0">
        <h1 className="text-lg font-extrabold leading-tight tracking-normal">TOEIC SW Writing</h1>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="font-medium">{status}</span>
          {user ? (
            <>
              <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-semibold text-slate-700">{user.username}</span>
              <button
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-teal-700 hover:border-teal-700 hover:bg-teal-50"
                type="button"
                onClick={onLogout}
              >
                Logout
              </button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
};

window.TW.EmptyState = function EmptyState({ children, error = false }) {
  return (
    <div className={`rounded-lg border border-dashed p-6 ${error ? "border-red-200 bg-red-50 text-red-800" : "border-slate-200 bg-white text-slate-500"}`}>
      {children}
    </div>
  );
};

window.TW.TestList = function TestList({ tests, selectedId, onSelect }) {
  const { PILL_CLASS } = window.TW.classes;
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-extrabold text-slate-900">Choose a test</h2>
      <p className="text-sm text-slate-500">Select a TOEIC SW Writing test to start practicing or take a mock exam.</p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {tests.map((test) => (
          <button
            key={test.study4_test_id}
            type="button"
            onClick={() => onSelect(test.study4_test_id)}
            className={`rounded-lg border bg-white p-4 text-left shadow-sm transition hover:border-teal-700 hover:bg-teal-50 ${
              test.study4_test_id === selectedId ? "border-teal-700 bg-teal-50" : "border-slate-200"
            }`}
          >
            <strong className="block text-base font-extrabold text-slate-900">{test.title}</strong>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} min</span>
              <span className={PILL_CLASS}>{test.question_count} questions</span>
              <span className={PILL_CLASS}>{test.access_status}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
};

window.TW.TestActions = function TestActions({ test, onBack, onPractice, onMockExam }) {
  const { PILL_CLASS } = window.TW.classes;
  return (
    <section className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="text-sm font-bold text-teal-700 hover:underline"
      >
        ← Back to tests
      </button>
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-extrabold text-slate-900">{test.title}</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} minutes</span>
          <span className={PILL_CLASS}>{test.question_count} questions</span>
          <span className={PILL_CLASS}>{test.access_status}</span>
        </div>
        <p className="mt-4 text-sm text-slate-500">
          Choose how you want to work with this test.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={onPractice}
            className="min-h-14 rounded-lg border border-teal-700 bg-teal-700 px-4 py-3 text-left text-white shadow-sm hover:bg-teal-800"
          >
            <strong className="block text-base">Practice</strong>
            <span className="mt-0.5 block text-xs opacity-90">Score each question as you go</span>
          </button>
          <button
            type="button"
            onClick={onMockExam}
            className="min-h-14 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left text-slate-900 shadow-sm hover:border-teal-700 hover:bg-teal-50"
          >
            <strong className="block text-base">Mock Exam</strong>
            <span className="mt-0.5 block text-xs text-slate-500">Answer all, then score to 0–200</span>
          </button>
        </div>
      </section>
    </section>
  );
};
