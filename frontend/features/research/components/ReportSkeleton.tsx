import { cn } from "@/lib/utils";

function SkeletonLine({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-3 rounded-md bg-gradient-to-r from-card via-surface to-card bg-[length:200%_100%] animate-shimmer",
        className
      )}
    />
  );
}

export function ReportSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Company cards skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex justify-between">
              <div className="space-y-1.5">
                <SkeletonLine className="w-12" />
                <SkeletonLine className="w-28" />
              </div>
              <SkeletonLine className="w-16 h-5" />
            </div>
            <SkeletonLine className="w-24 h-6" />
            <div className="grid grid-cols-2 gap-2">
              {[1, 2, 3, 4].map((j) => (
                <SkeletonLine key={j} className="w-full" />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Executive summary skeleton */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <SkeletonLine className="w-40 h-4" />
        <div className="space-y-2">
          <SkeletonLine className="w-full" />
          <SkeletonLine className="w-11/12" />
          <SkeletonLine className="w-4/5" />
          <SkeletonLine className="w-full" />
          <SkeletonLine className="w-3/4" />
        </div>
      </div>

      {/* Sections skeleton */}
      {[1, 2].map((i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-5 space-y-3">
          <SkeletonLine className="w-32 h-4" />
          <div className="space-y-2">
            {[1, 2, 3].map((j) => (
              <SkeletonLine key={j} className={j === 2 ? "w-5/6" : "w-full"} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}