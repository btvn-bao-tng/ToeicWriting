const Skeleton = function Skeleton({ className = "" }) {
  return <div className={`tw-skel rounded-[6px] ${className}`} />;
};
window.TW.Skeleton = Skeleton;

const SkeletonPill = function SkeletonPill({ className = "" }) {
  return <span className={`tw-skel inline-block h-6 rounded-full ${className}`} />;
};
window.TW.SkeletonPill = SkeletonPill;

const QuestionCardSkeleton = function QuestionCardSkeleton() {
  return (
    <article className="mb-2.5 overflow-hidden rounded-[18px] border border-hairline bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-hairline bg-parchment px-3 py-2.5">
        <Skeleton className="h-4 w-28" />
        <SkeletonPill className="w-16" />
      </div>
      <div className="px-3 py-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(300px,1fr)_minmax(300px,1fr)]">
          <div className="min-w-0 space-y-2.5">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="mt-1 h-28 w-full max-w-[min(100%,520px)]" />
          </div>
          <div className="min-w-0 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
        <Skeleton className="mt-3 h-20 w-full rounded-[18px]" />
      </div>
    </article>
  );
};
window.TW.QuestionCardSkeleton = QuestionCardSkeleton;

const TestListSkeleton = function TestListSkeleton({ count = 6 }) {
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-5 w-80 max-w-full" />
      </div>
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="rounded-[18px] border border-hairline bg-white p-6">
            <Skeleton className="h-5 w-2/3" />
            <div className="mt-3 flex flex-wrap gap-2">
              <SkeletonPill className="w-16" />
              <SkeletonPill className="w-20" />
              <SkeletonPill className="w-14" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
window.TW.TestListSkeleton = TestListSkeleton;

const TestActionsSkeleton = function TestActionsSkeleton() {
  return (
    <section className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <section className="rounded-[18px] border border-hairline bg-white p-6 sm:p-8">
        <Skeleton className="h-10 w-3/4" />
        <div className="mt-4 flex flex-wrap gap-2">
          <SkeletonPill className="w-24" />
          <SkeletonPill className="w-24" />
          <SkeletonPill className="w-20" />
        </div>
        <Skeleton className="mt-5 h-5 w-2/3" />
        <div className="mt-7 grid gap-3 sm:grid-cols-2">
          <Skeleton className="min-h-[68px] rounded-[18px]" />
          <Skeleton className="min-h-[68px] rounded-[18px]" />
        </div>
      </section>
    </section>
  );
};
window.TW.TestActionsSkeleton = TestActionsSkeleton;

const PracticeSkeleton = function PracticeSkeleton({ count = 3 }) {
  return (
    <>
      <Skeleton className="mb-3 h-4 w-32" />
      <section className="mb-3 rounded-[18px] border border-hairline bg-white p-4 sm:p-6">
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="mt-2 h-4 w-24" />
        <div className="mt-3 flex flex-wrap gap-2">
          <SkeletonPill className="w-20" />
          <SkeletonPill className="w-16" />
          <SkeletonPill className="w-24" />
          <SkeletonPill className="w-20" />
        </div>
      </section>
      <section className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[18px] border border-hairline bg-parchment p-2">
        <div className="flex flex-wrap gap-1.5">
          <Skeleton className="h-9 w-20 rounded-full" />
          <Skeleton className="h-9 w-16 rounded-full" />
          <Skeleton className="h-9 w-16 rounded-full" />
          <Skeleton className="h-9 w-16 rounded-full" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-36 rounded-full" />
          <Skeleton className="h-9 w-36 rounded-full" />
        </div>
      </section>
      {Array.from({ length: count }).map((_, i) => (
        <QuestionCardSkeleton key={i} />
      ))}
    </>
  );
};
window.TW.PracticeSkeleton = PracticeSkeleton;

const MockExamSkeleton = function MockExamSkeleton() {
  return (
    <section className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <section className="mb-3 rounded-[18px] border border-hairline bg-white p-4 sm:p-6">
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="mt-2 h-4 w-24" />
        <div className="mt-3 flex flex-wrap gap-2">
          <SkeletonPill className="w-20" />
          <SkeletonPill className="w-28" />
          <SkeletonPill className="w-24" />
        </div>
      </section>
      <section className="rounded-[18px] border border-hairline bg-white p-5 sm:p-6">
        <Skeleton className="mb-3 h-6 w-32" />
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-9 w-20 rounded-full" />
          <Skeleton className="h-9 w-20 rounded-full" />
          <Skeleton className="h-9 w-20 rounded-full" />
          <Skeleton className="h-9 w-24 rounded-full" />
        </div>
        <div className="mt-5 flex items-center gap-3">
          <Skeleton className="h-11 w-40 rounded-full" />
          <Skeleton className="h-5 w-28" />
        </div>
      </section>
    </section>
  );
};
window.TW.MockExamSkeleton = MockExamSkeleton;

const MockExamTakingSkeleton = function MockExamTakingSkeleton({ count = 3 }) {
  return (
    <section className="space-y-4">
      <section className="rounded-[18px] border border-hairline bg-white p-4 sm:p-6">
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="mt-2 h-4 w-24" />
        <div className="mt-3 flex flex-wrap gap-2">
          <SkeletonPill className="w-20" />
          <SkeletonPill className="w-28" />
          <SkeletonPill className="w-24" />
        </div>
      </section>
      <div className="rounded-[18px] border border-hairline bg-parchment/80 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Skeleton className="h-5 w-48" />
          <div className="flex flex-wrap items-center gap-2">
            <Skeleton className="h-8 w-24 rounded-full" />
            <Skeleton className="h-8 w-32 rounded-full" />
            <Skeleton className="h-8 w-24 rounded-full" />
          </div>
        </div>
      </div>
      {Array.from({ length: count }).map((_, i) => (
        <QuestionCardSkeleton key={i} />
      ))}
    </section>
  );
};
window.TW.MockExamTakingSkeleton = MockExamTakingSkeleton;

const VocabGridSkeleton = function VocabGridSkeleton({ count = 6 }) {
  return (
    <div className="h-full overflow-auto p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex flex-col overflow-hidden rounded-[10px] border border-hairline bg-white">
            <Skeleton className="aspect-[3/2] w-full rounded-none" />
            <div className="flex flex-col gap-1.5 p-2.5">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-12" />
              </div>
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
              <Skeleton className="h-8 w-full rounded-[4px]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
window.TW.VocabGridSkeleton = VocabGridSkeleton;
