const { useEffect, useMemo, useRef, useState } = React;

function partLabel(sort_order) {
  if (sort_order === "all") return "Entire test";
  return `Part ${sort_order}`;
}

function ExamTimer({ startedAt, endedAt }) {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!startedAt || endedAt) return;
    const interval = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, [startedAt, endedAt]);

  if (!startedAt) return null;

  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const elapsed = Math.max(0, end - start);
  const totalSeconds = Math.floor(elapsed / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n) => String(n).padStart(2, "0");
  const formatted =
    hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white px-3 py-1.5 font-mono text-[14px] font-semibold text-ink">
      <span className="text-[10px] font-semibold uppercase tracking-tight text-ink-48">Time</span>
      {formatted}
    </span>
  );
}

function visibleQuestions(payload, selectedPart) {
  const questions = payload?.questions || [];
  if (selectedPart === "all") return questions;
  const part = (payload?.parts || []).find(
    (item) => String(item.sort_order) === String(selectedPart)
  );
  if (!part) return [];
  return questions.filter((question) => question.study4_part_id === part.study4_part_id);
}

function partForQuestion(question, parts) {
  return parts.find((part) => part.study4_part_id === question.study4_part_id) || null;
}

function formatDate(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString();
  } catch (_error) {
    return iso;
  }
}

window.TW.MockExamScreen = function MockExamScreen({
  currentPayload,
  initialMockExamId,
  onStatus,
  onLeave,
  onStartMockExam,
  onNewMockExam,
}) {
  const {
    EmptyState,
    TestSummary,
    QuestionCard,
    ScoreResult,
    apiJson,
    createMockExam,
    getMockExam,
    saveMockExamDraft,
    submitMockExamStream,
    listMockExams,
    partName,
    MockExamTakingSkeleton,
  } = window.TW;
  const { PILL_CLASS, CARD, BTN_PRIMARY, BTN_UTILITY, LINK } = window.TW.classes;

  const [selectedPart, setSelectedPart] = useState("all");
  const [activeExam, setActiveExam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [history, setHistory] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [draftTimers, setDraftTimers] = useState({});
  const [streamingAttempts, setStreamingAttempts] = useState({});
  const [scoringProgress, setScoringProgress] = useState({
    total: 0,
    current: null,
    status: {},
    messages: {},
  });
  const pendingDrafts = useRef({});

  const test = currentPayload?.test;
  const parts = currentPayload?.parts || [];
  const questions = useMemo(
    () => visibleQuestions(currentPayload, activeExam?.selected_part || selectedPart),
    [currentPayload, activeExam, selectedPart]
  );

  useEffect(() => {
    if (!test) return;
    loadHistory();
  }, [test?.study4_test_id]);

  useEffect(() => {
    // Reset active exam when the selected test changes so the user sees the setup.
    setActiveExam(null);
    setDrafts({});
    setStreamingAttempts({});
    setSelectedPart("all");
  }, [test?.study4_test_id]);

  useEffect(() => {
    if (initialMockExamId && (!activeExam || activeExam.exam.id !== initialMockExamId)) {
      loadExam(initialMockExamId);
    }
  }, [initialMockExamId]);

  async function loadHistory() {
    try {
      const exams = await listMockExams();
      setHistory(exams.filter((exam) => exam.study4_test_id === test?.study4_test_id));
    } catch (error) {
      // History is optional; don't block the UI.
    }
  }

  async function startExam() {
    if (!test) return;
    setLoading(true);
    try {
      const exam = await createMockExam(test.study4_test_id, selectedPart);
      await loadExam(exam.id);
      await loadHistory();
      onStartMockExam(exam.id);
    } catch (error) {
      onStatus(`Could not start mock exam: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadExam(mock_exam_id) {
    setLoading(true);
    try {
      const data = await getMockExam(mock_exam_id);
      setActiveExam(data);
      setStreamingAttempts({});
      const nextDrafts = {};
      (data.questions || []).forEach((question) => {
        nextDrafts[question.question_number] = question.draft || "";
      });
      setDrafts(nextDrafts);
    } catch (error) {
      onStatus(`Could not load mock exam: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  function getDraft(question) {
    return drafts[question.question_number] || "";
  }

  function getAttempts(question) {
    const number = question.question_number;
    const persisted = (activeExam?.attempts || []).filter((attempt) => attempt.question_number === number);
    const streaming = streamingAttempts[number];
    if (!streaming) return persisted;
    return [...persisted, streaming];
  }

  function scheduleDraftSave(question, value) {
    const number = question.question_number;
    pendingDrafts.current[number] = value;
    clearTimeout(draftTimers[number]);
    const timer = setTimeout(async () => {
      if (pendingDrafts.current[number] !== value) return;
      delete pendingDrafts.current[number];
      try {
        await saveMockExamDraft(activeExam.exam.id, number, value);
      } catch (error) {
        onStatus(`Draft save failed: ${error.message}`);
      }
    }, 1000);
    setDraftTimers((previous) => ({ ...previous, [number]: timer }));
  }

  function handleDraftChange(question, value) {
    setDrafts((previous) => ({ ...previous, [question.question_number]: value }));
    scheduleDraftSave(question, value);
  }

  async function handleClear(question) {
    setDrafts((previous) => ({ ...previous, [question.question_number]: "" }));
    try {
      await saveMockExamDraft(activeExam.exam.id, question.question_number, "");
    } catch (error) {
      onStatus(`Could not clear draft: ${error.message}`);
    }
  }

  async function handleSubmit() {
    if (!activeExam) return;
    const emptyQuestions = questions.filter((question) => !getDraft(question).trim());
    if (emptyQuestions.length) {
      const confirmed = window.confirm(
        `${emptyQuestions.length} question(s) are empty. Submit anyway? Empty answers will likely score 0.`
      );
      if (!confirmed) return;
    }
    setSubmitting(true);

    const initialStatus = {};
    questions.forEach((question) => {
      initialStatus[question.question_number] = "pending";
    });
    setScoringProgress({ total: questions.length, current: null, status: initialStatus, messages: {} });
    setStreamingAttempts({});

    try {
      await submitMockExamStream(activeExam.exam.id, {
        onStart: (total) => {
          setScoringProgress((previous) => ({ ...previous, total }));
        },
        onQuestionStart: (number) => {
          setScoringProgress((previous) => ({
            ...previous,
            current: number,
            status: { ...previous.status, [number]: "scoring" },
            messages: { ...previous.messages, [number]: "Scoring..." },
          }));
          setStreamingAttempts((previous) => ({
            ...previous,
            [number]: {
              id: `stream-${number}`,
              answer: getDraft(questions.find((q) => q.question_number === number)),
              created_at: new Date().toISOString(),
              score: { state: "streaming", text: "## Scoring\n\nWaiting for the first tokens..." },
            },
          }));
        },
        onDelta: (number, content) => {
          setScoringProgress((previous) => ({
            ...previous,
            current: number,
            messages: { ...previous.messages, [number]: (previous.messages[number] || "") + content },
          }));
          setStreamingAttempts((previous) => {
            const current = previous[number];
            if (!current) return previous;
            return {
              ...previous,
              [number]: {
                ...current,
                score: {
                  state: "streaming",
                  text: (current.score?.text || "") + content,
                },
              },
            };
          });
        },
        onQuestionDone: (number, data) => {
          setScoringProgress((previous) => ({
            ...previous,
            status: { ...previous.status, [number]: "done" },
            messages: {
              ...previous.messages,
              [number]: `Score: ${data.score_10 ?? "-"} → ${data.converted_score ?? "-"}/${data.max_score}`,
            },
          }));
          setStreamingAttempts((previous) => {
            const current = previous[number];
            if (!current) return previous;
            return {
              ...previous,
              [number]: {
                ...current,
                score: { state: "visible", text: current.score?.text || "" },
              },
            };
          });
        },
        onQuestionError: (number, data) => {
          const { isImageInputError, imageInputErrorMessage } = window.TW;
          const detail = isImageInputError(data.detail)
            ? `${imageInputErrorMessage()} (${data.detail})`
            : data.detail || "Scoring failed";
          setScoringProgress((previous) => ({
            ...previous,
            status: { ...previous.status, [number]: "error" },
            messages: { ...previous.messages, [number]: detail },
          }));
          setStreamingAttempts((previous) => {
            const current = previous[number];
            if (!current) return previous;
            return {
              ...previous,
              [number]: {
                ...current,
                score: { state: "error", text: detail },
              },
            };
          });
        },
      });
      await loadExam(activeExam.exam.id);
      setStreamingAttempts({});
      await loadHistory();
    } catch (error) {
      onStatus(`Mock exam submission failed: ${error.message}`);
    } finally {
      setSubmitting(false);
      setScoringProgress({ total: 0, current: null, status: {}, messages: {} });
    }
  }

  function resetToSetup() {
    setActiveExam(null);
    setDrafts({});
    setStreamingAttempts({});
    setSelectedPart("all");
    onNewMockExam();
  }

  if (!currentPayload) {
    return <EmptyState>Select a test to start a mock exam.</EmptyState>;
  }

  if (loading && !activeExam) {
    return <MockExamTakingSkeleton />;
  }

  if (!activeExam) {
    return (
      <section className="space-y-6">
        <button type="button" onClick={onLeave} className={`text-[14px] ${LINK}`}>
          ← Back to options
        </button>
        <TestSummary test={test} questions={visibleQuestions(currentPayload, selectedPart)} modeLabel="Mock exam" />
        <section className={`${CARD} p-5 sm:p-6`}>
          <h3 className="mb-3 text-[21px] font-semibold tracking-tight text-ink">Select scope</h3>
          <div className="flex flex-wrap gap-2">
            {[
              { key: "1", label: "Part 1" },
              { key: "2", label: "Part 2" },
              { key: "3", label: "Part 3" },
              { key: "all", label: "Entire test" },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedPart(key)}
                className={`min-h-9 rounded-full border px-4 py-1.5 text-[14px] active:scale-95 ${
                  selectedPart === key
                    ? "border-action bg-parchment text-ink"
                    : "border-hairline bg-white text-ink hover:border-ink-48"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={startExam}
              className={BTN_PRIMARY}
            >
              {loading ? "Starting..." : "Start Mock Exam"}
            </button>
            <span className="text-[15px] text-ink-48">
              {visibleQuestions(currentPayload, selectedPart).length} question(s)
            </span>
          </div>
        </section>

        {history.length > 0 ? (
          <section className={`${CARD} p-5 sm:p-6`}>
            <h3 className="mb-3 text-[21px] font-semibold tracking-tight text-ink">Past mock exams for this test</h3>
            <div className="space-y-2">
              {history.map((exam) => (
                <button
                  key={exam.id}
                  type="button"
                  onClick={() => loadExam(exam.id)}
                  className="grid w-full grid-cols-[1fr_auto_auto] items-center gap-3 rounded-[11px] border border-hairline bg-parchment px-4 py-3 text-left active:scale-95 hover:bg-pearl"
                >
                  <span className="text-[15px] font-semibold text-ink">
                    {partLabel(exam.selected_part)}
                  </span>
                  <span className="text-[14px] text-ink-48">{formatDate(exam.created_at)}</span>
                  <span className="rounded-full border border-hairline bg-white px-3 py-1 text-[12px] font-medium text-ink-48">
                    {exam.status === "completed" ? `${exam.scaled_score ?? "-"} / 200` : "In progress"}
                  </span>
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </section>
    );
  }

  if (activeExam.exam.status === "completed") {
    const result = activeExam.result || {};
    const breakdown = result.breakdown || [];
    return (
      <section className="space-y-6">
        <TestSummary test={test} questions={questions} modeLabel={`Mock exam · ${partLabel(activeExam.exam.selected_part)}`} />
        <section className="rounded-[18px] bg-tile-1 p-10 text-center text-white">
          <div className="text-[14px] font-semibold uppercase tracking-tight text-white/60">Scaled Score</div>
          <div className="mt-1 text-[56px] font-semibold leading-[1.07] tracking-tight">
            {result.scaled_score ?? "-"}
            <span className="text-[28px] font-normal text-action-dark"> / 200</span>
          </div>
          <div className="mt-2 text-[17px] text-white/80">
            Raw score: {result.raw_score ?? "-"} / {result.max_raw ?? "-"}
          </div>
          <div className="mt-1 inline-flex items-center gap-1.5 text-[15px] text-white/80">
            Time taken:
            <ExamTimer startedAt={activeExam.exam.created_at} endedAt={activeExam.exam.completed_at} />
          </div>
        </section>

        <section className={`${CARD} p-5 sm:p-6`}>
          <h3 className="mb-3 text-[21px] font-semibold tracking-tight text-ink">Score breakdown</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-[15px]">
              <thead>
                <tr className="border-b border-hairline text-left text-ink-48">
                  <th className="pb-2 pr-3 font-semibold">Question</th>
                  <th className="pb-2 pr-3 font-semibold">Part</th>
                  <th className="pb-2 pr-3 font-semibold">Practice score</th>
                  <th className="pb-2 pr-3 font-semibold">Converted</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((item) => {
                  const question = questions.find((q) => q.question_number === item.question_number);
                  const part = question ? partForQuestion(question, parts) : null;
                  return (
                    <tr key={item.question_number} className="border-b border-divider last:border-0">
                      <td className="py-2.5 pr-3 font-semibold text-ink">Question {item.question_number}</td>
                      <td className="py-2.5 pr-3 text-ink-48">{part ? partName(part) : "-"}</td>
                      <td className="py-2.5 pr-3 text-ink-48">{item.score_10 ?? "-"} / 10</td>
                      <td className="py-2.5 pr-3 font-semibold text-action">
                        {item.converted_score} / {item.max_score}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-[21px] font-semibold tracking-tight text-ink">Feedback</h3>
          {(activeExam.attempts || []).map((attempt) => {
            const question = questions.find((q) => q.question_number === attempt.question_number);
            if (!question) return null;
            return (
              <article key={attempt.id} className={`${CARD} p-4`}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <strong className="text-[15px] font-semibold text-ink">Question {attempt.question_number}</strong>
                  <span className="rounded-full border border-hairline bg-white px-3 py-1 text-[12px] text-ink-48">
                    {attempt.converted_score} / {attempt.max_score}
                  </span>
                </div>
                <div className="mb-2 text-[12px] text-ink-48">Practice score: {attempt.score_10 ?? "-"} / 10</div>
                <ScoreResult
                  score={{
                    state: attempt.score_state,
                    text: attempt.score_text,
                  }}
                />
              </article>
            );
          })}
        </section>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={resetToSetup}
            className={BTN_PRIMARY}
          >
            Start New Mock Exam
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <TestSummary test={test} questions={questions} modeLabel={`Mock exam · ${partLabel(activeExam.exam.selected_part)}`} />
      <div className="sticky top-[52px] z-10 rounded-[18px] border border-hairline bg-parchment/80 p-3 backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-[15px] text-ink-48">
            <strong className="text-ink">{questions.length}</strong> question(s) · Drafts are saved automatically
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ExamTimer startedAt={activeExam.exam.created_at} />
            <button
              type="button"
              disabled={submitting}
              onClick={handleSubmit}
              className={`${BTN_PRIMARY} !text-[14px] disabled:opacity-70`}
            >
              {submitting ? "Scoring..." : "Complete & Score"}
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={onLeave}
              className={`${BTN_UTILITY} disabled:opacity-70`}
            >
              Leave exam
            </button>
          </div>
        </div>
      </div>

      {submitting ? (
        <section className="rounded-[18px] border border-action/30 bg-parchment p-5">
          <h3 className="mb-2 text-[14px] font-semibold uppercase tracking-tight text-ink">Scoring progress</h3>
          <div className="mb-3 text-[15px] text-ink-80">
            {scoringProgress.current
              ? `Scoring Question ${scoringProgress.current} of ${scoringProgress.total}`
              : `Preparing to score ${scoringProgress.total} question(s)...`}
          </div>
          <div className="space-y-1.5">
            {questions.map((question) => {
              const state = scoringProgress.status[question.question_number] || "pending";
              const message = scoringProgress.messages[question.question_number] || "";
              const stateClass =
                state === "done"
                  ? "text-action"
                  : state === "error"
                  ? "text-red-700"
                  : state === "scoring"
                  ? "text-ink-80"
                  : "text-ink-48";
              return (
                <div key={question.question_number} className="flex items-center gap-2 text-[14px]">
                  <span className={`min-w-[110px] font-semibold ${stateClass}`}>
                    Question {question.question_number}
                  </span>
                  <span className={`flex-1 truncate ${stateClass}`}>{message || state}</span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {questions.length ? (
        questions.map((question, index) => (
          <QuestionCard
            key={question.id}
            question={question}
            index={index}
            parts={parts}
            draft={getDraft(question)}
            attempts={getAttempts(question)}
            isScoring={scoringProgress.current === question.question_number && submitting}
            allowScoring={false}
            onDraftChange={handleDraftChange}
            onScore={() => {}}
            onClear={handleClear}
            onActivate={() => {}}
            saveLabel="Draft saved to mock exam"
          />
        ))
      ) : (
        <EmptyState>No questions found for this part.</EmptyState>
      )}

      <div className="rounded-[18px] border border-hairline bg-white p-3">
        <button
          type="button"
          disabled={submitting}
          onClick={handleSubmit}
          className={`${BTN_PRIMARY} w-full disabled:opacity-70`}
        >
          {submitting ? "Scoring..." : "Complete & Score"}
        </button>
      </div>
    </section>
  );
};
