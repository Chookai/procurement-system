// Creates one canonical synthetic procurement journey; leaves invoice review evidence.
const { chromium } = require(process.argv[2] || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const context = await browser.newContext({
      baseURL: "http://127.0.0.1:5175",
      viewport: { width: 1520, height: 1080 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let csrf;
    async function login(username) {
      const response = await context.request.post("/api/v1/auth/login", {
        data: { username, password: "harbor-demo" },
      });
      assert.equal(response.status(), 200);
      csrf = (await response.json()).csrf_token;
    }
    async function command(path, data) {
      const response = await context.request.post("/api/v1" + path, {
        data,
        headers: {
          "X-CSRF-Token": csrf,
          "Idempotency-Key": crypto.randomUUID(),
        },
      });
      assert.ok(response.ok(), await response.text());
      return response.json();
    }
    async function button(name) {
      await page.getByRole("button", { name, exact: true }).click();
    }
    const title = "Invoice review · " + Date.now();
    await login("aina");
    let record = await command("/requisitions", {
      title,
      kind: "goods",
      purpose: "Canonical ten ordered six accepted four outstanding journey",
      vessel: "MV Harbor One",
      location: "Port Klang",
      required_date: "2026-12-01",
      items: [{ description: "Pump seal", quantity: "10", unit_price: "200" }],
    });
    const path = "/requisitions/" + record.id;
    record = await command(path + "/submit", {
      expected_version: record.version,
    });
    await login("ben");
    record = await command(path + "/approve", {
      expected_version: record.version,
    });
    await login("chloe");
    record = await command(path + "/purchase-order", {
      expected_version: record.version,
      supplier: "Canonical Marine Supply",
      unit_prices: ["200"],
      delivery_terms: "Deliver ten seals",
    });
    await login("dinesh");
    record = await command(path + "/receipts", {
      expected_version: record.version,
      po_revision: 1,
      received_on: "2026-10-26",
      reference: "DN-INVOICE-DEMO",
      notes: "Six seals accepted; four pending delivery",
      lines: [{ line_index: 0, accepted: "6" }],
    });
    await login("eva");
    await page.goto("/?theme=dark");
    await page.getByRole("button").filter({ hasText: title }).click();
    const suffix = Date.now();
    async function capture(number, quantity, withEvidence = false) {
      await button("Capture supplier invoice");
      await page
        .getByLabel("Supplier invoice number", { exact: true })
        .fill(number);
      await page.getByLabel("Invoice date", { exact: true }).fill("2026-10-26");
      await page
        .getByLabel("Invoice evidence reference", { exact: true })
        .fill(number + ".pdf");
      await page
        .getByLabel("Invoice quantity, line 1", { exact: true })
        .fill(quantity);
      if (withEvidence) await page.getByRole("checkbox").check();
      await button("Capture invoice");
      await page
        .getByText("Supplier invoice captured", { exact: true })
        .waitFor();
    }
    async function review(number, outcome, reason) {
      await button("Review invoice " + number);
      await page
        .getByLabel("Review outcome", { exact: true })
        .selectOption(outcome);
      await page.getByLabel("Review reason", { exact: true }).fill(reason);
      await button("Record invoice outcome");
      await page
        .getByText("Invoice review outcome recorded", { exact: true })
        .waitFor();
    }
    const first = "SUP-A-" + suffix,
      second = "SUP-B-" + suffix,
      third = "SUP-C-" + suffix;
    await capture(first, "6", true);
    await review(
      first,
      "reviewed",
      "Checked six accepted seals against supplier invoice and receipt. No payment action.",
    );
    let saved = await (await context.request.get("/api/v1" + path)).json();
    assert.equal(saved.invoices[0].total, "1200.00");
    assert.equal(saved.invoices[0].status, "reviewed");
    assert.equal(saved.fulfilment.lines[0].outstanding, "4.00");
    assert.equal(saved.invoices[0].receipt_evidence.length, 1);
    await capture(second, "2");
    await review(
      second,
      "needs_clarification",
      "Quantity overlaps accepted evidence; request supplier clarification",
    );
    await capture(third, "1");
    await review(third, "rejected", "Duplicate claim for the same delivery");
    await page.reload();
    await page.getByRole("button").filter({ hasText: title }).click();
    await page
      .getByLabel("Filter by invoice review", { exact: true })
      .selectOption("needs_clarification");
    const row = page.getByRole("row").filter({ hasText: title });
    await row.waitFor();
    assert.match(await row.innerText(), /Eva · Review invoice/);
    assert.match(await row.innerText(), /Partially received/);
    const panel = page.getByRole("region", {
      name: "Supplier invoices",
      exact: true,
    });
    assert.match(await panel.innerText(), /Invoice reviewed/);
    assert.match(await panel.innerText(), /Invoice needs clarification/);
    assert.match(await panel.innerText(), /Invoice rejected/);
    await button("Review invoice " + second);
    assert.match(
      await panel.innerText(),
      /combined non-rejected invoices exceed accepted quantity/,
    );
    await page.screenshot({
      path: "mockups/invoices-dark.png",
      fullPage: true,
    });
    await button("Light theme");
    await page.screenshot({
      path: "mockups/invoices-light.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: "mockups/invoices-mobile.png",
      fullPage: true,
    });
    // Duplicate supplier invoice numbers are rejected, and the form remains editable.
    await button("Capture supplier invoice");
    await page
      .getByLabel("Supplier invoice number", { exact: true })
      .fill(first);
    await page.getByLabel("Invoice date", { exact: true }).fill("2026-10-26");
    await page
      .getByLabel("Invoice evidence reference", { exact: true })
      .fill("duplicate.pdf");
    await page
      .getByLabel("Invoice quantity, line 1", { exact: true })
      .fill("1");
    await button("Capture invoice");
    await page
      .getByRole("alert")
      .filter({ hasText: "already captured" })
      .waitFor();
    await button("Cancel");
    saved = await (await context.request.get("/api/v1" + path)).json();
    assert.equal(saved.invoices.length, 3);
    assert.equal(saved.fulfilment.lines[0].outstanding, "4.00");
    assert.deepEqual(errors, []);
    fs.writeFileSync(
      "runtime-results/invoices-browser.json",
      JSON.stringify(
        {
          status: "passed",
          title,
          record_id: record.id,
          checks: [
            "Eva captures invoice before full receipt",
            "links receipt evidence",
            "MYR 1200 review leaves four units outstanding",
            "multiple supplier invoices and all review outcomes",
            "advisory aggregate quantity warning",
            "visible invoice actions and filter",
            "history survives reload",
            "duplicate invoice rejected without write",
            "light/dark and 390px no overflow",
          ],
          page_errors: errors,
        },
        null,
        2,
      ) + "\n",
    );
    console.log("Invoice browser flow passed: " + title);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
