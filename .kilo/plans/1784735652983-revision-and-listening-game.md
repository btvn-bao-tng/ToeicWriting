# Plan: Vocab Revision List + Listen-and-Pick-Image Game

## Goal
1. **Revision list** — logged-in users can save any vocab term from the Vocab modal to a personal "revision" deck; view/remove saved terms on a dedicated page.
2. **Listening game** — the site speaks a saved term via TTS; the user picks the matching image from 4 options. Pulls exclusively from the user's revision list. Scores are session-only (no persistence).

## Decisions (confirmed with user)
- Add-to-revision entry point: **bookmark button on each `VocabTermCell`** in the existing Vocab modal (one-click save/remove).
- Game vocab source: **user's revision list** (ties both features together; needs ≥4 image-bearing saved terms).
- Game scores: **session-only, no DB persistence**.
- Access: **login required** for both revision and game (data is per-user). Guests see a login prompt.

## Architecture notes (from codebase)
- Backend: FastAPI; SQLAlchemy models in `src/database.py` with `_migrate()` for additive column changes; **new tables are created by `Base.metadata.create_all` on startup** (no manual migration needed for a brand-new table). Session auth via `require_user`. TTS endpoint `GET /api/tts?text=&accent=us|uk` already exists and is `require_user`-gated. Vocab terms normalized as `vocab_tables → vocab_categories → vocab_terms`.
- Frontend: React 18 UMD + Babel-in-browser (no build step). Scripts registered in `src/index.html` with cache-busting `?v=` tags (static middleware also sets `no-store`). Global `window.TW` namespace. Hash router in `app.jsx` (`parseHash`/`buildHash`); currently only `#/tests...`. `speak(text, accent)` (utils.jsx:97) plays the `/api/tts` MP3 via a single shared `<audio>` element, falling back to `SpeechSynthesis`.
- `VocabSection`/`VocabModal`/`VocabTermCell` live in `src/static/components/vocab.jsx` and are used **only** in `src/static/components/practice.jsx` (`QuestionCard`). Mock exam does NOT show vocab — so bookmark prop-threading is scoped to `practice.jsx → vocab.jsx` only.

---

## Backend

### 1. New model — `src/database.py`
Add `RevisionItem` (denormalized snapshot of a `VocabTerm`, decoupled from `vocab_tables` so it survives regeneration/deletion):

```python
class RevisionItem(Base):
    __tablename__ = "revision_items"
    __table_args__ = (
        UniqueConstraint("user_id", "term"),
        Index("idx_revision_items_user", "user_id", "id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    image_url: Mapped[str | None] = mapped_column(Text)
    image_page_url: Mapped[str | None] = mapped_column(Text)
    image_photographer: Mapped[str | None] = mapped_column(Text)
    image_alt: Mapped[str | None] = mapped_column(Text)
    part_of_speech: Mapped[str | None] = mapped_column(Text)
    ipa: Mapped[str | None] = mapped_column(Text)
    meaning: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)
    vietnamese_meaning: Mapped[str | None] = mapped_column(Text)
    synonyms: Mapped[str | None] = mapped_column(Text)  # JSON array string
    created_at: Mapped[str] = mapped_column(String, nullable=False)
```
- Uniqueness is enforced case-sensitively by the DB constraint, but the repo upsert must be **case-insensitive** (query existing by `func.lower(term) == func.lower(new_term)`); re-saving the same term refreshes metadata and keeps `created_at`. No `_migrate()` entry needed (new table).

### 2. Schemas — `src/schemas.py`
```python
class RevisionItemRequest(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    topic: str = Field(default="", max_length=80)
    image: dict | None = None          # {url, page_url, photographer, alt}
    part_of_speech: str | None = None
    ipa: str | None = None
    meaning: str | None = None
    example: str | None = None
    vietnamese_meaning: str | None = None
    synonyms: list[str] | None = None
```

### 3. Repo — `src/repositories/revision.py` (NEW)
- `list_revision(conn, user_id) -> list[dict]` — ordered by `created_at DESC, id DESC`. Each dict: `id, term, topic, image{url,page_url,photographer,alt}, part_of_speech, ipa, meaning, example, vietnamese_meaning, synonyms[list], created_at`.
- `upsert_revision(conn, user_id, data: dict) -> dict` — case-insensitive term match: if exists, update metadata fields (image_*, pos, ipa, meaning, example, vn, synonyms, topic) and return existing row assembled as dict with `created=false`; else insert new row (new `id`, `created_at=now()`), return dict with `created=true`.
- `find_revision_owned(conn, user_id, item_id) -> row | None`.
- `delete_revision(conn, user_id, item_id) -> bool`.
- Reuse the `synonyms` JSON-encode/decode pattern from `repositories/vocab.py`.

### 4. Router — `src/routers/revision.py` (NEW)
All `Depends(require_user)`, use `run_in_threadpool` + `db()` context (mirror `routers/vocab.py`):
- `GET /api/revision` → `{ items: [...] }` (wrap in object for forward-compat).
- `POST /api/revision` (body `RevisionItemRequest`) → the upserted item dict (+ `created` bool). Convert request → repo dict (flatten `image` sub-dict).
- `DELETE /api/revision/{item_id}` → 204 / 404 if not owned.

### 5. Register router — `src/main.py`
`from .routers import revision as revision_router` and `app.include_router(revision_router.router)`.

---

## Frontend

### 6. API helpers — `src/static/lib/api.jsx`
Add:
- `listRevision()` → `GET /api/revision` → returns `items` array.
- `addRevision(item)` → `POST /api/revision` with body built from a `VocabTermCell` item (`term, topic, image, part_of_speech, ipa, meaning, example, vietnamese_meaning, synonyms`). Returns `{...item, created}`.
- `removeRevision(id)` → `DELETE /api/revision/{id}`.
(Bump `?v=` on this file in index.html.)

### 7. Bookmark button — `src/static/components/vocab.jsx`
- `VocabTermCell({ item, saved, onToggleSave })`: add a bookmark button in the existing audio-button cluster (next to 🇺🇸/🇬🇧). Icon `+` when `!saved`, `✓` when `saved`; `title` "Add to revision"/"Saved to revision". Calls `onToggleSave(item)`.
- `VocabModal({ ..., savedKeys, onToggleSave })`: pass through; compute per-item `saved={savedKeys?.has(item.term.toLowerCase())}` when rendering `<TermCell>`.
- `VocabSection({ ..., savedKeys, onToggleSave })`: pass through to `VocabModal`.
(Bump `?v=`.)

### 8. Thread bookmark props — `src/static/components/practice.jsx`
- `QuestionCard({ ..., revisionSavedKeys, onToggleRevision })`: pass to `<VocabSection savedKeys={revisionSavedKeys} onToggleSave={onToggleRevision} />`.
(Bump `?v=`.)

### 9. Revision page — `src/static/components/revision.jsx` (NEW)
`window.TW.RevisionScreen({ onPlayGame, onLogin, isGuest })`:
- On mount (when logged in): `listRevision()` → state `items`.
- Render header with count + "Play listening game" button (`onPlayGame`).
- Grid of `RevisionCard` (image, term, ipa, pos, meaning, example (click→speak), VN, 🇺🇸/🇬🇧 buttons, remove ✕ button → `removeRevision(id)` then update state).
- Empty state: "You haven't saved any vocabs yet. Open a question's 'Vocab + images' and tap the bookmark on a word."
- Guest state: login prompt (reuse the existing guest banner pattern from `app.jsx`).

### 10. Game — `src/static/components/game.jsx` (NEW)
`window.TW.GameScreen({ onLeave, onLogin, isGuest })`:
- On mount (logged in): `listRevision()` → filter to items with `image?.url`.
- **Min to play: 4 image-bearing items.** If fewer → empty state: "Save at least 4 vocabs with images to your revision list, then play." with a button to go to Revision.
- Client-side state machine (`phase`: `playing | answered | done`):
  1. `Start`: shuffle the image-bearing items into `queue`; `score={correct:0,total:queue.length}`; `round=0`; accent state (default `us`, toggle US/UK).
  2. Per round: `current = queue[round]`; build 4 options = correct image + 3 random **other** items' images (unique, shuffle order); `speak(current.term, accent)`; `phase=playing`. **Do not show the term text** during the round (only the audio + a "Replay" button).
  3. User clicks an image (or keys 1–4): mark selected; `phase=answered`; highlight correct (green) + wrong pick (red); reveal term text, ipa, meaning, VN as feedback; if correct → `score.correct++`.
  4. `Next` → `round++`; if past end → `phase=done` (summary: `correct/total`, "Play again" reshuffles, "Back to revision").
- Autoplay note: rounds advance on user clicks ("Start"/"Next"/"Replay"), so programmatic `audio.play()` follows a user gesture → allowed; `SpeechSynthesis` fallback already exists in `speak()`.

### 11. Header nav — `src/static/components/layout.jsx`
Add nav links (Tests / Revision / Game) in `Header`. Clicking sets the hash route. Highlight active view. (Bump `?v=`.)

### 12. Router + state — `src/static/app.jsx`
- `parseHash`/`buildHash`: add top-level views
  - `#/revision` → `{ view: "revision", testId: null, mockExamId: null }`
  - `#/game` → `{ view: "game", testId: null, mockExamId: null }`
  - Keep `#/tests...` behavior unchanged (default `#/tests`).
- Revision state (login-gated): `revisionItems` (array), derived `revisionSavedKeys = new Set(items.map(i=>i.term.toLowerCase()))`, `revisionTermToId` map for deletes. `loadRevision()` called after `handleAuthenticated` and in `boot()` when a session exists (like `loadTests`).
- `handleToggleRevision(item)`: key=`item.term.toLowerCase()`; if in set → `removeRevision(revisionTermToId[key])` then remove from state; else `addRevision(item)` then add returned item to state. **Optimistic** toggle of the bookmark; on error revert + `setStatus`.
- On logout / auth-expired: clear revision state (add to the existing reset blocks).
- Render branches (login-gated, reuse guest banner):
  - `view === "revision"` → `<RevisionScreen .../>`
  - `view === "game"` → `<GameScreen .../>`
- Pass `revisionSavedKeys` + `onToggleRevision` into each `<QuestionCard>` (practice view).
(Bump `?v=`.)

### 13. Register new scripts — `src/index.html`
Add `<script type="text/babel" src="/static/components/revision.jsx?v=20260722-revision1"></script>` and `.../game.jsx?v=20260722-revision1"` (load before `app.jsx`). Bump `?v=` on edited files: `api.jsx`, `vocab.jsx`, `practice.jsx`, `layout.jsx`, `app.jsx` to `v=20260722-revision1`.

---

## Edge cases / risks
- **Case-insensitive dedup**: same word saved from different questions → one revision entry (metadata refreshed on re-save, `created_at` retained). Repo enforces via `func.lower(term)` lookup, not just the DB unique constraint (which is case-sensitive on SQLite).
- **Autoplay policy**: game's programmatic TTS plays only after user gestures (Start/Next/Replay) → allowed; `SpeechSynthesis` fallback covers blocked autoplay.
- **Shared `<audio>` element** in `speak()`: only one audio plays at a time — fine for the game (single target term per round). Game modal and vocab modal are never open together.
- **<4 image-bearing terms**: game shows a helpful empty state pointing to the Revision page.
- **Regenerating a vocab table** does NOT delete saved revision items (denormalized snapshot) — by design.
- **Existing SQLite/Postgres DBs**: new `revision_items` table is auto-created by `create_all` on next startup; no data migration.

## Validation
1. Backend syntax: `python -c "import ast,sys; [ast.parse(open(f).read()) for f in ['src/database.py','src/schemas.py','src/repositories/revision.py','src/routers/revision.py','src/main.py']]"` (no lint/test config exists in repo).
2. Start server: `uvicorn src.main:app --reload` (or existing run command). Confirm `health` is ok and `revision_items` table created (e.g. `sqlite3 data/database.db ".tables"`).
3. Smoke-test API (with a logged-in session/cookie): `GET /api/revision` → `{items:[]}`; `POST /api/vocab/detail`-style flow not needed — instead `POST /api/revision` with a sample item → returns item with id; `GET` again shows it; `DELETE /api/revision/{id}` removes it.
4. UI smoke test: open a question → Vocab modal → bookmark a few words (icon toggles); go to `#/revision` → see them, remove one; ensure ≥4 image-bearing saved → `#/game` → hear term, pick image, score advances, "Play again" reshuffles; log out → revision/game show login prompt.
5. Refresh the page while logged in → revision state reloads and bookmark icons reflect saved state across all question vocab modals.

## Out of scope
- Manual free-text vocab entry on the Revision page.
- Persisting game scores/history to the DB.
- Guest access to revision/game.
- Spaced-repetition scheduling (SRS) — revision is a flat deck; future enhancement.
