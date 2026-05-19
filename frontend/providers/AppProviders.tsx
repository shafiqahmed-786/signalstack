"use client";

import { type ReactNode, useState } from "react";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

const CLERK_APPEARANCE = {
  variables: {
    colorBackground: "#0f1520",
    colorInputBackground: "#141c2e",
    colorText: "#e8ecf4",
    colorTextSecondary: "#8a93b2",
    colorPrimary: "#0fd4b0",
    colorDanger: "#ef4444",
    borderRadius: "0.75rem",
    fontFamily: "var(--font-ibm-plex-sans)",
  },
  elements: {
    card: "bg-surface border border-border shadow-2xl",
    formFieldInput: "bg-card border-border text-ink focus:border-ai",
    footerActionLink: "text-ai hover:text-ai/80",
    headerTitle: "text-ink",
    headerSubtitle: "text-ink-secondary",
  },
};

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: (count, error) => {
          const status = (error as { status?: number })?.status;
          if (status && status >= 400 && status < 500) return false;
          return count < 2;
        },
      },
      mutations: {
        retry: 1,
      },
    },
  });
}

/**
 * Consolidated root application providers.
 *
 * Layer order (outermost → innermost):
 *   ErrorBoundary → ClerkProvider → QueryClientProvider → children
 *
 * Usage in app/layout.tsx:
 *   import { AppProviders } from "@/providers/AppProviders";
 *   <AppProviders>{children}</AppProviders>
 */
export function AppProviders({ children }: { children: ReactNode }) {
  // One stable QueryClient per browser session
  const [queryClient] = useState(makeQueryClient);

  return (
    <ErrorBoundary
      showReset
      resetLabel="Reload"
      onError={(err) =>
        process.env.NODE_ENV === "development" &&
        console.error("[AppProviders] Uncaught error:", err)
      }
    >
      <ClerkProvider appearance={CLERK_APPEARANCE}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </ClerkProvider>
    </ErrorBoundary>
  );
}