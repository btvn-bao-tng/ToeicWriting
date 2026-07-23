window.TW.App = function App() {
  const {
    Header,
    EmptyState,
    TestsPage,
    ActionsPage,
    PracticePage,
    MockPage,
    RevisionPage,
    GamePage,
    TestListSkeleton,
    TestActionsSkeleton,
    PracticeSkeleton,
    MockExamSkeleton,
    useAppState,
  } = window.TW;

  const app = useAppState();
  const {
    authChecked,
    status,
    currentUser,
    handleLogout,
    handleLogin,
    route,
    loadError,
    loadingTest,
    isGuest,
  } = app;

  const { view } = route;
  const activeView = view === "tests" || view === "actions" || view === "practice" || view === "mock" ? "tests" : view;

  if (!authChecked) {
    return (
      <>
        <Header status={status} />
        <main className="px-4 py-8 sm:px-6 sm:py-12">
          <section className="mx-auto min-w-0 max-w-5xl">
            <TestListSkeleton />
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <Header status={status} user={currentUser} onLogout={handleLogout} onLogin={handleLogin} activeView={activeView} />
      <main className="px-4 py-8 sm:px-6 sm:py-12">
        <section className="mx-auto min-w-0 max-w-5xl">
          {isGuest ? (
            <div className="mb-3 flex items-center justify-between gap-3 rounded-[18px] border border-hairline bg-parchment px-4 py-2.5 text-[15px] text-ink-80">
              <span>Browsing as a guest. Log in to score answers and save your progress.</span>
              <button
                type="button"
                onClick={handleLogin}
                className="rounded-full bg-action px-4 py-1.5 text-[14px] font-normal text-white active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus"
              >
                Login with Gmail
              </button>
            </div>
          ) : null}
          {loadError ? <EmptyState error>{loadError}</EmptyState> : null}
          {!loadError && loadingTest ? (
            view === "practice" ? <PracticeSkeleton /> :
            view === "mock" ? <MockExamSkeleton /> :
            <TestActionsSkeleton />
          ) : null}

          {!loadError && !loadingTest && view === "tests" ? <TestsPage app={app} /> : null}
          {!loadError && !loadingTest && view === "actions" && app.currentPayload ? <ActionsPage app={app} /> : null}
          {!loadError && !loadingTest && view === "practice" && app.currentPayload ? <PracticePage app={app} /> : null}
          {!loadError && !loadingTest && view === "mock" && app.currentPayload ? <MockPage app={app} /> : null}
          {view === "revision" ? <RevisionPage app={app} /> : null}
          {view === "game" ? <GamePage app={app} /> : null}
        </section>
      </main>
    </>
  );
};
