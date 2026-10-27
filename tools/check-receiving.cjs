// Synthetic, uniquely named records through real HTTP and browser commands.
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
      const r = await context.request.post("/api/v1/auth/login", {
        data: { username, password: "harbor-demo" },
      });
      assert.equal(r.status(), 200);
      csrf = (await r.json()).csrf_token;
    }
    async function command(path, data) {
      const r = await context.request.post("/api/v1" + path, {
        data,
        headers: {
          "X-CSRF-Token": csrf,
          "Idempotency-Key": crypto.randomUUID(),
        },
      });
      assert.ok(r.ok(), await r.text());
      return r.json();
    }
    async function button(name) {
      await page.getByRole("button", { name, exact: true }).click();
    }
    async function open(record) {
      await page.goto("/?theme=dark");
      await page.getByRole("button").filter({ hasText: record.title }).click();
    }
    async function details(record) {
      const response = await context.request.get(
        "/api/v1/requisitions/" + record.id,
      );
      assert.ok(response.ok());
      return response.json();
    }
    async function seed(kind, quantity) {
      const title = `Receiving ${kind} · ${Date.now()}`;
      const data = {
        title,
        kind,
        purpose: "Confirm accepted delivery with evidence",
        vessel: "MV Harbor One",
        location: "Port Klang",
        required_date: "2026-12-01",
        items: [
          {
            description:
              kind === "goods" ? "Pump seal" : "Inspection milestone",
            quantity,
            unit_price: "200",
          },
        ],
      };
      await login("aina");
      let r = await command("/requisitions", data);
      const path = "/requisitions/" + r.id;
      r = await command(path + "/submit", { expected_version: r.version });
      await login("ben");
      r = await command(path + "/approve", { expected_version: r.version });
      await login("chloe");
      r = await command(path + "/purchase-order", {
        expected_version: r.version,
        supplier: "Marine Supply",
        unit_prices: ["190"],
        delivery_terms: "",
      });
      return { record: r, data, path };
    }
    const goods = await seed("goods", "10");
    let record = await command(goods.path + "/po-proposals", {
      ...goods.data,
      expected_version: goods.record.version,
      supplier: "Marine Supply",
      items: [{ description: "Pump seal", quantity: "12", unit_price: "220" }],
      delivery_terms: "Priority delivery",
      reason: "Two extra seals required",
    });
    await login("dinesh");
    await open(record);
    const panel = page.getByRole("region", {
      name: "Issued PO fulfilment",
      exact: true,
    });
    assert.match(
      await panel.innerText(),
      /proposed quantities are not available/,
    );
    await button("Record goods receipt");
    await page
      .getByLabel("Delivery note reference", { exact: true })
      .fill("DN-BROWSER-001");
    await page.getByLabel("Accepted, line 1", { exact: true }).fill("6");
    await page.getByLabel("Damaged, line 1", { exact: true }).fill("2");
    await page.getByLabel("Rejected, line 1", { exact: true }).fill("1");
    await page
      .getByLabel("Inspection notes", { exact: true })
      .fill("Two damaged and one rejected seal; replacements needed");
    await button("Confirm goods receipt");
    await page
      .getByText("Receipt / acceptance recorded", { exact: true })
      .waitFor();
    record = await details(record);
    assert.equal(record.fulfilment.lines[0].outstanding, "4.00");
    assert.equal(record.receipts[0].po_revision, 1);
    const row = page.getByRole("row").filter({ hasText: record.title });
    assert.match(await row.innerText(), /Awaiting PO approval/);
    assert.match(await row.innerText(), /Partially received/);
    assert.match(await row.innerText(), /Dinesh/);
    await login("ben");
    record = await command(goods.path + "/po-proposals/approve", {
      expected_version: record.version,
      proposal_id: record.po_proposals[0].id,
    });
    await login("dinesh");
    await open(record);
    await button("Record goods receipt");
    await page
      .getByLabel("Delivery note reference", { exact: true })
      .fill("DN-OVER-LIMIT");
    await page.getByLabel("Accepted, line 1", { exact: true }).fill("4");
    await page.getByLabel("Damaged, line 1", { exact: true }).fill("1");
    await page
      .getByLabel("Inspection notes", { exact: true })
      .fill("Check combined quantity cap");
    await button("Confirm goods receipt");
    await page
      .getByRole("alert")
      .filter({ hasText: "exceed the outstanding" })
      .waitFor();
    assert.equal((await details(record)).receipts.length, 1);
    await button("Cancel");
    await login("chloe");
    record = await command(goods.path + "/po-proposals/issue", {
      expected_version: record.version,
      proposal_id: record.po_proposals[0].id,
    });
    assert.equal(record.fulfilment.lines[0].outstanding, "6.00");
    await login("dinesh");
    await open(record);
    await button("Record goods receipt");
    await page
      .getByLabel("Delivery note reference", { exact: true })
      .fill("DN-BROWSER-002");
    await page.getByLabel("Accepted, line 1", { exact: true }).fill("6");
    await button("Confirm goods receipt");
    await page
      .getByText("Receipt / acceptance recorded", { exact: true })
      .waitFor();
    await page.reload();
    await page.getByRole("button").filter({ hasText: record.title }).click();
    record = await details(record);
    assert.equal(record.fulfilment.status, "complete");
    assert.deepEqual(
      record.receipts.map((r) => r.po_revision),
      [1, 2],
    );
    assert.equal(
      await page
        .getByRole("button", { name: "Record goods receipt", exact: true })
        .count(),
      0,
    );
    await page
      .getByLabel("Filter by fulfilment", { exact: true })
      .selectOption("complete");
    await page.getByRole("row").filter({ hasText: record.title }).waitFor();
    await page.screenshot({
      path: "mockups/receiving-dark.png",
      fullPage: true,
    });
    await button("Light theme");
    await page.screenshot({
      path: "mockups/receiving-light.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: "mockups/receiving-mobile.png",
      fullPage: true,
    });
    const service = await seed("service", "3");
    await login("dinesh");
    await open(service.record);
    await button("Record service acceptance");
    await page
      .getByLabel("Work completion reference", { exact: true })
      .fill("WORK-001");
    await page.getByLabel("Accepted, line 1", { exact: true }).fill("1");
    assert.equal(
      await page.getByLabel("Damaged, line 1", { exact: true }).count(),
      0,
    );
    await button("Confirm service acceptance");
    await page
      .getByText("Receipt / acceptance recorded", { exact: true })
      .waitFor();
    const accepted = await details(service.record);
    assert.equal(accepted.fulfilment.lines[0].outstanding, "2.00");
    assert.match(accepted.receipts[0].number, /^SA-/);
    assert.deepEqual(errors, []);
    const report = {
      status: "passed",
      goods_title: record.title,
      goods_id: record.id,
      service_title: accepted.title,
      checks: [
        "Dinesh receives during pending revision",
        "accepted 6 damaged 2 rejected 1 leaves 4",
        "change approval and fulfilment visible separately",
        "combined quantity overflow rejected without write",
        "issued increase to 12 leaves 6",
        "second receipt linked to revision 2",
        "reload and history persist",
        "complete fulfilment filter",
        "no receive action on complete order",
        "service milestone acceptance leaves 2",
        "light/dark and mobile no overflow",
      ],
      page_errors: errors,
    };
    fs.writeFileSync(
      "runtime-results/receiving-browser.json",
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
