import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SchoolPlan } from "@/api/school";
import { api, getToken, setToken } from "@/lib/api";
import { SupportBanner, timeLeft } from "@/components/support-banner";
import { ok, renderWithQuery } from "@/test/render";

function plan(support: SchoolPlan["support"]): SchoolPlan {
  return {
    name: "Unilag",
    slug: "unilag",
    status: "active",
    timezone: "Africa/Lagos",
    features: [],
    limits: { max_students: null, max_staff_users: null },
    usage: { students: 0, staff_users: 1 },
    support,
  };
}

const assign = vi.fn();

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  assign.mockReset();
  localStorage.clear();
});

function stubLocation() {
  vi.stubGlobal("location", { ...window.location, assign, pathname: "/" });
}

describe("timeLeft", () => {
  it("counts down in minutes and seconds, never below zero", () => {
    const now = Date.parse("2026-10-11T10:00:00Z");
    expect(timeLeft("2026-10-11T10:59:05Z", now)).toBe("59:05");
    expect(timeLeft("2026-10-11T09:59:00Z", now)).toBe("00:00");
  });
});

describe("SupportBanner", () => {
  it("shows nothing for a school user", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(plan(null)));
    const { container } = renderWithQuery(<SupportBanner />);
    await vi.waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("names the admin and the time left", async () => {
    const expires = new Date(Date.now() + 30 * 60_000 + 500).toISOString();
    vi.spyOn(api, "get").mockResolvedValue(
      ok(plan({ active: true, expires_at: expires, admin_name: "Tobi" })),
    );
    renderWithQuery(<SupportBanner />);
    const banner = await screen.findByRole("status");
    expect(banner).toHaveTextContent("Ordo support session (Tobi), ends in 30:00");
  });

  it("ends the session and signs out", async () => {
    stubLocation();
    setToken("support-token");
    const expires = new Date(Date.now() + 60_000).toISOString();
    vi.spyOn(api, "get").mockResolvedValue(
      ok(plan({ active: true, expires_at: expires, admin_name: "Tobi" })),
    );
    const post = vi.spyOn(api, "post").mockResolvedValue(ok(null));
    renderWithQuery(<SupportBanner />);

    await userEvent.click(await screen.findByRole("button", { name: "End session" }));

    expect(post).toHaveBeenCalledWith("/support/end/");
    expect(getToken()).toBeNull();
    expect(assign).toHaveBeenCalledWith("/login");
  });

  it("signs out on its own when the time is up", async () => {
    stubLocation();
    setToken("support-token");
    const expires = new Date(Date.now() - 1_000).toISOString();
    vi.spyOn(api, "get").mockResolvedValue(
      ok(plan({ active: true, expires_at: expires, admin_name: "Tobi" })),
    );
    renderWithQuery(<SupportBanner />);
    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith("/login"));
    expect(getToken()).toBeNull();
  });
});
