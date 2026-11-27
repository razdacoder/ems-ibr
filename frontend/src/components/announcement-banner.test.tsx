import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SchoolPlan } from "@/api/school";
import { api } from "@/lib/api";
import { AnnouncementBanner } from "@/components/announcement-banner";
import { describeAgent } from "@/pages/platform/account";
import { ok, renderWithQuery } from "@/test/render";

function plan(announcements: SchoolPlan["announcements"]): SchoolPlan {
  return {
    name: "Unilag",
    slug: "unilag",
    status: "active",
    timezone: "Africa/Lagos",
    features: [],
    limits: { max_students: null, max_staff_users: null },
    usage: { students: 0, staff_users: 1 },
    support: null,
    announcements,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("AnnouncementBanner", () => {
  it("shows nothing without announcements", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(plan([])));
    const { container } = renderWithQuery(<AnnouncementBanner />);
    await vi.waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("lets information be dismissed and remembers it, but keeps warnings", async () => {
    vi.spyOn(api, "get").mockResolvedValue(
      ok(
        plan([
          { id: 1, message: "New feature", level: "info", ends_at: null },
          { id: 2, message: "Maintenance tonight", level: "warning", ends_at: null },
        ]),
      ),
    );
    renderWithQuery(<AnnouncementBanner />);

    expect(await screen.findByText("New feature")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Dismiss" })).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));

    expect(screen.queryByText("New feature")).not.toBeInTheDocument();
    expect(screen.getByText("Maintenance tonight")).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("ordo:dismissed-announcements") ?? "[]")).toEqual([1]);
  });
});

describe("describeAgent", () => {
  it("names the browser and system", () => {
    expect(
      describeAgent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      ),
    ).toBe("Chrome on macOS");
    expect(describeAgent("Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0")).toBe(
      "Firefox on Linux",
    );
    expect(describeAgent("")).toBe("Unknown device");
  });
});
