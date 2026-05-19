import { getApiBase } from "@/lib/api";
import type { ToolName, ConfidenceLevel } from "@/types/api";

export type SSEEventHandler = (event: string, data: unknown) => void;
export type SSEErrorHandler = (error: Error) => void;

export interface SSEClientOptions {
  token: string;
  query: string;
  companies?: string[];
  onEvent: SSEEventHandler;
  onError: SSEErrorHandler;
  onComplete: () => void;
}

// Parses raw SSE text chunks into (event, data) pairs
function* parseSSEChunks(raw: string): Generator<{ event: string; data: string }> {
  const lines = raw.split("\n");
  let currentEvent = "message";
  let dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      currentEvent = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    } else if (line === "" && dataLines.length > 0) {
      yield { event: currentEvent, data: dataLines.join("\n") };
      currentEvent = "message";
      dataLines = [];
    }
    // Skip comment lines (keepalive)
  }
}

export async function startResearchStream(options: SSEClientOptions): Promise<AbortController> {
  const controller = new AbortController();

  const doFetch = async () => {
    try {
      const response = await fetch(`${getApiBase()}/api/v1/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${options.token}`,
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          query: options.query,
          companies: options.companies?.length ? options.companies : undefined,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.error?.message ?? `HTTP ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Only process complete SSE chunks (terminated by \n\n)
        const boundary = buffer.lastIndexOf("\n\n");
        if (boundary === -1) continue;

        const toProcess = buffer.slice(0, boundary + 2);
        buffer = buffer.slice(boundary + 2);

        for (const { event, data } of parseSSEChunks(toProcess)) {
          try {
            const parsed = JSON.parse(data);
            options.onEvent(event, parsed);
          } catch {
            // Non-JSON data (e.g., keepalive content) — skip
          }
        }
      }

      options.onComplete();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      options.onError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  doFetch();
  return controller;
}