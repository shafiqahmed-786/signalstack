"use client";

import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { CommandPalette } from "@/components/CommandPalette";

/**
 * Dashboard shell layout — marked "use client" because:
 *   - ErrorBoundary is a class component (React error boundaries must be client-side)
 *   - CommandPalette uses hooks (useState, useEffect, useRouter)
 *   - AppShell uses usePathname
 *
 * AppShell provides the fixed Sidebar + main content area.
 * CommandPalette is mounted once here; it self-registers cmd+k globally.
 * ErrorBoundary catches runtime failures in any dashboard page.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary showReset resetLabel="Reload dashboard">
      <AppShell>
        {children}
        <CommandPalette />
      </AppShell>
    </ErrorBoundary>
  );
}