import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useHasFeature } from "@/api/school";
import { schoolPlan } from "@/test/fixtures";
import { ok } from "@/test/render";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useHasFeature", () => {
  it("is true until the plan loads, so a paying school never sees a flicker", () => {
    vi.spyOn(api, "get").mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useHasFeature("seat_allocation"), { wrapper });

    expect(result.current).toBe(true);
  });

  it("follows the plan's features once loaded", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(schoolPlan({ features: ["exports"] })));

    const { result } = renderHook(
      () => [useHasFeature("exports"), useHasFeature("seat_allocation")],
      { wrapper },
    );

    await waitFor(() => expect(result.current).toEqual([true, false]));
  });

  it("loads the plan from /school/ once for every caller", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue(ok(schoolPlan()));

    renderHook(() => [useHasFeature("exports"), useHasFeature("branding")], { wrapper });

    await waitFor(() => expect(get).toHaveBeenCalledTimes(1));
    expect(get).toHaveBeenCalledWith("/school/");
  });
});
