const { useEffect, useState } = React;

function RevisionCard({ item, onRemove, removing }) {
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
        <button
          type="button"
          className="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-full border border-hairline bg-white/90 text-[14px] leading-none text-ink-48 backdrop-blur transition active:scale-95 hover:bg-white hover:text-[#ea4335] disabled:opacity-60"
          title="Remove from revision"
          disabled={removing}
          onClick={() => onRemove(item)}
        >
          ✕
        </button>
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
            title="Hear example (US)"
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
}

window.TW.RevisionScreen = function RevisionScreen({ onPlayGame, onLogin, isGuest }) {
  const { listRevision, removeRevision, EmptyState } = window.TW;
  const { BTN_PRIMARY, CARD } = window.TW.classes;

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [removingId, setRemovingId] = useState(null);

  useEffect(() => {
    if (isGuest) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await listRevision();
        if (!cancelled) setItems(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load revision list");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isGuest]);

  async function handleRemove(item) {
    setRemovingId(item.id);
    try {
      await removeRevision(item.id);
      setItems((prev) => prev.filter((it) => it.id !== item.id));
    } catch (err) {
      setError(err.message || "Could not remove item");
    } finally {
      setRemovingId(null);
    }
  }

  if (isGuest) {
    return (
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">Revision</h2>
          <p className="text-[17px] text-ink-48">Save words from any vocab table and review them here.</p>
        </div>
        <div className={`${CARD} p-10 text-center`}>
          <p className="mb-4 text-[17px] text-ink-80">Log in to save and review your vocabulary.</p>
          <button
            type="button"
            onClick={onLogin}
            className={`${BTN_PRIMARY}`}
          >
            Login with Gmail
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-2">
          <h2 className="text-[40px] font-semibold leading-[1.1] tracking-normal text-ink">Revision</h2>
          <p className="text-[17px] text-ink-48">
            {loading ? "Loading..." : `${items.length} saved vocab${items.length === 1 ? "" : "s"}`}
          </p>
        </div>
        <button
          type="button"
          onClick={onPlayGame}
          className={`${BTN_PRIMARY} !text-[15px] disabled:opacity-60`}
          disabled={loading || items.length < 4}
          title={items.length < 4 ? "Save at least 4 vocabs with images to play" : "Play the listening game"}
        >
          Play listening game
        </button>
      </div>

      {error ? <EmptyState error>{error}</EmptyState> : null}

      {!error && !loading && items.length === 0 ? (
        <div className={`${CARD} border-dashed p-8 text-center text-[15px] text-ink-48`}>
          You haven't saved any vocabs yet. Open a question's <strong className="text-ink-80">Vocab + images</strong> and tap the <span className="font-semibold text-ink-80">+</span> bookmark on a word to add it here.
        </div>
      ) : null}

      {!error && (loading || items.length) ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex flex-col overflow-hidden rounded-[10px] border border-hairline bg-white">
                  <div className="tw-skel aspect-[3/2] w-full" />
                  <div className="flex flex-col gap-1.5 p-2.5">
                    <div className="tw-skel h-4 w-24 rounded-[6px]" />
                    <div className="tw-skel h-3 w-full rounded-[6px]" />
                    <div className="tw-skel h-3 w-4/5 rounded-[6px]" />
                  </div>
                </div>
              ))
            : items.map((item) => (
                <RevisionCard
                  key={item.id}
                  item={item}
                  removing={removingId === item.id}
                  onRemove={handleRemove}
                />
              ))}
        </div>
      ) : null}

      {!error && !loading && items.length > 0 && items.length < 4 ? (
        <p className="text-[13px] text-ink-48">
          Save at least {4 - items.length} more vocab{4 - items.length === 1 ? "" : "s"} (with images) to unlock the listening game.
        </p>
      ) : null}
    </section>
  );
};
