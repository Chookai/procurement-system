import { expect, type Page } from "@playwright/test";

// Synthetic, seeded demo identities. These users are created by the backend's
// `seed_users` on startup against the disposable test database; no manual
// preparation or historical records are required.
export const DEMO_PASSWORD = "harbor-demo";

export type SeededUser = "aina" | "ben" | "chloe" | "dinesh" | "eva";

export async function signIn(page: Page, username: SeededUser): Promise<void> {
  await expect(
    page.getByRole("heading", { name: "Sign in to procurement", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Purchase requisitions", exact: true }),
  ).toBeVisible();
}

export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to procurement", exact: true }),
  ).toBeVisible();
}

export function uniqueTitle(prefix: string): string {
  return `${prefix} · smoke ${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

export function registerRow(page: Page, title: string) {
  return page.getByRole("row").filter({ hasText: title });
}

// Open a saved requisition from the register by its unique title.
export async function openRequisition(
  page: Page,
  title: string,
): Promise<void> {
  const row = registerRow(page, title);
  await expect(row).toBeVisible();
  await row.getByRole("button").first().click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
}
