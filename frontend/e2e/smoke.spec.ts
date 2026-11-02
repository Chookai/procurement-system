import { expect, test } from "@playwright/test";
import {
  openRequisition,
  registerRow,
  signIn,
  signOut,
  uniqueTitle,
} from "./fixtures";

// End-to-end PR approval journey against a disposable, isolated stack.
//
// Aina (requester) creates and submits a purchase requisition. Ben (approver)
// signs in, approves it, and the approved state plus the expected next action
// become visible. A separate assertion confirms Aina never sees an approval
// action for her own request; backend authorization remains authoritative.
test.describe("PR create → submit → approve", () => {
  test("Aina drafts and submits a PR; Ben approves it", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const title = uniqueTitle("Pump seals for MV Harbor One");

    // --- Aina signs in and creates a draft. ---
    await page.goto("/");
    await signIn(page, "aina");

    await page.getByRole("button", { name: "Create PR", exact: true }).click();
    await page.getByLabel("Title", { exact: true }).fill(title);
    await page.getByLabel("Required date", { exact: true }).fill("2026-12-01");
    await page.getByLabel("Vessel", { exact: true }).fill("MV Harbor One");
    await page.getByLabel("Location", { exact: true }).fill("Port Klang");
    await page
      .getByLabel("Business purpose", { exact: true })
      .fill("Replace worn pump seals before departure");
    await page
      .getByLabel("Suggested supplier", { exact: false })
      .fill("Demo Marine Supply");
    await page.getByLabel("Description", { exact: true }).fill("Pump seals");
    await page.getByLabel("Quantity", { exact: true }).fill("10");
    await page
      .getByLabel("Unit estimate (MYR)", { exact: true })
      .fill("200.00");
    await page.getByRole("button", { name: "Save draft", exact: true }).click();

    // The saved record opens and its estimated value is rendered.
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".total")).toContainText("2,000");

    // --- Refresh: the saved record and session persist. ---
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Purchase requisitions", exact: true }),
    ).toBeVisible();
    await openRequisition(page, title);
    await expect(page.locator(".total")).toContainText("2,000");

    // --- Submit for approval. ---
    await page
      .getByRole("button", { name: "Submit for approval", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Submitted to Ben");
    await expect(page.locator(".status").first()).toContainText(
      "Awaiting PR approval",
    );

    // --- Aina cannot see an approval action for her own request. ---
    await expect(
      page.getByRole("button", { name: "Approve PR", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Return for changes", exact: true }),
    ).toHaveCount(0);

    // --- Ben signs in and approves the request. ---
    await signOut(page);
    await signIn(page, "ben");
    await openRequisition(page, title);

    await expect(
      page.getByRole("button", { name: "Approve PR", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Approve PR", exact: true }).click();

    await expect(page.getByRole("status")).toContainText("PR approved");
    await expect(page.locator(".status").first()).toContainText(
      "PR approved · Ready for PO",
    );

    // Expected next action is visible to the team.
    const row = registerRow(page, title);
    await expect(row).toContainText("Next: Prepare PO");
    await expect(row).toContainText("Chloe · Buyer");

    // The approval is recorded in the activity trail.
    await expect(page.locator(".activity")).toContainText("Approved PR");

    expect(pageErrors).toEqual([]);
  });
});
