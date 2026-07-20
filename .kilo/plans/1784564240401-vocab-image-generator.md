# Vocab + Image Generator (post-score)

## Goal
After a question is scored ("Save & score") and the AI response finishes, show a **Generate vocab + images** button in the AI feedback panel. Clicking it asks the LLM for a topic-grouped vocab table (categories decided by the LLM per topic), fetches one Pexels image per vocab term (capped), persists the result to the DB linked to the attempt, and renders a grid. Hovering any term speaks it via the Web Speech API (en-US, debounced).

## Confirmed decisions
- **Categories**: LLM-decided per topic (3–6 categories, dynamic names), not fixed.
- **Images**: one per vocab term, total cap ~28 terms, fetched in parallel (concurrency 6). Missing image → muted placeholder box, term kept.
- **Trigger**: button inside `FeedbackPanel`, shown only when `attempt.score.state === "visible"`; **login required** (consistent with scoring, protects Pexels rate-limit).
- **Response style**: single JSON response (AI returns structured JSON, backend attaches images, returns one payload).
- **Persistence**: store the generated table + image URLs in a new DB table linked to `attempt_id`; upsert on regenerate; reload shows the saved table.
- **TTS**: `window.speechSynthesis`, `en-US`, cancel-then-speak on hover (debounced).
- **Pexels key**: move to `.env` as `PEXELS_API_KEY`; remove the hardcoded key from `zdraft/search_image.py`. Endpoint returns **400** if unset.

## Data flow
1. User scores a question → `attempt` row created (`attempts.id`), stream completes, `score.state === "visible"`.
2. `FeedbackPanel` shows **Generate vocab + images** button. If a saved vocab table exists for this attempt (lazy `GET /api/vocab`), it is rendered instead and the button reads **Regenerate**.
3. Click → `POST /api/vocab { attempt_id, study4_test_id, question_number }` (login required).
4. Backend verifies the attempt belongs to the user; loads the attempt's `answer` + `score_text`; loads the question (`content_service.find_question`) for `prompt_text`/`prompt_html`/`asset_urls`.
5. `vocab_service.generate_table(...)` → `ai_service.ai_chat(vocab_system_prompt, vocab_user_content)` → tolerant JSON parse → cap/validate.
6. `image_service.attach_images(table)` → for each term, Pexels `GET /v1/search` (urllib, timeout 15s), `ThreadPoolExecutor(max_workers=6)`, in-memory LRU keyed by normalized term. `image_url`/`page_url`/`photographer`/`alt_text`, or `null`.
7. Persist to `vocab_tables` (upsert by `attempt_id`), return full payload.
8. Frontend renders `VocabPanel` (topic header + category columns + cells); hover term → `speak()`.

## Backend tasks

### 1. Config & env
- `src/config.py`: add `PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")`.
- `.env`: add `PEXELS_API_KEY=DiLSjYHWBx5jcJDNh2Nc1kbN2oUgXjFpnBkt0QmDJU8KabzhJWOXjCWq` (the key currently hardcoded in `zdraft/search_image.py`).
- `.env.example`: add commented `# PEXELS_API_KEY=` line under a new "Pexels image search" section.
- `zdraft/search_image.py`: remove the hardcoded key from `__main__` (read from env or leave the draft alone — but at minimum do not rely on it). **Do not import `requests`** in production code.

### 2. DB model (`src/database.py`)
Add a new ORM model (new table → `Base.metadata.create_all` auto-creates on startup; no `_migrate()` change needed):
```
class VocabTable(Base):
    __tablename__ = "vocab_tables"
    __table_args__ = (UniqueConstraint("attempt_id"), Index("idx_vocab_tables_user", "user_id", "id"))
    id, attempt_id (FK attempts.id ON DELETE CASCADE), user_id (FK users.id ON DELETE CASCADE),
    study4_test_id, question_number, topic (String), payload (Text, JSON string of full table incl. images),
    model (String|None), created_at (String), updated_at (String)
```
- One row per attempt (regenerate overwrites via upsert keyed on `attempt_id`).

### 3. Repositories (`src/repositories/vocab.py` — new)
- `upsert_vocab_table(conn, user_id, attempt_id, study4_test_id, question_number, topic, payload_json, model) -> int`
- `find_vocab_table_by_attempt(conn, attempt_id) -> dict|None`
- `find_vocab_table_by_attempt_owned(conn, attempt_id, user_id) -> dict|None` (ownership check helper)

### 4. Image service (`src/services/images.py` — new; uses `urllib.request`, no `requests`)
- `pexels_search(query: str) -> dict|None` → returns `{image_url, page_url, photographer, alt_text}` or None. Endpoint `https://api.pexels.com/v1/search`, header `Authorization: PEXELS_API_KEY`, params `query, per_page=1, orientation=landscape`. Raise HTTPException(400) if `PEXELS_API_KEY` unset is handled by the router, not here (service returns None on missing key? — no: router gates it).
- `@lru_cache(maxsize=2048)` wrapper `cached_pexels_search(query)` for the in-memory cache (normalize+lowercase query).
- `attach_images(categories: list[dict]) -> list[dict]` → for each term build query (try `term`, fallback `"{topic} {term}"` if first returns None), run via `concurrent.futures.ThreadPoolExecutor(max_workers=6)`, attach `image` dict or None. Preserve input order.

### 5. Vocab service (`src/services/vocab.py` — new)
- `VOCAB_SYSTEM_PROMPT` (in-code, or `data/system_prompt/vocab.md`): instruct the model to act as a TOEIC vocabulary curator; return **ONLY** a JSON object:
  ```
  { "topic": "OFFICE WORK",
    "categories": [ { "name": "PEOPLE", "terms": ["office worker", "employee", ...] }, ... ] }
  ```
  Constraints: 3–6 categories; 3–6 terms per category; total ≤ 28 terms; terms must be concrete/image-searchable English (single words or short phrases) relevant to the picture/prompt; categories named in UPPERCASE; no duplicates across the table.
- `build_vocab_user_content(question_row, answer, score_text) -> list[dict]` → text-only content (no vision): include test title, part, question number, `prompt_text`, `prompt_html` (stripped of tags is fine), asset URLs as text, the user's answer, and the AI score text as context. (Reuse the pattern from `scoring.build_user_content` but text-only — do NOT attach image data URLs, to avoid requiring a vision model.)
- `generate_table(question_row, answer, score_text) -> dict` → call `ai_service.ai_chat` (temperature 0.3). Tolerant parse: strip ```json fences, locate first `{` … last `}`, `json.loads`; on failure raise HTTPException(502, "Could not parse vocab table"). Enforce caps (truncate categories/terms) and de-duplicate.
- `build_payload(table_with_images, model) -> dict` → the response shape below.

### 6. Router (`src/routers/vocab.py` — new)
- `POST /api/vocab` body `VocabRequest{attempt_id, study4_test_id, question_number}`, `Depends(require_user)`.
  - If not `PEXELS_API_KEY` → HTTPException(400, "PEXELS_API_KEY is not set").
  - Load attempt via `attempts`; verify `attempt.user_id == user["id"]` and matches `study4_test_id`/`question_number` else 403/404.
  - Require `attempt.score_state == "visible"` (else 409, "Score the answer first").
  - `question_row = content_service.find_question(...)`; generate table; attach images; upsert; return `VocabResponse`.
- `GET /api/vocab?attempt_id=...` (login required): ownership check; return persisted payload or `404` if none.
- Register in `src/main.py` (`from .routers import vocab as vocab_router; app.include_router(vocab_router.router)`).

### 7. Schemas (`src/schemas.py`)
- `VocabRequest(BaseModel): attempt_id: int; study4_test_id: int; question_number: int = Field(ge=1, le=8)`.
- Response is a plain dict (no pydantic model needed) — shape:
  ```
  { "id", "attempt_id", "study4_test_id", "question_number", "topic",
    "categories": [ { "name": str, "items": [ { "term": str, "image": {url,page_url,alt,photographer} | None } ] } ],
    "model", "created_at" }
  ```

## Frontend tasks (JSX, no build step — bump `?v=` in `index.html`)

### 8. API helpers (`src/static/lib/api.jsx`)
- `window.TW.generateVocab(attempt_id, study4_test_id, question_number)` → `apiJson("/api/vocab", {method:"POST", body})`.
- `window.TW.getVocab(attempt_id)` → `apiJson("/api/vocab?attempt_id=...")`; tolerate 404 → return null.

### 9. TTS util (`src/static/lib/utils.jsx`)
- `window.TW.speak = function(text)` — if `!window.speechSynthesis` return; `speechSynthesis.cancel()`; `const u = new SpeechSynthesisUtterance(text); u.lang="en-US"; u.rate=0.95; speechSynthesis.speak(u)`.
- Hover handler: on `mouseenter` call `speak(term)`; rely on `cancel()` for debounce (no overlapping). Optional 120ms guard via a ref timestamp if rapid re-entry is noisy.

### 10. Components (`src/static/components/practice.jsx` + new `src/static/components/vocab.jsx`)
- New `VocabPanel({ vocab, onRegenerate, regenerating })`: topic header (e.g. `OFFICE WORK`), responsive grid of category columns; each column: category name header + list of `VocabTermCell`. A "Regenerate" button (BTN_UTILITY).
- `VocabTermCell({ item })`: image (or muted placeholder box `bg-pearl` with term) + the term as a button/span with `onMouseEnter={() => speak(item.term)}` and `title="Hover to hear"`. Image `loading="lazy"`, `rounded-sm`, `border hairline`. Clicking the image opens `image.page_url` in a new tab (photographer credit per Pexels ToS).
- `FeedbackPanel` changes (`practice.jsx:153`): after the latest attempt and when `attempt.score.state === "visible"`, render a vocab section:
  - On mount/attempts change: lazy `getVocab(attempt.id)` → if found, show `VocabPanel`; else show **Generate vocab + images** button.
  - Button → `generateVocab(...)`; manage local state `{ vocab, loading, error }`; show loading ("Generating vocab & images…"); on success set vocab; on error show inline message (reuse `enrichScoreError` style).
  - Only for the latest attempt (mirror existing `attempt = attempts[attempts.length - 1]`).
- Wire `speak` from `window.TW`.

### 11. `index.html`
- Add `<script type="text/babel" src="/static/components/vocab.jsx?v=20260720-apple-ui3">` before `app.jsx`.
- Bump `?v=` on `utils.jsx`, `api.jsx`, `practice.jsx` to `v=20260720-apple-ui3` to bust cache.

## Risks & mitigations
- **Pexels rate limit (200/hr)**: in-memory LRU by term + DB persistence (regenerate overwrites, but repeat terms across users/questions hit cache). Concurrency 6. If rate-limited (HTTP 429), treat as "no image" (placeholder) rather than failing the whole request — catch per-term errors in `attach_images`.
- **AI not returning valid JSON**: tolerant parser + caps; 502 with clear message.
- **Non-vision model**: vocab generation is text-only (uses prompt text + asset URLs as text), so it works with `kimi-k2.7-code` and any chat model.
- **New table on Postgres**: `create_all` handles it. If a partial run leaves a half-created table, `create_all` is idempotent.
- **Ownership**: every endpoint verifies `attempt.user_id == user["id"]`.
- **Stale vocab after re-score**: vocab is keyed to `attempt_id`; re-scoring creates a *new* attempt → old vocab still loads for the old attempt; the new attempt starts with no vocab (button reappears). Acceptable.

## Validation
- `python -m compileall src` (syntax check; no lint/test framework present in repo).
- Start server; log in; open a Part 1 question (has a picture) → **Save & score** → wait for stream to finish → click **Generate vocab + images** → verify: topic header + 3–6 category columns render, each term has an image (or placeholder), hovering a term speaks it (en-US), clicking an image opens Pexels page.
- Reload the page → the saved vocab table reappears without regenerating (loaded via `GET /api/vocab`).
- Regenerate → table updates and persists.
- Negative: click generate with `PEXELS_API_KEY` unset → 400 message; generate before scoring completes → 409 / button not shown; access another user's attempt → 403/404.
- Check mobile width: category columns collapse to a single stack (responsive).

## Out of scope
- Vision-based vocab from the actual picture image bytes (text-only input used for portability).
- Streaming the vocab table.
- Persisting vocab for guests (login required).
- Editing/curating individual vocab terms in the UI.
- Migrating existing `zdraft/search_image.py` into the package beyond removing the leaked key.
