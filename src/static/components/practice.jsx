window.TW.TestSummary = function TestSummary({ test, questions, modeLabel }) {
  const { PILL_CLASS, LINK, CARD } = window.TW.classes;
  return (
    <section className={`${CARD} mb-3 p-4 sm:p-6`}>
      <h2 className="mb-2 text-[34px] font-semibold leading-[1.1] tracking-tight text-ink">{test.title}</h2>
      <a className={`font-normal ${LINK}`} href={test.url} target="_blank" rel="noreferrer">
        Open on Study4
      </a>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className={PILL_CLASS}>{test.duration_minutes ?? "-"} minutes</span>
        <span className={PILL_CLASS}>{modeLabel}</span>
        <span className={PILL_CLASS}>{questions.length} questions shown</span>
        <span className={PILL_CLASS}>{test.access_status}</span>
      </div>
    </section>
  );
};

window.TW.PartTabs = function PartTabs({ payload, selectedPart, onSelectPart, onScoreVisible, onClearVisible, scoringVisible, allowScoring = true, onLogin }) {
  const { PART_BUTTON_BASE, PART_BUTTON_ACTIVE, BTN_PRIMARY, BTN_UTILITY } = window.TW.classes;
  const { partName } = window.TW;
  const parts = payload.parts || [];

  return (
    <section className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[18px] border border-hairline bg-parchment p-2 max-[860px]:flex-col max-[860px]:items-stretch">
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
      <div className="flex flex-wrap justify-end gap-2 max-[860px]:justify-start">
        {allowScoring ? (
          <button
            className={`${BTN_PRIMARY} !px-4 !py-1.5 !text-[14px] disabled:opacity-70`}
            type="button"
            disabled={scoringVisible}
            onClick={onScoreVisible}
          >
            {scoringVisible ? "Scoring..." : "Score visible drafts"}
          </button>
        ) : (
          <button
            className={`${BTN_UTILITY} border-action text-action`}
            type="button"
            onClick={onLogin}
          >
            Login to score
          </button>
        )}
        <button
          className={`${BTN_UTILITY}`}
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
        className="[&_img]:mb-2.5 [&_img]:block [&_img]:h-auto [&_img]:max-w-[min(100%,520px)] [&_img]:rounded-[8px] [&_img]:border [&_img]:border-hairline [&_img]:bg-white [&_p]:mb-2.5 [&_p:last-child]:mb-0"
        dangerouslySetInnerHTML={{ __html: window.TW.sanitizeHtml(html) }}
      />
    );
  }

  return <p className="mb-2.5 last:mb-0">{text}</p>;
}

window.TW.AnswerBox = function AnswerBox({
  question,
  part,
  draft,
  isScoring,
  allowScoring = true,
  onDraftChange,
  onScore,
  onClear,
  saveLabel = "Draft saved to your account",
  onLogin,
  canViewVocab = false,
  onViewVocab,
}) {
  const { countWords } = window.TW;
  const { LINK } = window.TW.classes;
  const partHeight = part?.sort_order === 2 ? "min-h-[180px]" : part?.sort_order === 3 ? "min-h-[260px]" : "min-h-28";

  return (
    <div className="min-w-0">
      <div className="mb-1.5 flex items-center justify-between gap-3 text-[14px] text-ink-48">
        <strong className="font-semibold text-ink">Your response</strong>
        <span>{countWords(draft)} words · {draft.length} chars</span>
      </div>
      <textarea
        className={`w-full resize-y rounded-[11px] border border-hairline bg-white px-3 py-2.5 font-sans text-[15px] leading-normal text-ink focus:border-action focus:outline-none focus:ring-2 focus:ring-action-focus/30 ${partHeight}`}
        value={draft}
        spellCheck="false"
        onChange={(event) => onDraftChange(question, event.target.value)}
      />
      <div className="mt-1.5 flex items-center justify-between gap-3 text-[12px] text-ink-48">
        <span>{saveLabel}</span>
        <span>
          {allowScoring ? (
            <>
              <button
                className={`p-0 text-[12px] font-semibold ${LINK} disabled:opacity-70`}
                type="button"
                disabled={isScoring}
                onClick={() => onScore(question)}
              >
                {isScoring ? "Scoring..." : "Save & score"}
              </button>
              {" · "}
              {canViewVocab && onViewVocab ? (
                <>
                  <button
                    className={`p-0 text-[12px] font-semibold ${LINK}`}
                    type="button"
                    onClick={onViewVocab}
                  >
                    Vocab + images
                  </button>
                  {" · "}
                </>
              ) : null}
            </>
          ) : onLogin ? (
            <>
              <button
                className={`p-0 text-[12px] font-semibold ${LINK}`}
                type="button"
                onClick={onLogin}
              >
                Login to score
              </button>
              {" · "}
            </>
          ) : null}
          <button className={`p-0 text-[12px] font-semibold ${LINK}`} type="button" onClick={() => onClear(question)}>
            Clear
          </button>
        </span>
      </div>
    </div>
  );
};

function FeedbackPanel({ question, attempts }) {
  const { countWords, ScoreResult } = window.TW;
  const { CARD } = window.TW.classes;
  const storageKey = `toeic-sw-writing-feedback-collapsed:${question.study4_test_id}:${question.question_number}`;
  const [isCollapsed, setIsCollapsed] = React.useState(() => localStorage.getItem(storageKey) !== "0");
  const attempt = attempts[attempts.length - 1];
  const isStreaming = attempt?.score?.state === "streaming";

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
    <section className="mt-3 rounded-[18px] border border-hairline bg-parchment p-3">
      <div className="flex items-center justify-between gap-3 text-[14px] text-ink-48">
        <strong className="font-semibold text-ink">AI feedback</strong>
        <button
          className="rounded-full border border-hairline bg-white px-3 py-1 text-[12px] font-medium text-ink active:scale-95"
          type="button"
          onClick={toggleCollapsed}
        >
          {isCollapsed ? "Show" : "Hide"}
        </button>
      </div>
      {!isCollapsed ? (
        <div className="mt-2">
          {attempt ? (
            <section className={`${CARD}`}>
              <div className="flex items-start justify-between gap-3 border-b border-hairline px-3 py-2 text-[12px] text-ink-48">
                <strong className="font-semibold text-ink">Latest response</strong>
                <span>{countWords(attempt.answer)} words · {attempt.answer.length} chars</span>
              </div>
              <p className="whitespace-pre-wrap border-b border-hairline px-3 py-2 text-[15px] text-ink-80">{attempt.answer}</p>
              <div className="px-3 pb-3">
                <ScoreResult score={attempt.score} />
              </div>
            </section>
          ) : (
            <div className="rounded-[18px] border border-dashed border-hairline bg-white p-4 text-[15px] text-ink-48">
              Save and score an answer to see feedback here.
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}

window.TW.QuestionCard = function QuestionCard({
  question,
  index,
  parts,
  draft,
  attempts,
  isScoring,
  allowScoring = true,
  onDraftChange,
  onScore,
  onClear,
  onActivate,
  saveLabel,
  onLogin,
  revisionSavedKeys,
  onToggleRevision,
}) {
  const { AnswerBox, partForQuestion, partName, VocabSection } = window.TW;
  const { PILL_CLASS, CARD, LINK } = window.TW.classes;
  const assets = Array.isArray(question.asset_urls) ? question.asset_urls : [];
  const part = partForQuestion(question, parts);
  const [vocabOpen, setVocabOpen] = React.useState(false);
  const latestAttempt = attempts[attempts.length - 1];
  const canViewVocab = allowScoring;

  return (
    <article
      id={`question-${question.id}`}
      className="mb-2.5 scroll-mt-20 overflow-hidden rounded-[18px] border border-hairline bg-white"
      onClick={() => onActivate(question)}
      onFocus={() => onActivate(question)}
    >
      <div className="flex items-center justify-between gap-3 border-b border-hairline bg-parchment px-3 py-2.5">
        <strong className="text-[15px] font-semibold text-ink">Question {question.question_number ?? index + 1}</strong>
        <span className={PILL_CLASS}>{partName(part)}</span>
      </div>
      <div className="px-3 py-4 leading-relaxed">
        <div className="grid gap-3 xl:grid-cols-[minmax(300px,1fr)_minmax(300px,1fr)]">
          <div className="min-w-0">
            <PromptHtml html={question.prompt_html} text={question.prompt_text} />
            {assets.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {assets.map((url, assetIndex) => (
                  <a key={url} className={`font-normal ${LINK}`} href={url} target="_blank" rel="noreferrer">
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
            allowScoring={allowScoring}
            onDraftChange={onDraftChange}
            onScore={onScore}
            onClear={onClear}
            saveLabel={saveLabel}
            onLogin={onLogin}
            canViewVocab={canViewVocab}
            onViewVocab={() => setVocabOpen(true)}
          />
        </div>
        <FeedbackPanel question={question} attempts={attempts} />
        {canViewVocab ? (
          <VocabSection
            question={question}
            allowScoring={allowScoring}
            attempt={latestAttempt}
            open={vocabOpen}
            onOpenChange={setVocabOpen}
            savedKeys={revisionSavedKeys}
            onToggleSave={onToggleRevision}
          />
        ) : null}
      </div>
    </article>
  );
};
