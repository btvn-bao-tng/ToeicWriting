window.TW = window.TW || {};

window.TW.classes = {
  PILL_CLASS: "rounded-full border border-slate-200 bg-white px-2.5 py-1 text-sm text-slate-500",
  PART_BUTTON_BASE: "min-h-9 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 hover:border-teal-700 hover:bg-teal-50 hover:text-teal-950",
  PART_BUTTON_ACTIVE: "border-teal-700 bg-teal-50 text-teal-950",
  SCORE_RESULT_BASE: "mt-2.5 overflow-hidden rounded-lg border border-slate-200 bg-white text-sm leading-relaxed",
};

window.TW.fetchJson = async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
};

window.TW.partName = function partName(part) {
  if (!part) return "Part";
  if (part.sort_order === 1) return "Part 1";
  if (part.sort_order === 2) return "Part 2";
  if (part.sort_order === 3) return "Part 3";
  return `Part ${part.sort_order}`;
};

window.TW.partForQuestion = function partForQuestion(question, parts) {
  return parts.find((part) => part.study4_part_id === question.study4_part_id) || null;
};

window.TW.answerKey = function answerKey(question) {
  return `toeic-sw-writing-answer:${question.study4_test_id}:${question.question_number}`;
};

window.TW.scoreKey = function scoreKey(question) {
  return `toeic-sw-writing-score:${question.study4_test_id}:${question.question_number}`;
};

window.TW.attemptsKey = function attemptsKey(question) {
  return `toeic-sw-writing-attempts:${question.study4_test_id}:${question.question_number}`;
};

window.TW.countWords = function countWords(value) {
  return value.trim().split(/\s+/).filter(Boolean).length;
};

window.TW.localGet = function localGet(key) {
  return localStorage.getItem(key) || "";
};

window.TW.readJsonLocal = function readJsonLocal(key, fallback) {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return fallback;
  }
};

window.TW.writeJsonLocal = function writeJsonLocal(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
};

window.TW.isImageInputError = function isImageInputError(message) {
  if (!message) return false;
  const text = String(message).toLowerCase();
  return (
    text.includes("does not support image") ||
    text.includes("cannot read") && text.includes("image") ||
    text.includes("image input") ||
    text.includes("vision") ||
    text.includes("image_url") ||
    text.includes("multipart")
  );
};

window.TW.imageInputErrorMessage = function imageInputErrorMessage() {
  return "The current AI model does not support image input, so picture-based questions (Part 1) cannot be scored automatically.";
};
