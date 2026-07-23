window.TW.VocabTermCell = function VocabTermCell({ item, saved = false, onToggleSave }) {
  const { speak } = window.TW;
  const image = item.image;
  const vn = item.vietnamese_meaning;

  return (
    <div className="flex flex-col overflow-hidden rounded-[10px] border border-hairline bg-white">
      <div className="relative block w-full overflow-hidden bg-pearl">
        {image ? (
          <img
            src={image.url}
            alt={image.alt || item.term}
            loading="lazy"
            className="block h-auto w-full object-cover"
          />
        ) : (
          <div className="flex aspect-[3/2] w-full items-center justify-center bg-pearl text-ink-48">
            <span className="text-[22px] leading-none">♫</span>
          </div>
        )}
        {onToggleSave ? (
          <button
            type="button"
            className={`absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-full border text-[14px] font-semibold leading-none shadow-sm transition active:scale-95 ${
              saved
                ? "border-action bg-action text-white"
                : "border-hairline bg-white/90 text-ink-48 backdrop-blur hover:bg-white hover:text-ink"
            }`}
            title={saved ? "Saved to revision" : "Add to revision"}
            onClick={() => onToggleSave(item)}
          >
            {saved ? "✓" : "+"}
          </button>
        ) : null}
      </div>
      <div className="flex flex-col gap-1.5 p-2.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className="text-[15px] font-semibold text-ink">{item.term}</span>
          {item.ipa ? <span className="text-[12px] text-ink-48">{item.ipa}</span> : null}
          {item.part_of_speech ? (
            <span className="rounded-full border border-hairline bg-parchment px-1.5 py-0.5 text-[10px] font-medium text-ink-48">
              {item.part_of_speech}
            </span>
          ) : null}
          <span className="ml-auto flex items-center gap-1">
            <button
              type="button"
              className="flex h-6 min-w-6 items-center justify-center rounded-full border border-hairline bg-white px-1 text-[10px] font-semibold leading-none text-ink-48 active:scale-95 hover:bg-parchment hover:text-ink"
              title={`Hear "${item.term}" (US)`}
              onClick={() => speak(item.term, "us")}
            >
              US
            </button>
            <button
              type="button"
              className="flex h-6 min-w-6 items-center justify-center rounded-full border border-hairline bg-white px-1 text-[10px] font-semibold leading-none text-ink-48 active:scale-95 hover:bg-parchment hover:text-ink"
              title={`Hear "${item.term}" (UK)`}
              onClick={() => speak(item.term, "uk")}
            >
              UK
            </button>
          </span>
        </div>
        {item.meaning ? (
          <p className="text-[13px] leading-relaxed text-ink-80">{item.meaning}</p>
        ) : null}
        {Array.isArray(item.synonyms) && item.synonyms.length ? (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-[10px] font-medium uppercase tracking-wide text-ink-48">syn:</span>
            {item.synonyms.map((s, i) => (
              <span
                key={i}
                className="rounded-full border border-hairline bg-parchment px-1.5 py-0.5 text-[11px] text-ink-80"
              >
                {s}
              </span>
            ))}
          </div>
        ) : null}
        {item.example ? (
          <blockquote
            className="cursor-pointer border-l-2 border-action bg-parchment py-1 pl-2 pr-1.5 text-[12px] leading-relaxed text-ink-80 hover:bg-divider active:scale-[0.99]"
            title={`Hear example (US)`}
            onClick={() => speak(item.example, "us")}
          >
            {item.example}
          </blockquote>
        ) : null}
        {vn ? (
          <p className="text-[12px] font-medium text-action">
            <span className="text-ink-48">VN:</span> {vn}
          </p>
        ) : null}
      </div>
    </div>
  );
};

window.TW.QuestionPicture = function QuestionPicture({ question }) {
  const assets = Array.isArray(question?.asset_urls) ? question.asset_urls : [];
  const promptText = question?.prompt_text || "";
  const promptHtml = question?.prompt_html || "";

  return (
    <div className="flex h-full flex-col gap-3">
      <strong className="text-[12px] font-semibold uppercase tracking-wide text-ink-48">Question</strong>
      {assets.length ? (
        <div className="flex flex-wrap gap-2">
          {assets.map((url, i) => (
            <a
              key={url}
              className="block overflow-hidden rounded-[8px] border border-hairline bg-white"
              href={url}
              target="_blank"
              rel="noreferrer"
            >
              <img src={url} alt={`Question asset ${i + 1}`} loading="lazy" className="block h-auto max-w-full object-cover" />
            </a>
          ))}
        </div>
      ) : null}
      {promptHtml ? (
        <div
          className="[&_img]:hidden [&_p]:mb-1.5 text-[13px] leading-relaxed text-ink-80"
          dangerouslySetInnerHTML={{ __html: promptHtml }}
        />
      ) : <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-80">{promptText}</p>}
    </div>
  );
};

window.TW.VocabModal = function VocabModal({ open, vocab, loading, error, onClose, onRegenerate, regenerating, question, savedKeys, onToggleSave }) {
  const { BTN_UTILITY: Btn } = window.TW.classes;
  const { VocabTermCell: TermCell, QuestionPicture, VocabGridSkeleton } = window.TW;
  const categories = vocab?.categories || [];

  const [catIndex, setCatIndex] = React.useState(0);

  React.useEffect(() => {
    if (open) {
      setCatIndex(0);
    }
  }, [open, vocab]);

  React.useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        setCatIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "ArrowRight") {
        setCatIndex((i) => Math.min(categories.length - 1, i + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose, categories.length]);

  if (!open) return null;

  const current = categories[catIndex];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[90dvh] w-[90vw] flex-col overflow-hidden rounded-[14px] bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline bg-parchment px-4 py-3">
          <div className="flex items-center gap-2">
            <strong className="text-[17px] font-semibold text-ink">Vocab + images</strong>
            {vocab?.topic ? (
              <span className="inline-flex items-center rounded-full border border-hairline bg-white px-3 py-1 text-[12px] font-medium tracking-wide text-ink-80">
                {vocab.topic}
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            {vocab && onRegenerate ? (
              <button
                type="button"
                className={`${Btn} !text-[12px] disabled:opacity-70`}
                disabled={regenerating}
                onClick={onRegenerate}
              >
                {regenerating ? "Generating..." : "Regenerate"}
              </button>
            ) : null}
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-hairline bg-white text-[16px] text-ink-48 active:scale-95 hover:text-ink"
              title="Close (Esc)"
              onClick={onClose}
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          {question ? (
            <aside className="hidden w-[300px] shrink-0 overflow-auto border-r border-hairline bg-parchment p-3 md:block lg:w-[340px]">
              <QuestionPicture question={question} />
            </aside>
          ) : null}

          <div className="min-w-0 flex-1 overflow-hidden">
          {error ? (
            <div className="flex h-full items-center justify-center p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-[11px] border border-red-200 bg-red-50 p-3 text-[14px] text-red-800">
                <span>{error}</span>
                <button type="button" className={`${Btn} !text-[12px]`} onClick={onRegenerate} disabled={regenerating}>
                  Try again
                </button>
              </div>
            </div>
          ) : loading ? (
            <VocabGridSkeleton />
          ) : categories.length ? (
            <div className="flex h-full flex-col">
              <div className="flex items-center gap-2 border-b border-hairline px-3 py-2">
                <button
                  type="button"
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-hairline bg-white text-ink-48 disabled:opacity-40 active:scale-95"
                  disabled={catIndex === 0}
                  onClick={() => setCatIndex((i) => Math.max(0, i - 1))}
                  title="Previous"
                >
                  ‹
                </button>
                <div className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto py-0.5">
                  {categories.map((c, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setCatIndex(i)}
                      className={`shrink-0 rounded-full px-3 py-1 text-[12px] font-medium transition active:scale-95 ${
                        i === catIndex
                          ? "border border-action bg-parchment text-ink"
                          : "border border-hairline bg-white text-ink-48 hover:text-ink"
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-hairline bg-white text-ink-48 disabled:opacity-40 active:scale-95"
                  disabled={catIndex >= categories.length - 1}
                  onClick={() => setCatIndex((i) => Math.min(categories.length - 1, i + 1))}
                  title="Next"
                >
                  ›
                </button>
                <span className="shrink-0 text-[12px] text-ink-48">
                  {catIndex + 1}/{categories.length}
                </span>
              </div>

              <div className="min-h-0 flex-1 overflow-auto p-3">
                {current ? (
                  <>
                    <h4 className="mb-2 text-[13px] font-semibold tracking-wide text-ink-48">{current.name}</h4>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {current.items.map((item, i) => (
                        <TermCell
                          key={i}
                          item={item}
                          saved={!!(savedKeys && savedKeys.has((item.term || "").toLowerCase()))}
                          onToggleSave={onToggleSave}
                        />
                      ))}
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center p-4">
              <div className="rounded-[11px] border border-dashed border-hairline bg-parchment p-4 text-[14px] text-ink-48">
                No vocabulary terms were generated.
              </div>
            </div>
          )}
          </div>
        </div>

        <div className="border-t border-hairline bg-parchment px-4 py-2 text-[12px] text-ink-48">
          Click US or UK next to a word to hear it · use ‹ › or arrow keys to switch groups
        </div>
      </div>
    </div>
  );
};

window.TW.VocabSection = function VocabSection({ question, allowScoring, attempt, open, onOpenChange, savedKeys, onToggleSave }) {
  const { generateVocab, getVocab, VocabModal } = window.TW;

  const enabled = !!allowScoring;

  const visibleAttemptId = (() => {
    const id = attempt?.id;
    if (!id || String(id).startsWith("temp-")) return null;
    if (attempt?.score?.state !== "visible") return null;
    return id;
  })();

  const [vocab, setVocab] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const loadStarted = React.useRef(false);
  const cacheKey = `${question.study4_test_id}:${question.question_number}`;

  // The App prefetches vocab for the question in view + the next 2 (see the
  // IntersectionObserver in app.jsx) and stores results in window.TW.vocabCache.
  // When the modal opens we prefer that prefetched data so it appears instantly;
  // otherwise we fetch the saved table, and only generate (POST) on demand.
  // Loaded data is kept on close so reopening is instant.
  React.useEffect(() => {
    if (!open || !enabled || loadStarted.current) return;
    loadStarted.current = true;
    if (window.TW.vocabCache && window.TW.vocabCache[cacheKey]) {
      setVocab(window.TW.vocabCache[cacheKey]);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const existing = await getVocab(question.study4_test_id, question.question_number);
        if (cancelled) return;
        if (existing) {
          setVocab(existing);
        } else {
          const payload = await generateVocab(
            question.study4_test_id,
            question.question_number,
            visibleAttemptId
          );
          if (cancelled) return;
          setVocab(payload);
          if (window.TW.vocabCache) window.TW.vocabCache[cacheKey] = payload;
        }
      } catch (err) {
        if (cancelled) return;
        setError(err.message || "Could not load vocab");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, enabled, cacheKey]);

  if (!enabled) return null;

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const payload = await generateVocab(
        question.study4_test_id,
        question.question_number,
        visibleAttemptId
      );
      setVocab(payload);
      if (window.TW.vocabCache) window.TW.vocabCache[cacheKey] = payload;
    } catch (err) {
      setError(err.message || "Could not generate vocab");
    } finally {
      setLoading(false);
    }
  }

  return (
    <VocabModal
      open={!!open}
      vocab={vocab}
      loading={loading}
      error={error}
      regenerating={loading}
      question={question}
      savedKeys={savedKeys}
      onToggleSave={onToggleSave}
      onClose={() => onOpenChange?.(false)}
      onRegenerate={handleGenerate}
    />
  );
};
