// Local browser check with its own Chromium process; no shared browser profile.
const { chromium } = require(process.argv[2] || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    baseURL: "http://127.0.0.1:5175",
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await page.goto("/?theme=dark");
    await page.getByLabel("Username", { exact: true }).fill("chloe");
    await page.getByLabel("Password", { exact: true }).fill("harbor-demo");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page
      .getByRole("link", { name: "Policy documents", exact: true })
      .click();
    const title = "Synthetic policy browser " + Date.now();
    await page.getByLabel("Document title", { exact: true }).fill(title);
    await page
      .getByLabel("Source file", { exact: true })
      .setInputFiles({
        name: "browser-policy.md",
        mimeType: "text/markdown",
        buffer: Buffer.from(
          "# Synthetic policy\nInvoice review does not authorize payment.\nFour seals remain outstanding after partial receipt.",
        ),
      });
    await page
      .getByRole("button", { name: "Upload document", exact: true })
      .click();
    const card = page
      .locator("article.document-card")
      .filter({ has: page.getByRole("heading", { name: title, exact: true }) });
    await card
      .getByText("Searchable", { exact: true })
      .waitFor({ timeout: 60000 });
    await page
      .getByLabel("Search policies", { exact: true })
      .fill("Does invoice review authorize payment?");
    await page
      .getByRole("button", { name: "Search evidence", exact: true })
      .click();
    await page
      .getByText("Invoice review does not authorize payment.", { exact: false })
      .first()
      .waitFor();
    assert.ok(
      await page.getByRole("link", { name: "Download cited source" }).count(),
    );
    await page.screenshot({
      path: "runtime-results/document-ingestion-dark.png",
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Light theme", exact: true })
      .click();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: "runtime-results/document-ingestion-mobile.png",
      fullPage: true,
    });
    await card
      .getByRole("button", { name: "Replace source", exact: true })
      .click();
    await page
      .getByLabel("Source file", { exact: true })
      .setInputFiles({
        name: "browser-policy-v2.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(
          "Replacement synthetic policy: invoice review is not payment. Accepted quantities still determine outstanding fulfilment.",
        ),
      });
    await page
      .getByRole("button", { name: "Upload replacement", exact: true })
      .click();
    await card
      .getByText("Search uses version 2.", { exact: true })
      .waitFor({ timeout: 60000 });
    await card
      .getByRole("button", { name: "Delete policy", exact: true })
      .click();
    await card
      .getByRole("button", { name: "Confirm deletion", exact: true })
      .click();
    await card.waitFor({ state: "detached" });
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page.getByLabel("Username", { exact: true }).fill("eva");
    await page.getByLabel("Password", { exact: true }).fill("harbor-demo");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page
      .getByRole("link", { name: "Policy documents", exact: true })
      .click();
    assert.equal(
      await page
        .getByRole("button", { name: "Upload document", exact: true })
        .count(),
      0,
    );
    assert.deepEqual(errors, []);
    const result = {
      status: "passed",
      scope:
        "Real local UI/Blob/worker/embeddings; synthetic browser fixture deleted",
      checks: [
        "buyer uploads",
        "worker publishes",
        "search citation",
        "source replacement",
        "delete",
        "reviewer read-only",
        "390px layout",
        "light/dark",
        "no page errors",
      ],
      page_errors: errors,
    };
    fs.writeFileSync(
      "runtime-results/document-ingestion-browser.json",
      JSON.stringify(result, null, 2) + "\n",
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
