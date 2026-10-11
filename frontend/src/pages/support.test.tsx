import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AxiosError, type AxiosResponse } from "axios";
import { api, getToken, hasLiveSupportToken } from "@/lib/api";
import SupportPage from "@/pages/support";
import { ok } from "@/test/render";

vi.mock("@/components/theme-toggle", () => ({ ThemeToggle: () => null }));

const replace = vi.fn();

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  replace.mockReset();
  localStorage.clear();
});

describe("SupportPage", () => {
  it("swaps the ticket for a support token and opens the dashboard", async () => {
    vi.stubGlobal("location", { ...window.location, replace });
    const expires = new Date(Date.now() + 3_600_000).toISOString();
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue(ok({ token: "support-token", expires_at: expires }));

    render(<SupportPage ticket="abc" />);

    await vi.waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith("/support/redeem/", { ticket: "abc" });
    expect(getToken()).toBe("support-token");
    expect(hasLiveSupportToken()).toBe(true);
  });

  it("says the link no longer works when the ticket is gone", async () => {
    const response = {
      status: 410,
      data: { detail: "This support link has expired.", code: "support_ticket_gone" },
    } as AxiosResponse;
    vi.spyOn(api, "post").mockRejectedValue(
      new AxiosError("Gone", "410", undefined, undefined, response),
    );

    render(<SupportPage ticket="used" />);

    expect(await screen.findByRole("heading", { name: "Link no longer works" })).toBeInTheDocument();
    expect(screen.getByText(/This support link has expired\./)).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("does nothing without a ticket", () => {
    const post = vi.spyOn(api, "post");
    render(<SupportPage />);
    expect(screen.getByRole("heading", { name: "Link no longer works" })).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });
});
