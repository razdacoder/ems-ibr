import { describe, expect, it, vi } from "vitest";
import { act, screen } from "@testing-library/react";
import type { SchoolStatusInfo } from "@/api/school";
import { api, clearToken, SCHOOL_CLOSED_EVENT, setSupportExpiry, setToken } from "@/lib/api";
import { RequireOpenSchool } from "@/components/route-guards";
import { ok, renderWithQuery } from "@/test/render";

vi.mock("@/components/theme-toggle", () => ({ ThemeToggle: () => null }));

const status = (s: SchoolStatusInfo["status"]): SchoolStatusInfo => ({ name: "Unilag", status: s });

function renderGate() {
  return renderWithQuery(
    <RequireOpenSchool>
      <h1>Dashboard</h1>
    </RequireOpenSchool>,
  );
}

describe("RequireOpenSchool", () => {
  it("shows the pages while the school is active", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(status("active")));
    renderGate();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it.each(["suspended", "pending_deletion"] as const)(
    "shows the fixed suspended message when %s",
    async (s) => {
      vi.spyOn(api, "get").mockResolvedValue(ok(status(s)));
      renderGate();
      expect(await screen.findByRole("heading", { name: "Access is suspended" })).toBeInTheDocument();
      expect(screen.getByText("This school's access is suspended. Contact Ordo.")).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Dashboard" })).not.toBeInTheDocument();
    },
  );

  it.each(["provisioning", "failed"] as const)("shows the being set up page when %s", async (s) => {
    vi.spyOn(api, "get").mockResolvedValue(ok(status(s)));
    renderGate();
    expect(await screen.findByRole("heading", { name: "Being set up" })).toBeInTheDocument();
  });

  it("checks again when a call is refused mid session", async () => {
    const get = vi
      .spyOn(api, "get")
      .mockResolvedValueOnce(ok(status("active")))
      .mockResolvedValueOnce(ok(status("suspended")));
    renderGate();
    await screen.findByRole("heading", { name: "Dashboard" });

    act(() => {
      window.dispatchEvent(new Event(SCHOOL_CLOSED_EVENT));
    });

    expect(await screen.findByRole("heading", { name: "Access is suspended" })).toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("lets Ordo support into a suspended school until its time is up", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(status("suspended")));
    setToken("support-token");
    setSupportExpiry(new Date(Date.now() + 60_000).toISOString());
    const live = renderGate();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    live.unmount();

    setSupportExpiry(new Date(Date.now() - 1_000).toISOString());
    renderGate();
    expect(await screen.findByRole("heading", { name: "Access is suspended" })).toBeInTheDocument();
    clearToken();
  });

  it("lets the pages try when the status can't be loaded", async () => {
    vi.spyOn(api, "get").mockRejectedValue(new Error("offline"));
    renderGate();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });
});
