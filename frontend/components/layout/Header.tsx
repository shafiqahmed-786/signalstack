import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface HeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  breadcrumb?: { label: string; href?: string }[];
  className?: string;
}

export function Header({ title, subtitle, action, breadcrumb, className }: HeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 mb-8", className)}>
      <div className="space-y-0.5">
        {breadcrumb && breadcrumb.length > 0 && (
          <nav className="flex items-center gap-1.5 mb-1" aria-label="Breadcrumb">
            {breadcrumb.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-ink-muted text-xs">/</span>}
                {crumb.href ? (
                  <a
                    href={crumb.href}
                    className="text-xs text-ink-muted hover:text-ai transition-colors font-mono"
                  >
                    {crumb.label}
                  </a>
                ) : (
                  <span className="text-xs text-ink-muted font-mono">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <h1 className="text-2xl font-semibold text-ink tracking-tight">{title}</h1>
        {subtitle && (
          <p className="text-sm text-ink-secondary">{subtitle}</p>
        )}
      </div>
      {action && (
        <div className="shrink-0 flex items-center gap-2">{action}</div>
      )}
    </div>
  );
}