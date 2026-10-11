import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

/** Render inside a fresh React Query cache, with retries off so errors show at once. */
export function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}

/** An axios style response for a mocked call. */
export const ok = <T,>(data: T) => ({ data, status: 200, statusText: "OK", headers: {}, config: {} });
