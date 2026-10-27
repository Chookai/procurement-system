// Creates a uniquely named synthetic fixture through the real browser/API.
const { chromium } = require(process.argv[2] || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({
    viewport: { width: 1520, height: 1080 },
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const title = "PO revisions · browser " + Date.now();
  async function login(user) {
    await page.getByLabel("Username", { exact: true }).fill(user);
    await page.getByLabel("Password", { exact: true }).fill("harbor-demo");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page
      .getByRole("heading", { name: "Purchase requisitions", exact: true })
      .waitFor();
  }
  async function logout() {
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page
      .getByRole("heading", { name: "Sign in to procurement", exact: true })
      .waitFor();
  }
  async function choose() {
    await page.getByRole("button").filter({ hasText: title }).click();
  }
  async function button(name) {
    await page.getByRole("button", { name, exact: true }).click();
  }
  async function proposal(reason) {
    const bar = page.getByRole("region", {name: "Next procurement action", exact: true});
    assert.equal(await bar.getByRole("button", {name: "Revise PO", exact: true}).count(), 1);
    assert.ok((await bar.boundingBox()).y < 650);
    await button("Revise PO");
    await page.getByLabel("Quantity", { exact: true }).fill("12");
    await page
      .getByLabel("Proposed unit price (MYR)", { exact: true })
      .fill("220.00");
    await page
      .getByLabel("Confirmed supplier", { exact: true })
      .fill("Replacement Marine Supply");
    await page.getByLabel("Reason for change", { exact: true }).fill(reason);
    await button("Submit PO proposal");
    await page
      .getByText("PO proposal submitted to Ben", { exact: true })
      .waitFor();
  }
  try {
    await page.goto("http://127.0.0.1:5175/?theme=dark");
    await login("aina");
    await button("Create PR");
    const fields = {
      Title: title,
      "Required date": "2026-12-01",
      Vessel: "MV Harbor One",
      Location: "Port Klang",
      "Business purpose": "Replace worn pump seals",
      Description: "Pump seals",
      Quantity: "10",
      "Unit estimate (MYR)": "200.00",
    };
    for (const [name, value] of Object.entries(fields))
      await page.getByLabel(name, { exact: true }).fill(value);
    await button("Save draft");
    await page.getByRole("heading", { name: title, exact: true }).waitFor();
    await button("Submit for approval");
    await page.getByText("Submitted to Ben", { exact: true }).waitFor();
    await logout();
    await login("ben");
    await choose();
    await button("Approve PR");
    await page.getByText("PR approved", { exact: true }).waitFor();
    await logout();
    await login("chloe");
    await choose();
    await button("Prepare PO");
    await page
      .getByLabel("Confirmed supplier", { exact: true })
      .fill("Original Marine Supply");
    await page
      .getByLabel("Final unit price, line 1 (MYR)", { exact: true })
      .fill("190.00");
    await button("Issue PO");
    await page
      .getByRole("region", { name: "Issued purchase order", exact: true })
      .waitFor();
    await proposal("Extra upgraded seals required");
    let current = page.getByRole("region", {
      name: "Issued purchase order",
      exact: true,
    });
    assert.match(await current.innerText(), /1,900/);
    assert.equal(
      await page
        .getByRole("button", { name: "Issue approved PO terms", exact: true })
        .count(),
      0,
    );
    await logout();
    await login("ben");
    await choose();
    await page
      .getByLabel("Return reason", { exact: true })
      .fill("Explain the extra quantity");
    await button("Return PO proposal");
    await page.getByText("PO proposal returned", { exact: true }).waitFor();
    await logout();
    await login("chloe");
    await choose();
    await proposal("Confirmed two extra seals with maintenance");
    await logout();
    await login("ben");
    await choose();
    await button("Review PO proposal");
    await button("Approve PO terms");
    await page
      .getByText("PO terms approved; awaiting Chloe’s issuance", {
        exact: true,
      })
      .waitFor();
    assert.match(await current.innerText(), /1,900/);
    await logout();
    await login("chloe");
    await choose();
    await button("Review and issue approved terms");
    await button("Issue approved PO terms");
    await page.getByText("Approved PO terms issued", { exact: true }).waitFor();
    assert.match(await current.innerText(), /revision 2/i);
    assert.match(await current.innerText(), /2,640/);
    await page.reload();
    await choose();
    assert.match(await current.innerText(), /2,640/);
    const history = page.getByRole("region", {
      name: "PO revisions and reapproval",
      exact: true,
    });
    await history
      .locator("summary")
      .filter({ hasText: "revision 1 · MYR 1900.00" })
      .click();
    assert.match(await history.innerText(), /Original Marine Supply/);
    await page.screenshot({
      path: "mockups/application-po-revisions-dark.png",
      fullPage: true,
    });
    await button("Light theme");
    await page.screenshot({
      path: "mockups/application-po-revisions-light.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: "mockups/application-po-revisions-mobile.png",
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    const report = {
      status: "passed",
      title,
      checks: [
        "create and approve PR",
        "issue original MYR 1900 PO",
        "propose quantity and price increase",
        "current snapshot unchanged while pending and approved",
        "return reason and replacement proposal",
        "Ben approves exact proposal",
        "Chloe issues revision 2 MYR 2640",
        "reload persists",
        "original revision expandable",
        "light/dark",
        "390px no overflow",
      ],
      page_errors: errors,
    };
    fs.writeFileSync(
      "runtime-results/po-revisions-browser.json",
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
