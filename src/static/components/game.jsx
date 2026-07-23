const { useEffect, useMemo, useState } = React;

function shuffle(arr) {
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

const FOCUS = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-focus focus-visible:ring-offset-2";

function GameOption({ option, index, state, correct, selected, reveal, onPick }) {
  const isCorrect = correct;
  const isWrong = selected && !correct;
  const border =
    state === "answered"
      ? isCorrect
        ? "border-[#34a853]"
        : isWrong
          ? "border-[#ea4335]"
          : "border-hairline opacity-60"
      : "border-hairline hover:border-action";
  return (
    <button
      type="button"
      disabled={state === "answered"}
      onClick={() => onPick(option)}
      className={`group relative flex flex-col overflow-hidden rounded-[18px] border bg-white transition active:scale-[0.98] ${FOCUS} ${border}`}
    >
      <div className="absolute left-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-[rgba(210,210,215,0.64)] text-[12px] font-semibold text-ink backdrop-blur-sm">
        {index + 1}
      </div>
      {option.image?.url ? (
        <div className="aspect-[3/2] w-full overflow-hidden bg-pearl">
          <img
            src={option.image.url}
            alt=""
            loading="lazy"
            className="block h-full w-full object-cover shadow-[3px_5px_30px_rgba(0,0,0,0.22)]"
          />
        </div>
      ) : (
        <div className="flex aspect-[3/2] w-full items-center justify-center bg-pearl text-ink-48">
          <span className="text-[22px] leading-none">♫</span>
        </div>
      )}
      {reveal ? (
        <div className="flex flex-col gap-0.5 px-2.5 py-2 text-left">
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            <span className={`text-[14px] font-semibold ${isCorrect ? "text-[#34a853]" : isWrong ? "text-[#ea4335]" : "text-ink"}`}>
              {option.term}
            </span>
            {option.ipa ? <span className="text-[11px] text-ink-48">{option.ipa}</span> : null}
            {option.part_of_speech ? (
              <span className="rounded-full border border-hairline bg-parchment px-1.5 py-0.5 text-[10px] font-medium text-ink-48">
                {option.part_of_speech}
              </span>
            ) : null}
          </div>
          {option.meaning ? <p className="text-[12px] leading-[1.35] text-ink-80">{option.meaning}</p> : null}
        </div>
      ) : null}
      {state === "answered" && isCorrect ? (
        <div className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-[#34a853] text-[13px] font-bold text-white">✓</div>
      ) : null}
      {state === "answered" && isWrong ? (
        <div className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-[#ea4335] text-[13px] font-bold text-white">✕</div>
      ) : null}
    </button>
  );
}

window.TW.GameScreen = function GameScreen({ onLeave, onGoRevision, onLogin, isGuest }) {
  const { listRevision, setRevisionReviewed, speak, EmptyState } = window.TW;
  const { BTN_PRIMARY, BTN_UTILITY, BTN_GHOST, CARD } = window.TW.classes;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [allItems, setAllItems] = useState([]);

  const [mode, setMode] = useState("new"); // "new" (not reviewed) | "reviewed"
  const [accent, setAccent] = useState("us");

  const [phase, setPhase] = useState("idle"); // idle | playing | answered | done
  const [queue, setQueue] = useState([]);
  const [round, setRound] = useState(0);
  const [options, setOptions] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [correctCount, setCorrectCount] = useState(0);

  const imageItems = useMemo(
    () => allItems.filter((it) => it.image && it.image.url),
    [allItems]
  );
  const newItems = useMemo(() => imageItems.filter((it) => !it.reviewed), [imageItems]);
  const reviewedItems = useMemo(() => imageItems.filter((it) => it.reviewed), [imageItems]);
  const pool = mode === "new" ? newItems : reviewedItems;

  useEffect(() => {
    if (isGuest) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const all = await listRevision();
        if (cancelled) return;
        setAllItems(all);
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load revision list");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isGuest]);

  function setupRound(poolArr, roundIndex) {
    const current = poolArr[roundIndex];
    const distractors = shuffle(
      poolArr.filter((_, i) => i !== roundIndex)
    ).slice(0, Math.min(3, poolArr.length - 1));
    const opts = shuffle([current, ...distractors]);
    setOptions(opts);
    setSelectedItem(null);
    setPhase("playing");
    speak(current.term, accent);
  }

  function buildQueue(sourcePool) {
    const shuffled = shuffle(sourcePool);
    setQueue(shuffled);
    setRound(0);
    setCorrectCount(0);
    setPhase("playing");
    setupRound(shuffled, 0);
  }

  function startGame() {
    buildQueue(pool);
  }

  function startMode(targetMode) {
    setMode(targetMode);
    buildQueue(targetMode === "new" ? newItems : reviewedItems);
  }

  function handlePick(option) {
    if (phase !== "playing") return;
    const current = queue[round];
    setSelectedItem(option);
    setPhase("answered");
    const correct = !!(option && option.id === current.id);
    if (correct) {
      setCorrectCount((c) => c + 1);
      if (mode === "new" && current && !current.reviewed) {
        setAllItems((prev) =>
          prev.map((it) => (it.id === current.id ? { ...it, reviewed: true } : it))
        );
        setRevisionReviewed(current.id, true).catch(() => {});
      }
    }
  }

  function nextRound() {
    const next = round + 1;
    if (next >= queue.length) {
      setPhase("done");
      return;
    }
    setRound(next);
    setupRound(queue, next);
  }

  function pickAccent(ac) {
    setAccent(ac);
    const cur = queue[round];
    if (cur) speak(cur.term, ac);
  }

  // keyboard: 1-4 to pick, Enter/Space to advance
  useEffect(() => {
    if (phase === "idle" || phase === "done") return;
    function onKey(e) {
      if (phase === "playing") {
        const n = parseInt(e.key, 10);
        if (n >= 1 && n <= options.length) handlePick(options[n - 1]);
      } else if (phase === "answered") {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          nextRound();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, options, queue, round]);

  const current = queue[round];
  const isCorrect = phase === "answered" && selectedItem && selectedItem.id === current?.id;

  if (isGuest) {
    return (
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">Listening game</h2>
          <p className="text-[17px] leading-[1.47] text-ink-48">Hear a word, pick the matching picture.</p>
        </div>
        <div className={`${CARD} p-10 text-center`}>
          <p className="mb-4 text-[17px] leading-[1.47] text-ink-80">Log in to play with your saved vocabulary.</p>
          <button type="button" onClick={onLogin} className={BTN_PRIMARY}>Login with Gmail</button>
        </div>
      </section>
    );
  }

  const tabClass = (active) =>
    `shrink-0 rounded-full px-3 py-1 text-[12px] font-medium transition active:scale-95 ${
      active
        ? "border border-action bg-parchment text-ink"
        : "border border-hairline bg-white text-ink-48 hover:text-ink"
    }`;

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-2">
          <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">Listening game</h2>
          <p className="text-[17px] leading-[1.47] text-ink-48">Listen to the word and pick the matching picture.</p>
        </div>
        <button type="button" onClick={onLeave} className={`${BTN_UTILITY}`}>← Back to tests</button>
      </div>

      {error ? <EmptyState error>{error}</EmptyState> : null}

      {!error && loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="overflow-hidden rounded-[18px] border border-hairline bg-white">
              <div className="tw-skel aspect-[3/2] w-full" />
            </div>
          ))}
        </div>
      ) : null}

      {!error && !loading && imageItems.length < 4 ? (
        <div className={`${CARD} p-8 text-center`}>
          <p className="mb-5 text-[17px] leading-[1.47] text-ink-80">
            Save at least 4 vocabs <span className="text-ink-48">(with images)</span> to your revision list, then come back to play.
          </p>
          <button type="button" onClick={onGoRevision} className={BTN_PRIMARY}>Go to revision</button>
        </div>
      ) : null}

      {!error && !loading && imageItems.length >= 4 ? (
        <>
          {phase === "idle" || phase === "done" ? (
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={() => setMode("new")} className={tabClass(mode === "new")}>
                New ({newItems.length})
              </button>
              <button type="button" onClick={() => setMode("reviewed")} className={tabClass(mode === "reviewed")}>
                Reviewed ({reviewedItems.length})
              </button>
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2 rounded-[18px] border border-hairline bg-parchment px-4 py-2.5">
            <div className="flex items-center gap-2 text-[14px] text-ink-80">
              {phase === "playing" || phase === "answered" ? (
                <>
                  <span className="font-semibold text-ink">Round {round + 1} / {queue.length}</span>
                  <span className="text-ink-48">·</span>
                  <span className="text-ink-48">Score: {correctCount}</span>
                </>
              ) : (
                <span>
                  {pool.length} {mode === "new" ? "new" : "reviewed"} vocab{pool.length === 1 ? "" : "s"} ready
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-ink-48">Accent</span>
              <button
                type="button"
                onClick={() => pickAccent("us")}
                title={phase === "playing" || phase === "answered" ? "Hear the word again (US)" : "Use US accent"}
                className={`rounded-full border px-3 py-1 text-[14px] font-normal transition active:scale-95 ${accent === "us" ? "border-action-focus border-2 bg-white text-ink" : "border-hairline bg-white text-ink-48 hover:text-ink"}`}
              >US</button>
              <button
                type="button"
                onClick={() => pickAccent("uk")}
                title={phase === "playing" || phase === "answered" ? "Hear the word again (UK)" : "Use UK accent"}
                className={`rounded-full border px-3 py-1 text-[14px] font-normal transition active:scale-95 ${accent === "uk" ? "border-action-focus border-2 bg-white text-ink" : "border-hairline bg-white text-ink-48 hover:text-ink"}`}
              >UK</button>
            </div>
          </div>

          {phase === "idle" && pool.length >= 4 ? (
            <div className={`${CARD} p-8 text-center`}>
              <p className="mb-5 text-[17px] leading-[1.47] text-ink-80">
                You'll hear a word. Pick the picture that matches it. Press <kbd className="rounded border border-hairline bg-white px-1 text-[12px]">1</kbd>–<kbd className="rounded border border-hairline bg-white px-1 text-[12px]">4</kbd> or click.
              </p>
              <button type="button" onClick={startGame} className={BTN_PRIMARY}>Start game</button>
            </div>
          ) : null}

          {phase === "idle" && pool.length < 4 ? (
            <div className={`${CARD} p-8 text-center`}>
              {mode === "new" ? (
                <>
                  <p className="mb-5 text-[17px] leading-[1.47] text-ink-80">
                    {reviewedItems.length > 0
                      ? "You've reviewed all your saved words. Practice them in the Reviewed tab."
                      : "You need at least 4 unreviewed vocabs (with images) to play. Save more to revision, then come back."}
                  </p>
                  {reviewedItems.length >= 4 ? (
                    <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                      <button type="button" onClick={() => startMode("reviewed")} className={BTN_PRIMARY}>Practice reviewed</button>
                      <button type="button" onClick={onGoRevision} className={BTN_GHOST}>Back to revision</button>
                    </div>
                  ) : (
                    <div className="mt-6">
                      <button type="button" onClick={onGoRevision} className={BTN_GHOST}>Back to revision</button>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="mb-5 text-[17px] leading-[1.47] text-ink-80">
                    No reviewed words yet. Play the New game and answer correctly to mark words as reviewed, then practice them here.
                  </p>
                  <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                    {newItems.length >= 4 ? (
                      <button type="button" onClick={() => startMode("new")} className={BTN_PRIMARY}>Play new words</button>
                    ) : null}
                    <button type="button" onClick={onGoRevision} className={BTN_GHOST}>Back to revision</button>
                  </div>
                </>
              )}
            </div>
          ) : null}

          {phase === "done" ? (
            <div className={`${CARD} p-8 text-center`}>
              <p className="text-[14px] text-ink-48">Final score</p>
              <p className="my-2 text-[40px] font-semibold leading-[1.1] text-ink">
                {correctCount} / {queue.length}
              </p>
              {pool.length < 4 ? (
                <p className="mb-4 text-[14px] leading-[1.43] text-ink-80">
                  {mode === "new"
                    ? "All caught up — these words are now reviewed. Switch to Reviewed above to practice them."
                    : "Not enough reviewed words to continue. Switch to New above."}
                </p>
              ) : null}
              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                {pool.length >= 4 ? (
                  <button type="button" onClick={startGame} className={BTN_PRIMARY}>Play again</button>
                ) : null}
                <button type="button" onClick={onGoRevision} className={BTN_GHOST}>Back to revision</button>
              </div>
            </div>
          ) : null}

          {phase === "playing" || phase === "answered" ? (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {options.map((opt, i) => (
                  <GameOption
                    key={opt.id}
                    option={opt}
                    index={i}
                    state={phase}
                    correct={opt.id === current?.id}
                    selected={!!selectedItem && selectedItem.id === opt.id}
                    reveal={phase === "answered" && isCorrect}
                    onPick={handlePick}
                  />
                ))}
              </div>

              {phase === "answered" ? (
                <div className={`rounded-[18px] border p-4 bg-white ${isCorrect ? "border-[#34a853]" : "border-[#ea4335]"}`}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className={`text-[17px] font-semibold ${isCorrect ? "text-[#34a853]" : "text-[#ea4335]"}`}>
                        {isCorrect ? "Correct!" : `Wrong — it was "${current?.term}"`}
                      </p>
                      {current?.ipa ? <span className="text-[12px] text-ink-48"> {current.ipa}</span> : null}
                      {current?.part_of_speech ? (
                        <span className="ml-1 rounded-full border border-hairline bg-parchment px-1.5 py-0.5 text-[10px] font-medium text-ink-48">{current.part_of_speech}</span>
                      ) : null}
                      {current?.meaning ? <p className="mt-1 text-[14px] leading-[1.43] text-ink-80">{current.meaning}</p> : null}
                      {current?.vietnamese_meaning ? <p className="text-[14px] font-medium text-action"><span className="text-ink-48">VN:</span> {current.vietnamese_meaning}</p> : null}
                      {current?.example ? (
                        <blockquote
                          className="mt-1.5 cursor-pointer border-l-2 border-action bg-parchment py-1 pl-2 pr-1.5 text-[13px] leading-relaxed text-ink-80 hover:bg-divider active:scale-[0.99]"
                          title="Hear example"
                          onClick={() => speak(current.example, accent)}
                        >
                          {current.example}
                        </blockquote>
                      ) : null}
                    </div>
                    <button type="button" onClick={nextRound} className={BTN_PRIMARY}>
                      {round + 1 >= queue.length ? "See results" : "Next →"}
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}
    </section>
  );
};
