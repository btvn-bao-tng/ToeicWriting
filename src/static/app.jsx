const { useEffect, useMemo, useState } = React;

const LAST_TEST_KEY = "toeic-sw-writing-last-test-id";
const LAST_PART_KEY = "toeic-sw-writing-last-part";
const LAST_QUESTION_KEY = "toeic-sw-writing-last-question-number";

function visibleQuestions(payload, selectedPart) {
  const questions = payload?.questions || [];
  if (selectedPart === "all") return questions;
  const part = (payload?.parts || []).find((item) => String(item.sort_order) === String(selectedPart));
  if (!part) return questions;
  return questions.filter((question) => question.study4_part_id === part.study4_part_id);
}

window.TW.App = function App() {
  const {
    Header,
    Sidebar,
    EmptyState,
    TestSummary,
    PartTabs,
    QuestionCard,
    answerKey,
    attemptsKey,
    fetchJson,
    localGet,
    partName,
    readJsonLocal,
    scoreKey,
    streamScore,
    writeJsonLocal,
  } = window.TW;

  const [tests, setTests] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedPart, setSelectedPart] = useState(() => localStorage.getItem(LAST_PART_KEY) || "all");
  const [currentPayload, setCurrentPayload] = useState(null);
  const [status, setStatus] = useState("Loading database...");
  const [loadError, setLoadError] = useState("");
  const [loadingTest, setLoadingTest] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [attempts, setAttempts] = useState({});
  const [scoringNumbers, setScoringNumbers] = useState(new Set());
  const [scoringVisible, setScoringVisible] = useState(false);
  const [lastQuestionNumber, setLastQuestionNumber] = useState(() => Number(localStorage.getItem(LAST_QUESTION_KEY)) || null);

  const questions = useMemo(() => visibleQuestions(currentPayload, selectedPart), [currentPayload, selectedPart]);
  const parts = currentPayload?.parts || [];
  const modeLabel = selectedPart === "all"
    ? "Full test"
    : partName(parts.find((part) => String(part.sort_order) === String(selectedPart)));

  useEffect(() => {
    async function boot() {
      try {
        const nextTests = await fetchJson("/api/tests");
        setTests(nextTests);
        setStatus(`${nextTests.length} tests loaded`);
        const savedId = Number(localStorage.getItem(LAST_TEST_KEY));
        const savedTest = nextTests.find((test) => test.study4_test_id === savedId);
        const initialId = savedTest?.study4_test_id ?? nextTests[0]?.study4_test_id ?? null;
        if (initialId) {
          await loadTest(initialId, {
            part: localStorage.getItem(LAST_PART_KEY) || "all",
            remember: false,
          });
        }
      } catch (error) {
        setStatus("Database unavailable");
        setLoadError(`Could not load database: ${error.message}`);
      }
    }
    boot();
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

  async function loadTest(id, options = {}) {
    const nextPart = options.part ?? "all";
    setSelectedId(id);
    setSelectedPart(nextPart);
    setCurrentPayload(null);
    setLoadingTest(true);
    setLoadError("");
    if (options.remember !== false) {
      localStorage.setItem(LAST_TEST_KEY, String(id));
      localStorage.setItem(LAST_PART_KEY, nextPart);
      localStorage.removeItem(LAST_QUESTION_KEY);
      setLastQuestionNumber(null);
    }

    try {
      const payload = await fetchJson(`/api/tests/${id}`);
      setCurrentPayload(payload);

      const nextDrafts = {};
      const nextAttempts = {};
      (payload.questions || []).forEach((question) => {
        const aKey = answerKey(question);
        const atKey = attemptsKey(question);
        const savedDraft = localGet(aKey);
        const savedScore = localGet(scoreKey(question));
        const savedAttempts = readJsonLocal(atKey, null);

        nextDrafts[aKey] = savedDraft;
        if (Array.isArray(savedAttempts)) {
          nextAttempts[atKey] = savedAttempts;
        } else if (savedScore || savedDraft) {
          nextAttempts[atKey] = savedDraft || savedScore ? [{
            id: `legacy-${question.study4_test_id}-${question.question_number}`,
            answer: savedDraft,
            score: savedScore ? { state: "visible", text: savedScore } : null,
          }] : [];
        } else {
          nextAttempts[atKey] = [];
        }
      });
      setDrafts((previous) => ({ ...previous, ...nextDrafts }));
      setAttempts((previous) => ({ ...previous, ...nextAttempts }));
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

  function getDraft(question) {
    const key = answerKey(question);
    return drafts[key] ?? localGet(key);
  }

  function getAttempts(question) {
    const key = attemptsKey(question);
    return attempts[key] || readJsonLocal(key, []);
  }

  function handleDraftChange(question, value) {
    rememberQuestion(question);
    const key = answerKey(question);
    localStorage.setItem(key, value);
    setDrafts((previous) => ({ ...previous, [key]: value }));
  }

  function handleClear(question) {
    rememberQuestion(question);
    const aKey = answerKey(question);
    const sKey = scoreKey(question);
    const atKey = attemptsKey(question);
    localStorage.removeItem(aKey);
    localStorage.removeItem(sKey);
    localStorage.removeItem(atKey);
    setDrafts((previous) => ({ ...previous, [aKey]: "" }));
    setAttempts((previous) => ({ ...previous, [atKey]: [] }));
  }

  function updateAttempt(question, attemptId, patch) {
    const atKey = attemptsKey(question);
    setAttempts((previous) => {
      const nextList = (previous[atKey] || []).map((attempt) => (
        attempt.id === attemptId ? { ...attempt, ...patch } : attempt
      ));
      writeJsonLocal(atKey, nextList);
      return { ...previous, [atKey]: nextList };
    });
  }

  async function handleScore(question) {
    rememberQuestion(question);
    const answer = getDraft(question);
    const aKey = answerKey(question);
    const atKey = attemptsKey(question);

    if (!answer.trim()) {
      return;
    }

    localStorage.setItem(aKey, answer);
    const attemptId = `${Date.now()}-${question.id}-${Math.random().toString(36).slice(2, 8)}`;
    const attempt = {
      id: attemptId,
      answer,
      created_at: new Date().toISOString(),
      score: { state: "streaming", text: "### Scoring\n\nWaiting for the first tokens..." },
    };

    const nextAttempts = [...getAttempts(question), attempt];
    writeJsonLocal(atKey, nextAttempts);
    setAttempts((previous) => ({ ...previous, [atKey]: nextAttempts }));
    setScoringNumbers((previous) => new Set(previous).add(question.question_number));

    try {
      const scoreText = await streamScore(question, answer, (partialText) => {
        updateAttempt(question, attemptId, {
          score: { state: "streaming", text: partialText || "### Scoring\n\nThinking..." },
        });
      });
      updateAttempt(question, attemptId, {
        score: { state: "visible", text: scoreText },
      });
    } catch (error) {
      updateAttempt(question, attemptId, {
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

  function handleClearVisible() {
    questions.forEach(handleClear);
  }

  async function handleScoreVisible() {
    setScoringVisible(true);
    try {
      for (const question of questions) {
        await handleScore(question);
      }
    } finally {
      setScoringVisible(false);
    }
  }

  return (
    <>
      <Header status={status} />
      <main className="grid w-full grid-cols-[minmax(220px,1fr)_minmax(0,4fr)] gap-6 p-6 max-[860px]:grid-cols-1">
        <Sidebar tests={tests} selectedId={selectedId} onSelect={(id) => loadTest(id, { part: "all" })} />
        <section className="min-w-0">
          {loadError ? <EmptyState error>{loadError}</EmptyState> : null}
          {!loadError && loadingTest ? <EmptyState>Loading questions...</EmptyState> : null}
          {!loadError && !loadingTest && !currentPayload ? <EmptyState>Loading tests...</EmptyState> : null}
          {!loadError && !loadingTest && currentPayload ? (
            <>
              <TestSummary test={currentPayload.test} questions={questions} modeLabel={modeLabel} />
              <PartTabs
                payload={currentPayload}
                selectedPart={selectedPart}
                onSelectPart={handleSelectPart}
                onScoreVisible={handleScoreVisible}
                onClearVisible={handleClearVisible}
                scoringVisible={scoringVisible}
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
                  />
                ))
              ) : (
                <EmptyState>No questions found for this part.</EmptyState>
              )}
            </>
          ) : null}
        </section>
      </main>
    </>
  );
};
