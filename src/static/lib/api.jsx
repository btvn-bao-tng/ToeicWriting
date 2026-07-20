window.TW.apiFetch = async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401 && !options.suppressAuthExpired) {
    window.dispatchEvent(new CustomEvent("tw-auth-expired"));
  }

  return response;
};

window.TW.apiJson = async function apiJson(url, options = {}) {
  const response = await window.TW.apiFetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(data.detail || `${response.status} ${response.statusText}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
};

window.TW.createMockExam = async function createMockExam(study4_test_id, selected_part) {
  return window.TW.apiJson("/api/mock-exams", {
    method: "POST",
    body: JSON.stringify({ study4_test_id, selected_part }),
  });
};

window.TW.listMockExams = async function listMockExams() {
  return window.TW.apiJson("/api/mock-exams");
};

window.TW.getMockExam = async function getMockExam(mock_exam_id) {
  return window.TW.apiJson(`/api/mock-exams/${encodeURIComponent(mock_exam_id)}`);
};

window.TW.saveMockExamDraft = async function saveMockExamDraft(mock_exam_id, question_number, body) {
  return window.TW.apiJson(`/api/mock-exams/${encodeURIComponent(mock_exam_id)}/draft`, {
    method: "PUT",
    body: JSON.stringify({ question_number, body }),
  });
};

window.TW.submitMockExamStream = async function submitMockExamStream(mock_exam_id, callbacks = {}) {
  const response = await window.TW.apiFetch(`/api/mock-exams/${encodeURIComponent(mock_exam_id)}/submit`, {
    method: "POST",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw window.TW.enrichScoreError(new Error(data.detail || `${response.status} ${response.statusText}`));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  const handleEvent = (rawEvent) => {
    const lines = rawEvent.split("\n");
    const eventLine = lines.find((line) => line.startsWith("event:"));
    const dataLines = lines.filter((line) => line.startsWith("data:"));
    const event = eventLine ? eventLine.replace("event:", "").trim() : "message";
    const dataText = dataLines.length
      ? dataLines.map((line) => line.replace("data:", "").trim()).join("\n")
      : "{}";
    const data = JSON.parse(dataText || "{}") || {};

    if (event === "start") {
      callbacks.onStart?.(data.total_questions);
    } else if (event === "question_start") {
      callbacks.onQuestionStart?.(data.question_number);
    } else if (event === "delta") {
      callbacks.onDelta?.(data.question_number, data.content || "");
    } else if (event === "question_done") {
      callbacks.onQuestionDone?.(data.question_number, data);
    } else if (event === "question_error") {
      callbacks.onQuestionError?.(data.question_number, data);
    } else if (event === "complete") {
      result = data;
      callbacks.onComplete?.(data);
    } else if (event === "done") {
      return;
    } else if (event === "error") {
      const error = new Error(data.detail || "AI stream failed");
      throw window.TW.enrichScoreError(error);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    events.forEach((rawEvent) => {
      if (rawEvent.trim()) handleEvent(rawEvent);
    });
  }

  if (buffer.trim()) handleEvent(buffer);
  return result;
};

window.TW.enrichScoreError = function enrichScoreError(error) {
  const { isImageInputError, imageInputErrorMessage } = window.TW;
  if (isImageInputError(error.message)) {
    error.message = `${imageInputErrorMessage()} Original error: ${error.message}`;
  }
  return error;
};

window.TW.streamScore = async function streamScore(question, answer, callbacks = {}) {
  const response = await window.TW.apiFetch("/api/score/stream", {
    method: "POST",
    body: JSON.stringify({
      study4_test_id: question.study4_test_id,
      question_number: question.question_number,
      answer,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw window.TW.enrichScoreError(new Error(data.detail || `${response.status} ${response.statusText}`));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let fullText = "";

  const handleEvent = (rawEvent) => {
    const lines = rawEvent.split("\n");
    const eventLine = lines.find((line) => line.startsWith("event:"));
    const dataLines = lines.filter((line) => line.startsWith("data:"));
    const event = eventLine ? eventLine.replace("event:", "").trim() : "message";
    const dataText = dataLines.length ? dataLines.map((line) => line.replace("data:", "").trim()).join("\n") : "{}";
    const data = JSON.parse(dataText || "{}");

    if (event === "start") {
      callbacks.onStart?.(data.attempt_id);
    } else if (event === "delta") {
      fullText += data.content || "";
      callbacks.onDelta?.(fullText);
    } else if (event === "done") {
      return;
    } else if (event === "error") {
      const error = new Error(data.detail || "AI stream failed");
      error.attemptId = data.attempt_id;
      throw window.TW.enrichScoreError(error);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    events.forEach((rawEvent) => {
      if (rawEvent.trim()) handleEvent(rawEvent);
    });
  }

  if (buffer.trim()) handleEvent(buffer);
  return fullText;
};

window.TW.generateVocab = async function generateVocab(study4_test_id, question_number, attemptId) {
  return window.TW.apiJson("/api/vocab", {
    method: "POST",
    body: JSON.stringify({
      study4_test_id,
      question_number,
      ...(attemptId ? { attempt_id: attemptId } : {}),
    }),
  });
};

window.TW.getVocab = async function getVocab(study4_test_id, question_number) {
  const qs = `study4_test_id=${encodeURIComponent(study4_test_id)}&question_number=${encodeURIComponent(question_number)}`;
  const response = await window.TW.apiFetch(`/api/vocab?${qs}`);
  if (response.status === 404) return null;
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
};

window.TW.getVocabDetail = async function getVocabDetail(term, topic, mainImageUrl, questionPrompt) {
  return window.TW.apiJson("/api/vocab/detail", {
    method: "POST",
    body: JSON.stringify({
      term,
      topic: topic || "",
      main_image_url: mainImageUrl || null,
      question_prompt: questionPrompt || "",
    }),
  });
};
