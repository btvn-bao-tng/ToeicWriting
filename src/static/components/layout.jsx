window.TW.Header = function Header({ status }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="relative mx-auto flex min-h-14 max-w-7xl items-center justify-center gap-4 px-1.5 py-2.5 max-[860px]:min-h-0">
        <h1 className="text-center text-xl font-extrabold leading-tight tracking-normal">TOEIC SW Writing Browser</h1>
        <div className="absolute right-1.5 top-1/2 -translate-y-1/2 whitespace-nowrap text-xs text-slate-500 max-[860px]:static max-[860px]:translate-y-0">
          {status}
        </div>
      </div>
    </header>
  );
};

window.TW.Sidebar = function Sidebar({ tests, selectedId, onSelect }) {
  const { TEST_BUTTON_BASE } = window.TW.classes;

  return (
    <aside aria-label="Writing tests" className="sticky top-[72px] max-h-[calc(100vh-88px)] self-start overflow-auto rounded-lg border border-slate-200 bg-white max-[860px]:static max-[860px]:max-h-none">
      {tests.map((test) => (
        <button
          key={test.study4_test_id}
          className={`${TEST_BUTTON_BASE} ${test.study4_test_id === selectedId ? "bg-teal-50" : ""}`}
          type="button"
          onClick={() => onSelect(test.study4_test_id)}
        >
          <span>
            <strong className="block text-sm font-extrabold text-slate-500">{test.title}</strong>
            <span className="text-xs text-slate-500">{test.duration_minutes ?? "-"} min · {test.practice_count ?? 0} practices</span>
          </span>
          <span className="min-w-9 rounded-full bg-slate-100 px-2 py-1 text-center text-xs text-slate-500">
            {test.crawled_question_count}/{test.question_count}
          </span>
        </button>
      ))}
    </aside>
  );
};

window.TW.EmptyState = function EmptyState({ children, error = false }) {
  return (
    <div className={`rounded-lg border border-dashed p-6 ${error ? "border-red-200 bg-red-50 text-red-800" : "border-slate-200 bg-white text-slate-500"}`}>
      {children}
    </div>
  );
};
