import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 text-center",
        className
      )}
    >
      {icon && (
        <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center mb-4 text-ink-muted">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-medium text-ink mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-ink-muted max-w-xs leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}