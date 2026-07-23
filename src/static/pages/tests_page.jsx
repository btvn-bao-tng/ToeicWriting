window.TW.TestsPage = function TestsPage({ app }) {
  const { TestList, TestListSkeleton } = window.TW;
  const { tests, loadingTests, selectedId, handleSelectTest } = app;
  if (loadingTests && !tests.length) return <TestListSkeleton />;
  return <TestList tests={tests} selectedId={selectedId} onSelect={handleSelectTest} />;
};
