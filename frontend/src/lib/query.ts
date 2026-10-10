import { QueryClient } from "@tanstack/react-query";

/**
 * One per app instance: the root route creates it, so each server render
 * gets its own cache and nothing leaks between visitors.
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}
