window.TW.streamScore = async function streamScore(question, answer, onDelta) {
  const response = await fetch("/api/score/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    const eventLine = rawEvent.split("\n").find((line) => line.startsWith("event:"));
    const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data:"));
    const event = eventLine ? eventLine.replace("event:", "").trim() : "message";
    const dataText = dataLine ? dataLine.replace("data:", "").trim() : "{}";
    const data = JSON.parse(dataText || "{}");

    if (event === "delta") {
      fullText += data.content || "";
      onDelta(fullText);
    } else if (event === "error") {
      throw new Error(data.detail || "AI stream failed");
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
