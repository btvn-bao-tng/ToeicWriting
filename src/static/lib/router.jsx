window.TW.LAST_TEST_KEY = "toeic-sw-writing-last-test-id";
window.TW.LAST_PART_KEY = "toeic-sw-writing-last-part";
window.TW.LAST_QUESTION_KEY = "toeic-sw-writing-last-question-number";

window.TW.parseHash = function parseHash() {
  const raw = (window.location.hash || "#/tests").replace(/^#/, "");
  const segments = raw.split("/").filter(Boolean);
  if (segments[0] === "revision") return { view: "revision", testId: null, mockExamId: null };
  if (segments[0] === "game") return { view: "game", testId: null, mockExamId: null };
  if (segments[0] !== "tests") return { view: "tests", testId: null, mockExamId: null };
  const testId = segments[1] ? Number(segments[1]) : null;
  const view = segments[2] || "actions";
  const mockExamId = segments[3] ? Number(segments[3]) : null;
  if (!testId) return { view: "tests", testId: null, mockExamId: null };
  if (!["actions", "practice", "mock"].includes(view)) return { view: "actions", testId, mockExamId: null };
  return { view, testId, mockExamId };
}

window.TW.buildHash = function buildHash({ view, testId, mockExamId }) {
  if (view === "revision") return "#/revision";
  if (view === "game") return "#/game";
  if (!testId) return "#/tests";
  if (view === "mock" && mockExamId) return `#/tests/${testId}/mock/${mockExamId}`;
  if (view === "actions") return `#/tests/${testId}`;
  return `#/tests/${testId}/${view}`;
}

window.TW.visibleQuestions = function visibleQuestions(payload, selectedPart) {
  const questions = payload?.questions || [];
  if (selectedPart === "all") return questions;
  const part = (payload?.parts || []).find((item) => String(item.sort_order) === String(selectedPart));
  if (!part) return questions;
  return questions.filter((question) => question.study4_part_id === part.study4_part_id);
}

window.TW.progressKey = function progressKey(question) {
  return `${question.study4_test_id}:${question.question_number}`;
}

window.TW.scoreFromRow = function scoreFromRow(row) {
  return {
    id: String(row.id),
    answer: row.answer || "",
    created_at: row.created_at,
    model: row.model,
    score: {
      state: row.score_state || "visible",
      text: row.score_text || "",
    },
  };
}
