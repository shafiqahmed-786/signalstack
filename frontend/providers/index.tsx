"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

const clerkAppearance = {
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

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      })
  );

  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  return (
    <ClerkProvider publishableKey={publishableKey || undefined} appearance={clerkAppearance}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ClerkProvider>
  );
}