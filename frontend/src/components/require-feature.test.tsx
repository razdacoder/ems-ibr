import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { api } from "@/lib/api";
import { RequireFeature } from "@/components/route-guards";
import { schoolPlan } from "@/test/fixtures";
import { ok, renderWithQuery } from "@/test/render";

describe("RequireFeature", () => {
  it("shows the page when the plan includes the feature", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(schoolPlan()));

    renderWithQuery(
      <RequireFeature feature="seat_allocation">
        <h1>Allocation</h1>
      </RequireFeature>,
    );

    expect(await screen.findByRole("heading", { name: "Allocation" })).toBeInTheDocument();
  });

  it("explains plainly when the plan leaves the feature off", async () => {
    vi.spyOn(api, "get").mockResolvedValue(ok(schoolPlan({ features: ["exports"] })));

    renderWithQuery(
      <RequireFeature feature="seat_allocation">
        <h1>Allocation</h1>
      </RequireFeature>,
    );

    expect(await screen.findByText("Seat allocation isn't in your plan")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Contact Ordo");
    expect(screen.queryByRole("heading", { name: "Allocation" })).not.toBeInTheDocument();
  });

  it("holds the page back while the plan loads", () => {
    vi.spyOn(api, "get").mockReturnValue(new Promise(() => {}));

    renderWithQuery(
      <RequireFeature feature="seat_allocation">
        <h1>Allocation</h1>
      </RequireFeature>,
    );

    expect(screen.queryByRole("heading", { name: "Allocation" })).not.toBeInTheDocument();
  });

  it("shows the page if the plan can't be loaded, since the server still refuses", async () => {
    const get = vi.spyOn(api, "get").mockRejectedValue(new Error("offline"));

    renderWithQuery(
      <RequireFeature feature="seat_allocation">
        <h1>Allocation</h1>
      </RequireFeature>,
    );

    expect(await screen.findByRole("heading", { name: "Allocation" })).toBeInTheDocument();
    expect(get).toHaveBeenCalled();
  });
});
