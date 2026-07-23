const { useEffect, useMemo, useRef, useState } = React;

window.TW.useAppState = function useAppState() {
  const {
    apiFetch,
    apiJson,
    partName,
    streamScore,
    generateVocab,
    getVocab,
    listRevision,
    addRevision,
    removeRevision,
    parseHash,
    buildHash,
    visibleQuestions,
    progressKey,
    scoreFromRow,
    LAST_TEST_KEY,
    LAST_PART_KEY,
    LAST_QUESTION_KEY,
  } = window.TW;

  const [currentUser, setCurrentUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tests, setTests] = useState([]);
  const [loadingTests, setLoadingTests] = useState(true);
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
  const [revisionItems, setRevisionItems] = useState([]);
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

  const revisionSavedKeys = useMemo(
    () => new Set(revisionItems.map((it) => (it.term || "").toLowerCase())),
    [revisionItems]
  );
  const revisionTermToId = useRef({});
  useEffect(() => {
    revisionTermToId.current = Object.fromEntries(
      revisionItems.map((it) => [(it.term || "").toLowerCase(), it.id])
    );
  }, [revisionItems]);

  function visibleAttemptIdFor(q) {
    const list = attemptsRef.current[progressKey(q)] || [];
    const a = list[list.length - 1];
    if (!a) return null;
    const id = a.id;
    if (!id || String(id).startsWith("temp-")) return null;
    if (a.score?.state !== "visible") return null;
    return id;
  }

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
      if (user) {
        loadRevision();
      }
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
      setRevisionItems([]);
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
    setRevisionItems([]);
    setLoadError("");
    setLoadingTest(false);
    setRoute({ view: "tests", testId: null, mockExamId: null });
    setStatus(nextStatus);
  }

  async function loadTests() {
    setLoadingTests(true);
    try {
      const nextTests = await apiJson("/api/tests");
      setTests(nextTests);
      setStatus(`${nextTests.length} tests loaded`);
    } finally {
      setLoadingTests(false);
    }
  }

  async function loadRevision() {
    try {
      const items = await listRevision();
      setRevisionItems(items);
    } catch (error) {
      setStatus(`Could not load revision: ${error.message}`);
    }
  }

  async function handleToggleRevision(item) {
    const key = (item.term || "").toLowerCase();
    const existingId = revisionTermToId.current[key];
    if (existingId) {
      const prevItems = revisionItems;
      setRevisionItems((prev) => prev.filter((it) => it.id !== existingId));
      try {
        await removeRevision(existingId);
      } catch (error) {
        setRevisionItems(prevItems);
        setStatus(`Could not remove from revision: ${error.message}`);
      }
    } else {
      const prevItems = revisionItems;
      setRevisionItems((prev) => [...prev, { ...item, id: `temp-${Date.now()}` }]);
      try {
        const saved = await addRevision(item);
        setRevisionItems((prev) => {
          const without = prev.filter((it) => (it.term || "").toLowerCase() !== key);
          return [...without, saved];
        });
      } catch (error) {
        setRevisionItems(prevItems);
        setStatus(`Could not save to revision: ${error.message}`);
      }
    }
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
    loadRevision();
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
    setRevisionItems([]);
    navigate({ view: "tests", testId: null, mockExamId: null });
    setStatus("Logged out");
  }

  const isGuest = !currentUser;

  return {
    currentUser,
    authChecked,
    status,
    setStatus,
    route,
    loadError,
    loadingTest,
    tests,
    loadingTests,
    selectedId,
    currentPayload,
    selectedPart,
    questions,
    parts,
    modeLabel,
    scoringNumbers,
    scoringVisible,
    revisionSavedKeys,
    isGuest,
    navigate,
    handleSelectTest,
    handleStartPractice,
    handleStartMock,
    handleSelectPart,
    handleScoreVisible,
    handleClearVisible,
    getDraft,
    getAttempts,
    handleDraftChange,
    handleScore,
    handleClear,
    rememberQuestion,
    handleToggleRevision,
    handleAuthenticated,
    handleLogin,
    handleLogout,
    clearAppState,
  };
};
