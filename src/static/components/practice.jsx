window.TW.TestSummary = function TestSummary({ test, questions, modeLabel }) {
  const { PILL_CLASS } = window.TW.classes;
  return (
    <section className="mb-3 rounded-lg border border-slate-200 bg-white px-2.5 py-3.5">
      <h2 className="mb-2.5 text-2xl font-extrabold leading-tight">{test.title}</h2>
      <a className="font-semibold text-teal-700 no-underline hover:underline" href={test.url} target="_blank" rel="noreferrer">
        Open on Study4
      </a>
      <div className="mt-2.5 flex flex-wrap gap-2">
        <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} minutes</span>
        <span className={PILL_CLASS}>{modeLabel}</span>
        <span className={PILL_CLASS}>{questions.length} questions shown</span>
        <span className={PILL_CLASS}>{test.access_status}</span>
      </div>
    </section>
  );
};

window.TW.PartTabs = function PartTabs({ payload, selectedPart, onSelectPart, onScoreVisible, onClearVisible, scoringVisible }) {
  const { PART_BUTTON_BASE, PART_BUTTON_ACTIVE } = window.TW.classes;
  const { partName } = window.TW;
  const parts = payload.parts || [];

  return (
    <section className="mb-3 flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-2 max-[860px]:flex-col max-[860px]:items-stretch">
      <div className="flex flex-wrap gap-1.5">
        <button
          className={`${PART_BUTTON_BASE} ${selectedPart === "all" ? PART_BUTTON_ACTIVE : ""}`}
          type="button"
          onClick={() => onSelectPart("all")}
        >
          Full test
        </button>
        {parts.map((part) => (
          <button
            key={part.study4_part_id}
            className={`${PART_BUTTON_BASE} ${String(part.sort_order) === String(selectedPart) ? PART_BUTTON_ACTIVE : ""}`}
            type="button"
            onClick={() => onSelectPart(String(part.sort_order))}
          >
            {partName(part)}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap justify-end gap-1.5 max-[860px]:justify-start">
        <button
          className="min-h-9 rounded-md border border-teal-700 bg-teal-700 px-3 py-1.5 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-wait disabled:opacity-70"
          type="button"
          disabled={scoringVisible}
          onClick={onScoreVisible}
        >
          {scoringVisible ? "Scoring..." : "Score visible drafts"}
        </button>
        <button
          className="min-h-9 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 hover:border-teal-700 hover:bg-teal-50 hover:text-teal-950"
          type="button"
          onClick={onClearVisible}
        >
          Clear visible drafts
        </button>
      </div>
    </section>
  );
};

function PromptHtml({ html, text }) {
  if (html) {
    return (
      <div
        className="[&_img]:mb-2.5 [&_img]:block [&_img]:h-auto [&_img]:max-w-[min(100%,520px)] [&_img]:rounded-md [&_img]:border [&_img]:border-slate-200 [&_img]:bg-white [&_p]:mb-2.5 [&_p:last-child]:mb-0"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  return <p className="mb-2.5 last:mb-0">{text}</p>;
}

window.TW.AnswerBox = function AnswerBox({ question, part, draft, isScoring, onDraftChange, onScore, onClear }) {
  const { countWords } = window.TW;
  const partHeight = part?.sort_order === 2 ? "min-h-[180px]" : part?.sort_order === 3 ? "min-h-[260px]" : "min-h-28";

  return (
    <div className="min-w-0">
      <div className="mb-1.5 flex items-center justify-between gap-3 text-sm text-slate-500">
        <strong>Your response</strong>
        <span>{countWords(draft)} words · {draft.length} chars</span>
      </div>
      <textarea
        className={`w-full resize-y rounded-lg border border-slate-200 bg-white px-2 py-2.5 font-sans leading-normal text-slate-900 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-50 ${partHeight}`}
        value={draft}
        spellCheck="false"
        onChange={(event) => onDraftChange(question, event.target.value)}
      />
      <div className="mt-1.5 flex items-center justify-between gap-3 text-xs text-slate-500">
        <span>Draft saved locally</span>
        <span>
          <button
            className="bg-transparent p-0 text-xs font-bold text-teal-700 hover:underline disabled:cursor-wait disabled:opacity-70"
            type="button"
            disabled={isScoring}
            onClick={() => onScore(question)}
          >
            {isScoring ? "Scoring..." : "Save & score"}
          </button>
          {" · "}
          <button className="bg-transparent p-0 text-xs font-bold text-teal-700 hover:underline" type="button" onClick={() => onClear(question)}>
            Clear
          </button>
        </span>
      </div>
    </div>
  );
};

function FeedbackPanel({ question, attempts }) {
  const { countWords, ScoreResult } = window.TW;
  const storageKey = `toeic-sw-writing-feedback-collapsed:${question.study4_test_id}:${question.question_number}`;
  const [isCollapsed, setIsCollapsed] = React.useState(() => localStorage.getItem(storageKey) === "1");
  const isStreaming = attempts.some((attempt) => attempt.score?.state === "streaming");

  React.useEffect(() => {
    if (!isStreaming || !isCollapsed) return;
    localStorage.removeItem(storageKey);
    setIsCollapsed(false);
  }, [isStreaming, isCollapsed, storageKey]);

  function toggleCollapsed() {
    const nextCollapsed = !isCollapsed;
    if (nextCollapsed) {
      localStorage.setItem(storageKey, "1");
    } else {
      localStorage.removeItem(storageKey);
    }
    setIsCollapsed(nextCollapsed);
  }

  return (
    <section className="mt-3 rounded-lg border border-slate-200 bg-slate-50/60 p-2">
      <div className="flex items-center justify-between gap-3 text-sm text-slate-500">
        <strong>AI feedback</strong>
        <div className="flex items-center gap-2">
          <span>{attempts.length} attempts</span>
          <button
            className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-teal-700 hover:border-teal-700 hover:bg-teal-50"
            type="button"
            onClick={toggleCollapsed}
          >
            {isCollapsed ? "Show" : "Hide"}
          </button>
        </div>
      </div>
      {!isCollapsed ? (
        <div className="mt-2">
          {attempts.length ? (
            <div className="space-y-2">
              {attempts.map((attempt, attemptIndex) => (
                <section key={attempt.id} className="rounded-lg border border-slate-200 bg-white">
                  <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-2.5 py-2 text-xs text-slate-500">
                    <strong>Attempt {attemptIndex + 1}</strong>
                    <span>{countWords(attempt.answer)} words · {attempt.answer.length} chars</span>
                  </div>
                  <p className="whitespace-pre-wrap border-b border-slate-200 px-2.5 py-2 text-sm text-slate-700">{attempt.answer}</p>
                  <div className="px-2.5 pb-2">
                    <ScoreResult score={attempt.score} />
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-slate-500">
              Save and score an answer to see feedback here.
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}

window.TW.QuestionCard = function QuestionCard({ question, index, parts, draft, attempts, isScoring, onDraftChange, onScore, onClear, onActivate }) {
  const { AnswerBox, partForQuestion, partName } = window.TW;
  const { PILL_CLASS } = window.TW.classes;
  const assets = Array.isArray(question.asset_urls) ? question.asset_urls : [];
  const part = partForQuestion(question, parts);

  return (
    <article
      id={`question-${question.id}`}
      className="mb-2.5 scroll-mt-20 overflow-hidden rounded-lg border border-slate-200 bg-white"
      onClick={() => onActivate(question)}
      onFocus={() => onActivate(question)}
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-2 py-2.5">
        <strong className="text-[15px] font-extrabold">Question {question.question_number ?? index + 1}</strong>
        <span className={PILL_CLASS}>{partName(part)}</span>
      </div>
      <div className="px-2 py-3 leading-relaxed">
        <div className="grid gap-3 xl:grid-cols-[minmax(300px,1fr)_minmax(300px,1fr)]">
          <div className="min-w-0">
            <PromptHtml html={question.prompt_html} text={question.prompt_text} />
            {assets.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {assets.map((url, assetIndex) => (
                  <a key={url} className="font-semibold text-teal-700 no-underline hover:underline" href={url} target="_blank" rel="noreferrer">
                    Asset {assetIndex + 1}
                  </a>
                ))}
              </div>
            ) : null}
          </div>
          <AnswerBox
            question={question}
            part={part}
            draft={draft}
            isScoring={isScoring}
            onDraftChange={onDraftChange}
            onScore={onScore}
            onClear={onClear}
          />
        </div>
        <FeedbackPanel question={question} attempts={attempts} />
      </div>
    </article>
  );
};
