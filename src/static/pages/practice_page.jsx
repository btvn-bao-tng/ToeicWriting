window.TW.PracticePage = function PracticePage({ app }) {
  const { TestSummary, PartTabs, QuestionCard, EmptyState } = window.TW;
  const {
    currentPayload,
    questions,
    parts,
    modeLabel,
    selectedPart,
    handleSelectPart,
    handleScoreVisible,
    handleClearVisible,
    scoringVisible,
    isGuest,
    handleLogin,
    scoringNumbers,
    getDraft,
    getAttempts,
    handleDraftChange,
    handleScore,
    handleClear,
    rememberQuestion,
    revisionSavedKeys,
    handleToggleRevision,
    navigate,
  } = app;

  return (
    <>
      <button
        type="button"
        onClick={() => navigate({ view: "actions", testId: currentPayload.test.study4_test_id, mockExamId: null })}
        className="mb-3 text-[14px] font-normal text-action hover:underline"
      >
        ← Back to options
      </button>
      <TestSummary test={currentPayload.test} questions={questions} modeLabel={modeLabel} />
      <PartTabs
        payload={currentPayload}
        selectedPart={selectedPart}
        onSelectPart={handleSelectPart}
        onScoreVisible={handleScoreVisible}
        onClearVisible={handleClearVisible}
        scoringVisible={scoringVisible}
        allowScoring={!isGuest}
        onLogin={handleLogin}
      />
      {questions.length ? (
        questions.map((question, index) => (
          <QuestionCard
            key={question.id}
            question={question}
            index={index}
            parts={parts}
            draft={getDraft(question)}
            attempts={getAttempts(question)}
            isScoring={scoringNumbers.has(question.question_number)}
            onDraftChange={handleDraftChange}
            onScore={handleScore}
            onClear={handleClear}
            onActivate={rememberQuestion}
            allowScoring={!isGuest}
            onLogin={handleLogin}
            revisionSavedKeys={revisionSavedKeys}
            onToggleRevision={handleToggleRevision}
          />
        ))
      ) : (
        <EmptyState>No questions found for this part.</EmptyState>
      )}
    </>
  );
};
