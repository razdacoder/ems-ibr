import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { api } from "@/lib/api";
import { PlanUsage } from "@/components/plan-usage";
import { schoolPlan } from "@/test/fixtures";
import { ok, renderWithQuery } from "@/test/render";

function withPlan(plan: ReturnType<typeof schoolPlan>) {
  vi.spyOn(api, "get").mockResolvedValue(ok(plan));
}

describe("PlanUsage", () => {
  it("shows how much of a student cap is used", async () => {
    withPlan(schoolPlan({ limits: { max_students: 2000, max_staff_users: null }, usage: { students: 1240, staff_users: 1 } }));

    renderWithQuery(<PlanUsage kind="students" />);

    const line = await screen.findByText("1,240 of 2,000 students used");
    expect(line).not.toHaveClass("text-destructive");
    expect(line).not.toHaveAttribute("title");
  });

  it("warns once the cap is reached", async () => {
    withPlan(schoolPlan({ limits: { max_students: null, max_staff_users: 3 }, usage: { students: 0, staff_users: 3 } }));

    renderWithQuery(<PlanUsage kind="staff_users" />);

    const line = await screen.findByText("3 of 3 staff accounts used");
    expect(line).toHaveClass("text-destructive");
    expect(line).toHaveAttribute("title", "Your plan's limit is reached. Contact Ordo to raise it.");
  });

  it("also warns when usage is over a lowered cap", async () => {
    withPlan(schoolPlan({ limits: { max_students: 10, max_staff_users: null }, usage: { students: 15, staff_users: 1 } }));

    renderWithQuery(<PlanUsage kind="students" />);

    expect(await screen.findByText("15 of 10 students used")).toHaveClass("text-destructive");
  });

  it("uses the singular for a cap of one", async () => {
    withPlan(schoolPlan({ limits: { max_students: null, max_staff_users: 1 }, usage: { students: 0, staff_users: 0 } }));

    renderWithQuery(<PlanUsage kind="staff_users" />);

    expect(await screen.findByText("0 of 1 staff account used")).toBeInTheDocument();
  });

  it("shows nothing when the plan is unlimited", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue(ok(schoolPlan()));

    const { container } = renderWithQuery(<PlanUsage kind="students" />);

    await vi.waitFor(() => expect(get).toHaveBeenCalledWith("/school/"));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing while the plan is loading or failed", async () => {
    vi.spyOn(api, "get").mockRejectedValue(new Error("offline"));

    const { container } = renderWithQuery(<PlanUsage kind="students" />);

    expect(container).toBeEmptyDOMElement();
  });
});
