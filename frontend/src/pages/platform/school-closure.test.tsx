import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { platformApi } from "@/lib/api";
import { ok, renderWithQuery } from "@/test/render";
import { DeleteSchoolDialog, SuspendSchoolDialog } from "./school-closure";

const SCHOOL = { id: 7, name: "Unilag", slug: "unilag" };

describe("SuspendSchoolDialog", () => {
  it("needs a reason, then suspends with it", async () => {
    const post = vi.spyOn(platformApi, "post").mockResolvedValue(ok({}));
    const onOpenChange = vi.fn();
    renderWithQuery(<SuspendSchoolDialog school={SCHOOL} open onOpenChange={onOpenChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Suspend school" }));
    expect(screen.getByText("Give a reason. Only the Ordo team sees it.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText("Reason"), "Unpaid invoice");
    await userEvent.click(screen.getByRole("button", { name: "Suspend school" }));

    expect(post).toHaveBeenCalledWith("/schools/7/suspend/", { reason: "Unpaid invoice" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

describe("DeleteSchoolDialog", () => {
  it("only deletes once the slug is typed exactly", async () => {
    const post = vi.spyOn(platformApi, "post").mockResolvedValue(ok({}));
    renderWithQuery(<DeleteSchoolDialog school={SCHOOL} open onOpenChange={vi.fn()} />);

    const button = screen.getByRole("button", { name: "Delete school" });
    await userEvent.type(screen.getByLabelText(/to confirm/), "unila");
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/to confirm/), "g");
    expect(button).toBeEnabled();
    await userEvent.click(button);

    expect(post).toHaveBeenCalledWith("/schools/7/delete/", { confirm_slug: "unilag" });
  });
});
