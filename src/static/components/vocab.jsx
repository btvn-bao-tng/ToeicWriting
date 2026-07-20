window.TW.VocabTermCell = function VocabTermCell({ item, onOpenDetail }) {
  const { speak } = window.TW;
  const image = item.image;

  return (
    <div className="group flex flex-col gap-1.5">
      {image ? (
        <button
          type="button"
          className="relative block w-full cursor-pointer overflow-hidden rounded-[8px] border border-hairline bg-white"
          title={`Click to study "${item.term}" · hover to hear`}
          onMouseEnter={() => speak(item.term)}
          onFocus={() => speak(item.term)}
          onClick={() => onOpenDetail(item)}
        >
          <img
            src={image.url}
            alt={image.alt || item.term}
            loading="lazy"
            className="block h-auto w-full object-cover transition group-hover:opacity-90"
          />
          <span className="pointer-events-none absolute inset-x-0 bottom-0 truncate bg-black/45 px-1.5 py-0.5 text-[11px] font-medium text-white opacity-0 transition group-hover:opacity-100">
            {item.term}
          </span>
        </button>
      ) : (
        <button
          type="button"
          className="flex aspect-[3/2] w-full cursor-pointer items-center justify-center rounded-[8px] border border-dashed border-hairline bg-pearl text-ink-48 transition hover:border-action hover:text-action"
          title={`Click to study "${item.term}" · hover to hear`}
          onMouseEnter={() => speak(item.term)}
          onFocus={() => speak(item.term)}
          onClick={() => onOpenDetail(item)}
        >
          <span className="flex flex-col items-center gap-1">
            <span className="text-[20px] leading-none">♫</span>
            <span className="text-[12px] font-medium">{item.term}</span>
          </span>
        </button>
      )}
      <span className="self-start text-[13px] font-medium text-ink-80">{item.term}</span>
    </div>
  );
};

function DetailImage({ image, term }) {
  const { speak } = window.TW;
  if (!image) return null;
  return (
    <a
      className="group/img relative block overflow-hidden rounded-[8px] border border-hairline bg-white"
      href={image.page_url}
      target="_blank"
      rel="noreferrer"
      title={`Hover to hear · open on Pexels${image.photographer ? ` · by ${image.photographer}` : ""}`}
      onMouseEnter={() => speak(term)}
      onFocus={() => speak(term)}
    >
      <img
        src={image.url}
        alt={image.alt || term}
        loading="lazy"
        className="block h-auto w-full object-cover transition group-hover/img:opacity-90"
      />
    </a>
  );
}

window.TW.VocabTermDetail = function VocabTermDetail({ item, topic, questionPrompt, onBack }) {
  const { getVocabDetail, speak } = window.TW;
  const { BTN_UTILITY, LINK } = window.TW.classes;
  const [detail, setDetail] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setDetail(null);
    getVocabDetail(item.term, topic, item.image?.url, questionPrompt)
      .then((d) => { if (!cancelled) setDetail(d); })
      .catch((err) => { if (!cancelled) setError(err.message || "Could not load details"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [item.term, topic, item.image?.url, questionPrompt]);

  const extraImages = detail?.images || [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-3 py-2">
        <button type="button" className={`text-[13px] ${LINK}`} onClick={onBack}>
          ← Back to vocab
        </button>
        <button
          type="button"
          className={`${BTN_UTILITY} !text-[12px]`}
          title="Hear the word"
          onMouseEnter={() => speak(item.term)}
          onClick={() => speak(item.term)}
        >
          ♫ {item.term}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {loading ? (
          <div className="flex h-full min-h-[160px] items-center justify-center text-[14px] text-ink-48">
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-action border-t-transparent" />
              Loading details...
            </span>
          </div>
        ) : error ? (
          <div className="rounded-[11px] border border-red-200 bg-red-50 p-3 text-[14px] text-red-800">{error}</div>
        ) : (
          <div className="mx-auto max-w-[640px]">
            <div className="mb-3">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <h3 className="text-[22px] font-semibold leading-tight text-ink">{detail?.term || item.term}</h3>
                {detail?.ipa ? <span className="text-[15px] text-ink-48">{detail.ipa}</span> : null}
                {detail?.part_of_speech ? (
                  <span className="rounded-full border border-hairline bg-parchment px-2 py-0.5 text-[11px] font-medium text-ink-48">
                    {detail.part_of_speech}
                  </span>
                ) : null}
                {detail?.register ? (
                  <span className="rounded-full border border-hairline bg-white px-2 py-0.5 text-[11px] font-medium text-action">
                    {detail.register}
                  </span>
                ) : null}
              </div>
            </div>

            {detail?.explanation ? (
              <div className="mb-3">
                <h4 className="mb-1 text-[12px] font-semibold tracking-wide text-ink-48">MEANING</h4>
                <p className="text-[15px] leading-relaxed text-ink-80">{detail.explanation}</p>
              </div>
            ) : null}

            {detail?.example ? (
              <div className="mb-4">
                <h4 className="mb-1 text-[12px] font-semibold tracking-wide text-ink-48">EXAMPLE</h4>
                <blockquote className="rounded-[11px] border-l-4 border-action bg-parchment py-2 pl-3 pr-2 text-[15px] leading-relaxed text-ink-80">
                  {detail.example}
                </blockquote>
              </div>
            ) : null}

            {detail?.synonyms?.length ? (
              <div className="mb-4">
                <h4 className="mb-1.5 text-[12px] font-semibold tracking-wide text-ink-48">SYNONYMS · hover to hear</h4>
                <div className="flex flex-wrap gap-1.5">
                  {detail.synonyms.map((syn, i) => (
                    <button
                      key={i}
                      type="button"
                      className="rounded-full border border-hairline bg-white px-2.5 py-1 text-[13px] font-medium text-ink-80 transition hover:border-action hover:text-action active:scale-95"
                      title="Hover to hear"
                      onMouseEnter={() => speak(syn)}
                      onFocus={() => speak(syn)}
                      onClick={() => speak(syn)}
                    >
                      {syn}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {detail?.collocations?.length ? (
              <div className="mb-4">
                <h4 className="mb-1.5 text-[12px] font-semibold tracking-wide text-ink-48">COLLOCATIONS · hover to hear</h4>
                <div className="flex flex-wrap gap-1.5">
                  {detail.collocations.map((col, i) => (
                    <button
                      key={i}
                      type="button"
                      className="rounded-full border border-hairline bg-pearl px-2.5 py-1 text-[13px] text-ink-80 transition hover:border-action hover:text-action active:scale-95"
                      title="Hover to hear"
                      onMouseEnter={() => speak(col)}
                      onFocus={() => speak(col)}
                      onClick={() => speak(col)}
                    >
                      {col}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {extraImages.length ? (
              <div>
                <h4 className="mb-2 text-[12px] font-semibold tracking-wide text-ink-48">MORE IMAGES</h4>
                <div className="grid grid-cols-2 gap-2.5">
                  {extraImages.map((img, i) => (
                    <DetailImage key={i} image={img} term={item.term} />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

window.TW.vocabStripHtml = function vocabStripHtml(html) {
  if (!html) return "";
  return String(html).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
};

window.TW.QuestionPicture = function QuestionPicture({ question }) {
  const assets = Array.isArray(question?.asset_urls) ? question.asset_urls : [];
  const promptText = question?.prompt_text || "";
  const promptHtml = question?.prompt_html || "";

  return (
    <div className="flex h-full flex-col gap-3">
      <strong className="text-[12px] font-semibold uppercase tracking-wide text-ink-48">Question picture</strong>
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
      ) : null}
      {promptText ? (
        <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-80">{promptText}</p>
      ) : null}
    </div>
  );
};

window.TW.VocabModal = function VocabModal({ open, vocab, loading, error, onClose, onRegenerate, regenerating, question }) {
  const { BTN_UTILITY: Btn } = window.TW.classes;
  const { VocabTermCell: TermCell, VocabTermDetail: TermDetail, QuestionPicture } = window.TW;
  const categories = vocab?.categories || [];

  const [catIndex, setCatIndex] = React.useState(0);
  const [detailItem, setDetailItem] = React.useState(null);

  React.useEffect(() => {
    if (open) {
      setCatIndex(0);
      setDetailItem(null);
    }
  }, [open, vocab]);

  React.useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === "Escape") {
        if (detailItem) setDetailItem(null);
        else onClose();
      } else if (e.key === "ArrowLeft" && !detailItem) {
        setCatIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "ArrowRight" && !detailItem) {
        setCatIndex((i) => Math.min(categories.length - 1, i + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose, detailItem, categories.length]);

  if (!open) return null;

  const current = categories[catIndex];
  const questionPromptText = question
    ? [question.prompt_text || "", window.TW.vocabStripHtml(question.prompt_html)].filter(Boolean).join(" ")
    : "";

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[100dvh] w-screen flex-col overflow-hidden bg-white"
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
          {detailItem ? (
            <TermDetail item={detailItem} topic={vocab?.topic || ""} questionPrompt={question ? questionPromptText : ""} onBack={() => setDetailItem(null)} />
          ) : error ? (
            <div className="flex h-full items-center justify-center p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-[11px] border border-red-200 bg-red-50 p-3 text-[14px] text-red-800">
                <span>{error}</span>
                <button type="button" className={`${Btn} !text-[12px]`} onClick={onRegenerate} disabled={regenerating}>
                  Try again
                </button>
              </div>
            </div>
          ) : loading ? (
            <div className="flex h-full items-center justify-center text-[15px] text-ink-48">
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-action border-t-transparent" />
                Generating vocab &amp; images...
              </span>
            </div>
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
                    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-4">
                      {current.items.map((item, i) => (
                        <TermCell key={i} item={item} onOpenDetail={setDetailItem} />
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
          Hover an image to hear the word · click an image to study it · use ‹ › or arrow keys to switch groups
        </div>
      </div>
    </div>
  );
};

window.TW.VocabSection = function VocabSection({ question, allowScoring, attempt, open, onOpenChange }) {
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

  React.useEffect(() => {
    if (open) return;
    setVocab(null);
    setError("");
    setLoading(false);
    loadStarted.current = false;
  }, [open]);

  React.useEffect(() => {
    if (!open || !enabled || loadStarted.current) return;
    loadStarted.current = true;
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
        }
      } catch (err) {
        if (cancelled) return;
        setError(err.message || "Could not load vocab");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, enabled]);

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
      onClose={() => onOpenChange?.(false)}
      onRegenerate={handleGenerate}
    />
  );
};
