// Read-only browser regression using a privately preserved real package.
// Run after `npm run build` and `npm run preview -- --port 4175`.
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
import fs from "node:fs/promises";
import path from "node:path";
const root = path.resolve("../../..");
const out = path.join(root, ".runtime/workbench-visual");
const data = JSON.parse(
  await fs.readFile(path.join(out, "recorded-reads.json"), "utf8"),
);
const browser = await chromium.launch({ headless: true });
const audit = [];
for (const width of [1440, 1280, 768, 390]) {
  const context = await browser.newContext({
    viewport: { width, height: 1000 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const errors = [],
    requests = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => requests.push(r.url()));
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    if (req.method() !== "GET")
      throw new Error("Visual QA cannot mutate records");
    const url = new URL(req.url());
    let value;
    if (url.pathname.endsWith("/health"))
      value = {
        status: "ok",
        mode: "live",
        model: "swiss-ai/Apertus-v1.5-8B",
        model_configured: true,
        workflow: "temporal",
        database: "postgresql",
      };
    else if (url.pathname.endsWith("/default")) value = data.project;
    else value = data[url.pathname.split("/").at(-1)];
    if (value === undefined)
      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "This read is outside the recorded visual QA package.",
        }),
      });
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  });
  await page.goto("http://127.0.0.1:4175");
  await page.getByText("Resolve review blockers").waitFor();
  async function record(name) {
    const metrics = await page.evaluate(() => {
      const elements = [...document.querySelectorAll("body *")].filter(
        (el) =>
          el.getBoundingClientRect().width > 0 &&
          el.getBoundingClientRect().height > 0 &&
          getComputedStyle(el).visibility !== "hidden",
      );
      const text = elements.filter((el) =>
        [...el.childNodes].some(
          (n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim(),
        ),
      );
      return {
        viewport: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        minFont: Math.min(
          ...text.map((el) => parseFloat(getComputedStyle(el).fontSize)),
        ),
        smallText: text
          .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 13)
          .map((el) => ({
            text: el.textContent.slice(0, 60),
            font: getComputedStyle(el).fontSize,
          })),
        outside: elements
          .filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
          .slice(0, 30)
          .map((el) => ({
            tag: el.tagName,
            class: el.className,
            right: el.getBoundingClientRect().right,
            width: el.getBoundingClientRect().width,
          })),
        statusHeight: document
          .querySelector(".release-status")
          ?.getBoundingClientRect().height,
      };
    });
    await page.screenshot({
      path: path.join(out, `${width}-${name}.png`),
      fullPage: true,
      animations: "disabled",
    });
    audit.push({
      width,
      name,
      ...metrics,
      errors: [...errors],
      externalRequests: requests.filter(
        (url) => !url.startsWith("http://127.0.0.1:4175"),
      ),
    });
  }
  await record("overview");
  await page.getByRole("button", { name: /^Review issues/ }).click();
  await record("issues");
  await page.getByRole("button", { name: "Close review issues" }).click();
  await page.getByRole("button", { name: /^Evidence(?: 02)?$/ }).click();
  await page.getByLabel("Search source text").fill("37105.50");
  await page
    .getByRole("button", { name: "Search sources", exact: true })
    .click();
  await page.getByRole("region", { name: "Source search results" }).waitFor();
  await record("evidence");
  await page
    .getByRole("button", { name: /View lineage for/ })
    .first()
    .click();
  await record("lineage");
  await page
    .getByRole("button", { name: /Inspect passage on page/ })
    .first()
    .click();
  await record("source");
  await page.getByRole("button", { name: "Close source inspector" }).click();
  for (const [name, nav] of [
    ["requirements", /^Requirements(?: |$)/],
    ["offers", /^Supplier comparison/],
    ["release", /^Acceptance & release/],
    ["history", /^Change history/],
  ]) {
    await page.getByRole("button", { name: nav }).click();
    if (name === "history") {
      await page.getByRole("button", { name: "Compare snapshots" }).click();
      await page.getByRole("region", { name: "Snapshot changes" }).waitFor();
    }
    await record(name);
  }
  await context.close();
}
await browser.close();
await fs.writeFile(
  path.join(out, "responsive-audit.json"),
  JSON.stringify(audit, null, 2),
);
console.log(
  JSON.stringify(
    {
      views: audit.length,
      overflow: audit.filter((a) => a.scrollWidth > a.width),
      smallText: audit.filter((a) => a.smallText.length),
      errors: audit.filter((a) => a.errors.length),
      externalRequests: audit.filter((a) => a.externalRequests.length),
    },
    null,
    2,
  ),
);
