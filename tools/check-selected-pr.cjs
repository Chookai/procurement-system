// Read-only regression for stale right-panel DOM caused by duplicate sibling keys.
const { chromium } = require(process.argv[2] || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const context = await browser.newContext({
      baseURL: "http://127.0.0.1:5175",
      viewport: { width: 1288, height: 884 },
    });
    async function login(username) {
      const response = await context.request.post("/api/v1/auth/login", {
        data: { username, password: "harbor-demo" },
      });
      assert.equal(response.status(), 200);
    }
    await login("eva");
    const records = (
      await (await context.request.get("/api/v1/requisitions")).json()
    ).items;
    let targets = [
      records.find((r) => r.number === "PR-0014"),
      records.find((r) => r.number === "PR-0013"),
    ].filter(Boolean);
    if (targets.length !== 2) {
      const first = records.find((r) => r.invoices.length > 0);
      targets = first
        ? [
            first,
            records.find(
              (r) =>
                r.id !== first.id &&
                r.purchase_order &&
                r.invoices.length !== first.invoices.length,
            ),
          ].filter(Boolean)
        : [];
    }
    assert.equal(
      targets.length,
      2,
      "Need two issued PRs with distinct invoice histories",
    );
    const page = await context.newPage();
    const errors = [];
    const duplicateKeys = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (message) => {
      if (
        message.type() === "error" &&
        /same key|unique.*key/.test(message.text())
      )
        duplicateKeys.push("Duplicate React key warning");
    });
    for (const role of ["eva", "ben", "chloe", "dinesh"]) {
      await login(role);
      await page.goto("/?theme=dark");
      for (let cycle = 0; cycle < 3; cycle++)
        for (const record of targets) {
          await page
            .getByRole("button")
            .filter({ hasText: record.title })
            .click();
          const detail = page.getByRole("region", {
            name: "Request detail",
            exact: true,
          });
          await detail
            .getByRole("heading", { name: record.title, exact: true })
            .waitFor();
          assert.match(
            await detail.locator(".detail-heading").innerText(),
            new RegExp(record.number),
          );
          const panel = detail.getByRole("region", {
            name: "Supplier invoices",
            exact: true,
          });
          assert.equal(await panel.count(), 1, "Exactly one invoice panel");
          assert.equal(
            await panel
              .getByRole("heading", {
                name: "Supplier invoices · " + record.invoices.length,
                exact: true,
              })
              .count(),
            1,
            record.number + " invoice count must match selected record",
          );
          const summaries = await panel
            .locator("details > summary")
            .allTextContents();
          assert.equal(
            summaries.length,
            record.invoices.length,
            record.number + " has stale invoice DOM nodes",
          );
          for (const invoice of record.invoices)
            assert.ok(
              summaries.some((text) =>
                text.startsWith(invoice.invoice_number + " ·"),
              ),
              record.number + " missing its invoice " + invoice.invoice_number,
            );
          for (const other of targets.filter((r) => r.id !== record.id))
            for (const invoice of other.invoices)
              assert.ok(
                !summaries.some((text) =>
                  text.startsWith(invoice.invoice_number + " ·"),
                ),
                record.number +
                  " shows another PR invoice " +
                  invoice.invoice_number,
              );
          const issued = detail.getByRole("region", {
            name: "Issued purchase order",
            exact: true,
          });
          assert.equal(
            await issued
              .getByRole("heading", {
                name: record.purchase_order.number,
                exact: true,
              })
              .count(),
            1,
          );
          const revisions = detail.getByRole("region", {
            name: "PO revisions and reapproval",
            exact: true,
          });
          assert.equal(
            await revisions.locator("details").count(),
            record.po_history.length + record.po_proposals.length,
          );
          const receiptHistory = detail.getByRole("region", {
            name: "Receipt and acceptance history",
            exact: true,
          });
          assert.equal(
            await receiptHistory.locator("details").count(),
            record.receipts.length,
          );
          assert.equal(
            await detail.locator(":scope > ol.activity > li").count(),
            record.events.length,
            "Activity must belong to selected PR",
          );
          assert.equal(
            await detail.locator(".invoice-review-form").count(),
            0,
            "Unsaved invoice review must reset when changing PRs",
          );
          if (role === "eva") {
            const open = record.invoices.find((invoice) =>
              ["awaiting_review", "needs_clarification"].includes(
                invoice.status,
              ),
            );
            if (open) {
              await panel
                .getByRole("button", {
                  name: "Review invoice " + open.invoice_number,
                  exact: true,
                })
                .click();
              await page
                .getByLabel("Review reason", { exact: true })
                .fill("Unsaved regression check; do not submit");
            }
          }
        }
    }
    // Capture the screenshot PR after the final switch, without changing business records.
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "mockups/selected-pr-dark.png",
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Light theme", exact: true })
      .click();
    await page.screenshot({
      path: "mockups/selected-pr-light.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    assert.deepEqual(errors, []);
    assert.deepEqual(duplicateKeys, []);
    const report = {
      status: "passed",
      records: targets.map((record) => ({
        number: record.number,
        invoices: record.invoices.length,
      })),
      roles: ["eva", "ben", "chloe", "dinesh"],
      checks: [
        "Repeated switching retains only selected PR invoices",
        "PO revisions and receipt history match selected PR",
        "Main activity count matches selected PR",
        "Unsaved review state resets between PRs",
        "No duplicate React key warnings",
        "Light/dark and 390px layout",
      ],
      page_errors: errors,
    };
    fs.writeFileSync(
      "runtime-results/selected-pr-browser.json",
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
