const { SCORE_RESULT_BASE } = window.TW.classes;

window.TW.renderInlineMarkdown = function renderInlineMarkdown(value, keyPrefix) {
  const nodes = [];
  const pattern = /(`[^`]+`|\*\*[^*]+(?:\*(?!\*)[^*]+)*\*\*)/g;
  let lastIndex = 0;
  let matchIndex = 0;

  String(value || "").replace(pattern, (match, _unused, offset) => {
    if (offset > lastIndex) nodes.push(String(value).slice(lastIndex, offset));
    if (match.startsWith("`")) {
      nodes.push(
        <code key={`${keyPrefix}-code-${matchIndex}`} className="rounded bg-slate-100 px-1 py-0.5 text-[0.92em] text-slate-950">
          {match.slice(1, -1)}
        </code>
      );
    } else {
      nodes.push(
        <strong key={`${keyPrefix}-strong-${matchIndex}`} className="font-semibold text-slate-950">
          {match.slice(2, -2)}
        </strong>
      );
    }
    lastIndex = offset + match.length;
    matchIndex += 1;
    return match;
  });

  if (lastIndex < String(value || "").length) nodes.push(String(value || "").slice(lastIndex));
  return nodes;
};

function scoreSections(markdown) {
  const normalized = String(markdown || "")
    .replace(/\r\n?/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (!normalized) return [{ title: "", lines: ["Thinking..."] }];

  const sections = [];
  let current = { title: "", lines: [] };
  const legacySectionLabels = new Set([
    "Advanced Examples (10/10)",
    "Advanced Grammar & Vocab to Reach 10/10",
    "Feedback",
  ]);

  const legacyHeading = (line) => {
    const score = line.match(/^Score:\s*(.+)$/i);
    if (score) return { title: "Score", firstLine: score[1].trim() };

    const label = line.match(/^([^:]{1,80}):\s*$/);
    if (label && legacySectionLabels.has(label[1].trim())) {
      return { title: label[1].trim(), firstLine: "" };
    }

    return null;
  };

  normalized.split("\n").forEach((line) => {
    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+)$/);
    const legacy = !heading ? legacyHeading(line.trim()) : null;
    if (heading || legacy) {
      if (current.title || current.lines.some((item) => item.trim())) sections.push(current);
      current = {
        title: heading ? heading[2].trim() : legacy.title,
        lines: legacy?.firstLine ? [legacy.firstLine] : [],
      };
      return;
    }
    current.lines.push(line);
  });

  if (current.title || current.lines.some((item) => item.trim())) sections.push(current);
  return sections;
}

function ScoreBlocks({ lines, sectionIndex }) {
  const blocks = [];
  let listType = null;
  let listItems = [];
  const { renderInlineMarkdown } = window.TW;

  const flushList = () => {
    if (!listItems.length) return;
    const Tag = listType === "ol" ? "ol" : "ul";
    blocks.push(
      <Tag key={`list-${sectionIndex}-${blocks.length}`} className={`${Tag === "ol" ? "list-decimal" : "list-disc"} space-y-1 pl-5`}>
        {listItems.map((item, itemIndex) => (
          <li key={itemIndex}>{renderInlineMarkdown(item, `li-${sectionIndex}-${itemIndex}`)}</li>
        ))}
      </Tag>
    );
    listType = null;
    listItems = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    const unordered = trimmed.match(/^[-*]\s+(.+)/);
    if (unordered) {
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listItems.push(unordered[1]);
      return;
    }

    const ordered = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (ordered) {
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listItems.push(ordered[1]);
      return;
    }

    if (listItems.length && /^\s{2,}\S/.test(line)) {
      listItems[listItems.length - 1] += ` ${trimmed}`;
      return;
    }

    flushList();
    if (trimmed.startsWith(">")) {
      blocks.push(
        <blockquote key={`quote-${sectionIndex}-${blocks.length}`} className="mb-2 border-l-4 border-teal-700 bg-teal-50/60 py-1.5 pl-3 text-slate-500 last:mb-0">
          {renderInlineMarkdown(trimmed.replace(/^>\s*/, ""), `quote-${sectionIndex}-${blocks.length}`)}
        </blockquote>
      );
    } else {
      blocks.push(
        <p key={`p-${sectionIndex}-${blocks.length}`} className="mb-2 last:mb-0">
          {renderInlineMarkdown(trimmed, `p-${sectionIndex}-${blocks.length}`)}
        </p>
      );
    }
  });

  flushList();
  return <>{blocks}</>;
}

window.TW.ScoreMarkdown = function ScoreMarkdown({ markdown }) {
  const { renderInlineMarkdown } = window.TW;
  return (
    <div className="grid overflow-hidden">
      {scoreSections(markdown).map((section, sectionIndex) => (
        <section key={sectionIndex} className="border-t border-slate-200 px-2.5 py-2.5 first:border-t-0 first:bg-teal-50/60">
          {section.title ? (
            <h3 className="mb-2 text-[15px] font-extrabold leading-tight text-slate-900">
              {renderInlineMarkdown(section.title, `h-${sectionIndex}`)}
            </h3>
          ) : null}
          <ScoreBlocks lines={section.lines} sectionIndex={sectionIndex} />
        </section>
      ))}
    </div>
  );
};

window.TW.ScoreResult = function ScoreResult({ score }) {
  const { ScoreMarkdown } = window.TW;
  if (!score?.text && score?.state !== "error") return null;

  const className = score.state === "error"
    ? `${SCORE_RESULT_BASE} block border-red-200 bg-red-50 p-3 text-red-800`
    : `${SCORE_RESULT_BASE} block ${score.state === "streaming" ? "text-slate-900" : ""}`;

  return (
    <div className={className}>
      {score.state === "error" ? score.text : <ScoreMarkdown markdown={score.text || "### Scoring\n\nThinking..."} />}
      {score.state === "streaming" ? <span className="ml-2 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-teal-700 align-[-2px]" /> : null}
    </div>
  );
};
