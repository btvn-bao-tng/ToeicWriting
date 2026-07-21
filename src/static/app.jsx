const { useEffect, useMemo, useRef, useState } = React;

const LAST_TEST_KEY = "toeic-sw-writing-last-test-id";
const LAST_PART_KEY = "toeic-sw-writing-last-part";
const LAST_QUESTION_KEY = "toeic-sw-writing-last-question-number";

function parseHash() {
  const raw = (window.location.hash || "#/tests").replace(/^#/, "");
  const segments = raw.split("/").filter(Boolean);
  if (segments[0] !== "tests") return { view: "tests", testId: null, mockExamId: null };
  const testId = segments[1] ? Number(segments[1]) : null;
  const view = segments[2] || "actions";
  const mockExamId = segments[3] ? Number(segments[3]) : null;
  if (!testId) return { view: "tests", testId: null, mockExamId: null };
  if (!["actions", "practice", "mock"].includes(view)) return { view: "actions", testId, mockExamId: null };
  return { view, testId, mockExamId };
}

function buildHash({ view, testId, mockExamId }) {
  if (!testId) return "#/tests";
  if (view === "mock" && mockExamId) return `#/tests/${testId}/mock/${mockExamId}`;
  if (view === "actions") return `#/tests/${testId}`;
  return `#/tests/${testId}/${view}`;
}

function visibleQuestions(payload, selectedPart) {
  const questions = payload?.questions || [];
  if (selectedPart === "all") return questions;
  const part = (payload?.parts || []).find((item) => String(item.sort_order) === String(selectedPart));
  if (!part) return questions;
  return questions.filter((question) => question.study4_part_id === part.study4_part_id);
}

function progressKey(question) {
  return `${question.study4_test_id}:${question.question_number}`;
}

function scoreFromRow(row) {
  return {
    id: String(row.id),
    answer: row.answer || "",
    created_at: row.created_at,
    model: row.model,
    score: {
      state: row.score_state || "visible",
      text: row.score_text || "",
    },
  };
}

window.TW.App = function App() {
  const {
    Header,
    EmptyState,
    TestSummary,
    PartTabs,
    QuestionCard,
    AuthScreen,
    MockExamScreen,
    TestList,
    TestActions,
    apiFetch,
    apiJson,
    partName,
    streamScore,
    generateVocab,
    getVocab,
  } = window.TW;

  const [currentUser, setCurrentUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tests, setTests] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedPart, setSelectedPart] = useState(() => localStorage.getItem(LAST_PART_KEY) || "all");
  const [route, setRoute] = useState(parseHash);
  const [currentPayload, setCurrentPayload] = useState(null);
  const [status, setStatus] = useState("Checking session...");
  const [loadError, setLoadError] = useState("");
  const [loadingTest, setLoadingTest] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [attempts, setAttempts] = useState({});
  const [scoringNumbers, setScoringNumbers] = useState(new Set());
  const [scoringVisible, setScoringVisible] = useState(false);
  const [lastQuestionNumber, setLastQuestionNumber] = useState(() => Number(localStorage.getItem(LAST_QUESTION_KEY)) || null);
  const draftTimers = useRef({});
  const pendingDrafts = useRef({});
  const vocabPrefetched = useRef(new Set());
  const attemptsRef = useRef(attempts);

  function navigate(nextRoute) {
    const hash = buildHash(nextRoute);
    if (window.location.hash !== hash) {
      window.location.hash = hash;
    }
    setRoute(nextRoute);
  }

  const questions = useMemo(() => visibleQuestions(currentPayload, selectedPart), [currentPayload, selectedPart]);
  const parts = currentPayload?.parts || [];
  const modeLabel = selectedPart === "all"
    ? "Full test"
    : partName(parts.find((part) => String(part.sort_order) === String(selectedPart)));

  useEffect(() => { attemptsRef.current = attempts; }, [attempts]);

  function visibleAttemptIdFor(q) {
    const list = attemptsRef.current[progressKey(q)] || [];
    const a = list[list.length - 1];
    if (!a) return null;
    const id = a.id;
    if (!id || String(id).startsWith("temp-")) return null;
    if (a.score?.state !== "visible") return null;
    return id;
  }

  // When a question scrolls into view, warm the vocab cache for it and the
  // next 2 questions by calling POST /api/vocab (generates + saves on the
  // server). Results are stored in window.TW.vocabCache so the modal opens
  // instantly. Each question is requested at most once per session.
  function prefetchVocab(activeQuestion) {
    const idx = questions.findIndex((q) => q.question_number === activeQuestion.question_number);
    if (idx === -1) return;
    const targets = questions.slice(idx, idx + 3);
    for (const q of targets) {
      const key = progressKey(q);
      if (vocabPrefetched.current.has(key)) continue;
      vocabPrefetched.current.add(key);
      const attemptId = visibleAttemptIdFor(q);
      (async () => {
        try {
          const existing = await getVocab(q.study4_test_id, q.question_number);
          const payload = existing
            ? existing
            : await generateVocab(q.study4_test_id, q.question_number, attemptId);
          if (window.TW.vocabCache) window.TW.vocabCache[key] = payload;
        } catch (_err) {
          vocabPrefetched.current.delete(key);
        }
      })();
    }
  }

  useEffect(() => {
    if (route.view !== "practice" || !currentUser || !questions.length) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting);
      if (!visible.length) return;
      visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      const el = visible[0].target;
      const match = el.id && el.id.match(/^question-(.+)$/);
      if (!match) return;
      const active = questions.find((q) => String(q.id) === match[1]);
      if (active) prefetchVocab(active);
    }, { rootMargin: "0px 0px -55% 0px", threshold: 0 });
    questions.forEach((q) => {
      const el = document.getElementById(`question-${q.id}`);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [questions, route.view, currentUser]);

  useEffect(() => {
    async function boot() {
      try {
        const user = await apiJson("/api/auth/me", { suppressAuthExpired: true });
        setCurrentUser(user);
      } catch (error) {
        if (error.status && error.status !== 401) {
          setLoadError(`Could not check session: ${error.message}`);
        }
      }
      setAuthChecked(true);
      await loadTests();
      const initialRoute = parseHash();
      if (initialRoute.testId) {
        await loadTest(initialRoute.testId, { view: initialRoute.view, remember: false, mockExamId: initialRoute.mockExamId });
      }
    }
    boot();
  }, []);

  useEffect(() => {
    function handleAuthExpired() {
      Object.values(draftTimers.current).forEach(clearTimeout);
      draftTimers.current = {};
      pendingDrafts.current = {};
      vocabPrefetched.current = new Set();
      setCurrentUser(null);
      setDrafts({});
      setAttempts({});
      setScoringNumbers(new Set());
      setScoringVisible(false);
      setStatus("Session expired. Log in to score and save.");
    }
    window.addEventListener("tw-auth-expired", handleAuthExpired);
    return () => window.removeEventListener("tw-auth-expired", handleAuthExpired);
  }, []);

  useEffect(() => {
    function onHashChange() {
      const nextRoute = parseHash();
      setRoute(nextRoute);
      if (nextRoute.testId && nextRoute.testId !== selectedId) {
        loadTest(nextRoute.testId, { view: nextRoute.view, remember: false, mockExamId: nextRoute.mockExamId });
      }
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [selectedId]);

  useEffect(() => {
    function flushOnLeave() {
      flushPendingDrafts();
    }

    function flushOnHidden() {
      if (document.visibilityState === "hidden") flushPendingDrafts();
    }

    window.addEventListener("pagehide", flushOnLeave);
    window.addEventListener("blur", flushOnLeave);
    document.addEventListener("visibilitychange", flushOnHidden);
    return () => {
      window.removeEventListener("pagehide", flushOnLeave);
      window.removeEventListener("blur", flushOnLeave);
      document.removeEventListener("visibilitychange", flushOnHidden);
    };
  }, []);

  useEffect(() => {
    if (!currentPayload || !lastQuestionNumber || loadingTest) return;
    const question = currentPayload.questions?.find((item) => item.question_number === lastQuestionNumber);
    if (!question) return;

    requestAnimationFrame(() => {
      const element = document.getElementById(`question-${question.id}`);
      element?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [currentPayload, lastQuestionNumber, loadingTest, selectedPart]);

  function clearAppState(nextStatus) {
    Object.values(draftTimers.current).forEach(clearTimeout);
    draftTimers.current = {};
    pendingDrafts.current = {};
    setCurrentUser(null);
    setTests([]);
    setSelectedId(null);
    setCurrentPayload(null);
    setDrafts({});
    setAttempts({});
    setScoringNumbers(new Set());
    setScoringVisible(false);
    setLoadError("");
    setLoadingTest(false);
    setRoute({ view: "tests", testId: null, mockExamId: null });
    setStatus(nextStatus);
  }

  async function loadTests() {
    const nextTests = await apiJson("/api/tests");
    setTests(nextTests);
    setStatus(`${nextTests.length} tests loaded`);
  }

  async function loadTest(id, options = {}) {
    const nextPart = options.part ?? "all";
    setSelectedId(id);
    setSelectedPart(nextPart);
    setCurrentPayload(null);
    setLoadingTest(true);
    setLoadError("");
    vocabPrefetched.current = new Set();
    if (options.remember !== false) {
      localStorage.setItem(LAST_TEST_KEY, String(id));
      localStorage.setItem(LAST_PART_KEY, nextPart);
      localStorage.removeItem(LAST_QUESTION_KEY);
      setLastQuestionNumber(null);
    }

    try {
      const payload = await apiJson(`/api/tests/${id}`);
      const nextDrafts = {};
      const nextAttempts = {};

      (payload.questions || []).forEach((question) => {
        const key = progressKey(question);
        nextDrafts[key] = "";
        nextAttempts[key] = [];
      });

      const progressRes = await apiFetch(`/api/progress?study4_test_id=${encodeURIComponent(id)}`, { suppressAuthExpired: true });
      if (progressRes.ok) {
        const progress = await progressRes.json();
        (progress.drafts || []).forEach((draft) => {
          nextDrafts[`${id}:${draft.question_number}`] = draft.body || "";
        });

        (progress.attempts || []).forEach((attempt) => {
          const key = `${id}:${attempt.question_number}`;
          nextAttempts[key] = [...(nextAttempts[key] || []), scoreFromRow(attempt)];
        });
      }

      setCurrentPayload(payload);
      setDrafts(nextDrafts);
      setAttempts(nextAttempts);
    } catch (error) {
      setLoadError(`Could not load test: ${error.message}`);
    } finally {
      setLoadingTest(false);
    }
  }

  function rememberQuestion(question) {
    localStorage.setItem(LAST_TEST_KEY, String(question.study4_test_id));
    localStorage.setItem(LAST_QUESTION_KEY, String(question.question_number));
    localStorage.setItem(LAST_PART_KEY, selectedPart);
    setLastQuestionNumber(question.question_number);
  }

  function handleSelectPart(part) {
    localStorage.setItem(LAST_PART_KEY, part);
    setSelectedPart(part);
  }

  async function handleSelectTest(id) {
    navigate({ view: "actions", testId: id, mockExamId: null });
    await loadTest(id, { view: "actions" });
  }

  function handleStartPractice() {
    if (!currentPayload) return;
    const nextPart = localStorage.getItem(LAST_PART_KEY) || "all";
    setSelectedPart(nextPart);
    navigate({ view: "practice", testId: currentPayload.test.study4_test_id, mockExamId: null });
  }

  function handleStartMock() {
    if (!currentPayload) return;
    navigate({ view: "mock", testId: currentPayload.test.study4_test_id, mockExamId: null });
  }

  function getDraft(question) {
    return drafts[progressKey(question)] || "";
  }

  function getAttempts(question) {
    return attempts[progressKey(question)] || [];
  }

  function saveDraft(question, value) {
    const key = progressKey(question);
    return apiJson("/api/draft", {
      method: "PUT",
      body: JSON.stringify({
        study4_test_id: question.study4_test_id,
        question_number: question.question_number,
        body: value,
      }),
    }).then(() => {
      if (pendingDrafts.current[key]?.value === value) delete pendingDrafts.current[key];
    });
  }

  function scheduleDraftSave(question, value) {
    if (!currentUser) return;
    const key = progressKey(question);
    pendingDrafts.current[key] = { question, value };
    clearTimeout(draftTimers.current[key]);
    draftTimers.current[key] = setTimeout(() => {
      delete draftTimers.current[key];
      saveDraft(question, value).catch((error) => {
        setStatus(`Draft save failed: ${error.message}`);
      });
    }, 1000);
  }

  function flushPendingDrafts() {
    Object.entries(pendingDrafts.current).forEach(([key, item]) => {
      clearTimeout(draftTimers.current[key]);
      delete draftTimers.current[key];
      apiFetch("/api/draft", {
        method: "PUT",
        keepalive: true,
        body: JSON.stringify({
          study4_test_id: item.question.study4_test_id,
          question_number: item.question.question_number,
          body: item.value,
        }),
      }).catch(() => {});
    });
    pendingDrafts.current = {};
  }

  function handleDraftChange(question, value) {
    rememberQuestion(question);
    const key = progressKey(question);
    setDrafts((previous) => ({ ...previous, [key]: value }));
    scheduleDraftSave(question, value);
  }

  async function handleClear(question) {
    rememberQuestion(question);
    const key = progressKey(question);
    if (currentUser) {
      await apiJson(`/api/progress?study4_test_id=${encodeURIComponent(question.study4_test_id)}&question_number=${encodeURIComponent(question.question_number)}`, {
        method: "DELETE",
      });
    }
    clearTimeout(draftTimers.current[key]);
    delete draftTimers.current[key];
    delete pendingDrafts.current[key];
    setDrafts((previous) => ({ ...previous, [key]: "" }));
    setAttempts((previous) => ({ ...previous, [key]: [] }));
  }

  function updateAttempt(question, attemptId, patch) {
    const key = progressKey(question);
    setAttempts((previous) => {
      const nextList = (previous[key] || []).map((attempt) => (
        String(attempt.id) === String(attemptId) ? { ...attempt, ...patch } : attempt
      ));
      return { ...previous, [key]: nextList };
    });
  }

  async function handleScore(question) {
    if (!currentUser) {
      window.location.href = "/api/auth/google/login";
      return;
    }
    rememberQuestion(question);
    const answer = getDraft(question);
    const key = progressKey(question);

    if (!answer.trim()) {
      return;
    }

    await saveDraft(question, answer).catch(() => {});
    const tempId = `temp-${Date.now()}-${question.id}-${Math.random().toString(36).slice(2, 8)}`;
    let activeAttemptId = tempId;
    const attempt = {
      id: tempId,
      answer,
      created_at: new Date().toISOString(),
      score: { state: "streaming", text: "## Scoring\n\nWaiting for the first tokens..." },
    };

    setAttempts((previous) => ({ ...previous, [key]: [attempt] }));
    setScoringNumbers((previous) => new Set(previous).add(question.question_number));

    try {
      const scoreText = await streamScore(question, answer, {
        onStart: (attemptId) => {
          activeAttemptId = String(attemptId);
          updateAttempt(question, tempId, { id: activeAttemptId });
        },
        onDelta: (partialText) => {
          updateAttempt(question, activeAttemptId, {
            score: { state: "streaming", text: partialText || "## Scoring\n\nThinking..." },
          });
        },
      });
      updateAttempt(question, activeAttemptId, {
        score: { state: "visible", text: scoreText },
      });
    } catch (error) {
      updateAttempt(question, activeAttemptId, {
        score: { state: "error", text: `Could not score answer: ${error.message}` },
      });
    } finally {
      setScoringNumbers((previous) => {
        const next = new Set(previous);
        next.delete(question.question_number);
        return next;
      });
    }
  }

  async function handleClearVisible() {
    for (const question of questions) {
      await handleClear(question);
    }
  }

  async function handleScoreVisible() {
    if (!currentUser) {
      window.location.href = "/api/auth/google/login";
      return;
    }
    setScoringVisible(true);
    try {
      for (const question of questions) {
        await handleScore(question);
      }
    } finally {
      setScoringVisible(false);
    }
  }

  async function handleAuthenticated(user) {
    setCurrentUser(user);
    setAuthChecked(true);
    setLoadError("");
    setStatus("Loading database...");
    await loadTests();
    const initialRoute = parseHash();
    if (initialRoute.testId) {
      await loadTest(initialRoute.testId, { view: initialRoute.view, remember: false, mockExamId: initialRoute.mockExamId });
    }
  }

  function handleLogin() {
    window.location.href = "/api/auth/google/login";
  }

  async function handleLogout() {
    try {
      await apiJson("/api/auth/logout", { method: "POST" });
    } catch (_error) {
      // The local UI can still return to the test list if the session is already gone.
    }
    Object.values(draftTimers.current).forEach(clearTimeout);
    draftTimers.current = {};
    pendingDrafts.current = {};
    vocabPrefetched.current = new Set();
    setCurrentUser(null);
    setDrafts({});
    setAttempts({});
    setScoringNumbers(new Set());
    setScoringVisible(false);
    navigate({ view: "tests", testId: null, mockExamId: null });
    setStatus("Logged out");
  }

  if (!authChecked) {
    return (
      <>
        <Header status={status} />
      <main className="px-4 py-8 sm:px-6 sm:py-12">
        <EmptyState>Checking session...</EmptyState>
        </main>
      </>
    );
  }

  const { view, testId, mockExamId } = route;
  const isGuest = !currentUser;

  return (
    <>
      <Header status={status} user={currentUser} onLogout={handleLogout} onLogin={handleLogin} />
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
          {!loadError && loadingTest ? <EmptyState>Loading test...</EmptyState> : null}

          {!loadError && !loadingTest && view === "tests" ? (
            <TestList tests={tests} selectedId={selectedId} onSelect={handleSelectTest} />
          ) : null}

          {!loadError && !loadingTest && view === "actions" && currentPayload ? (
            <TestActions
              test={currentPayload.test}
              onBack={() => navigate({ view: "tests", testId: null, mockExamId: null })}
              onPractice={handleStartPractice}
              onMockExam={handleStartMock}
            />
          ) : null}

          {!loadError && !loadingTest && view === "practice" && currentPayload ? (
            <>
              <button
                type="button"
                onClick={() => navigate({ view: "actions", testId: currentPayload.test.study4_test_id, mockExamId: null })}
                className="mb-3 text-[14px] font-normal text-action hover:underline"
              >
                ← Back to options
              </button>
              <TestSummary test={currentPayload.test} questions={questions} modeLabel={modeLabel} />
              <PartTabs
                payload={currentPayload}
                selectedPart={selectedPart}
                onSelectPart={handleSelectPart}
                onScoreVisible={handleScoreVisible}
                onClearVisible={handleClearVisible}
                scoringVisible={scoringVisible}
                allowScoring={!isGuest}
                onLogin={handleLogin}
              />
              {questions.length ? (
                questions.map((question, index) => (
                  <QuestionCard
                    key={question.id}
                    question={question}
                    index={index}
                    parts={parts}
                    draft={getDraft(question)}
                    attempts={getAttempts(question)}
                    isScoring={scoringNumbers.has(question.question_number)}
                    onDraftChange={handleDraftChange}
                    onScore={handleScore}
                    onClear={handleClear}
                    onActivate={rememberQuestion}
                    allowScoring={!isGuest}
                    onLogin={handleLogin}
                  />
                ))
              ) : (
                <EmptyState>No questions found for this part.</EmptyState>
              )}
            </>
          ) : null}

          {!loadError && !loadingTest && view === "mock" && currentPayload ? (
            isGuest ? (
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
            ) : (
              <MockExamScreen
                currentPayload={currentPayload}
                initialMockExamId={mockExamId}
                onStatus={setStatus}
                onLeave={() => navigate({ view: "actions", testId: currentPayload.test.study4_test_id, mockExamId: null })}
                onStartMockExam={(id) => navigate({ view: "mock", testId: currentPayload.test.study4_test_id, mockExamId: id })}
                onNewMockExam={() => navigate({ view: "mock", testId: currentPayload.test.study4_test_id, mockExamId: null })}
              />
            )
          ) : null}
        </section>
      </main>
    </>
  );
};
