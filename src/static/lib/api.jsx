window.TW.apiFetch = async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
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
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
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
      throw error;
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
