// Browser smoke test for the deployed (or local) DClaw Flow app — loads the key
// pages and asserts they render. See e2e/README.md for setup.
//
//   node e2e/smoke.mjs [BASE_URL]   (default: https://dclaw-flow.vercel.app)
//
// Exits non-zero if any check fails.
import { chromium } from "playwright";

const APP = process.argv[2] || "https://dclaw-flow.vercel.app";
let failures = 0;
const check = (name, ok) => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}`);
  if (!ok) failures++;
};

const browser = await chromium.launch();
const page = await (
  await browser.newContext({ viewport: { width: 1280, height: 850 } })
).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));

try {
  // Auth: every route is gated, so sign up first (unique email per run).
  await page.goto(`${APP}/signup`, { waitUntil: "networkidle", timeout: 60000 });
  const email = `smoke+${Date.now()}@example.com`;
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', "smoketest123");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/workflows$/, { timeout: 35000 }).catch(() => {});
  check("signup → authenticated app", /\/workflows/.test(page.url()));

  // Home + copilot widget
  await page.goto(APP, { waitUntil: "networkidle", timeout: 60000 });
  check("home renders (nav)", (await page.locator("text=DClaw Flow").count()) > 0);
  await page.locator('button[aria-label="Open Flow Copilot"]').click();
  await page.waitForTimeout(800);
  check("copilot widget opens", (await page.locator("text=Flow Copilot").count()) > 0);

  // Workflows list + editor canvas
  await page.goto(`${APP}/workflows`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  check("workflows list renders", (await page.textContent("body")).includes("New Workflow"));
  const card = page.locator('a[href^="/workflows/"]:not([href$="/new"])').first();
  if (await card.count()) {
    await card.click();
    await page.waitForSelector(".react-flow", { timeout: 35000 }).catch(() => {});
    check("editor canvas renders", (await page.locator(".react-flow").count()) > 0);
    check("canvas has nodes", (await page.locator(".react-flow__node").count()) > 0);
  } else {
    check("a workflow card exists to open", false);
  }

  // New-workflow page: starter template gallery
  await page.goto(`${APP}/workflows/new`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2000);
  check(
    "template gallery renders",
    (await page.textContent("body")).includes("Start from a template"),
  );
  const tplCard = page.locator('button:has-text("nodes")').first();
  if (await tplCard.count()) {
    await tplCard.click();
    await page.waitForURL(/\/workflows\/[0-9a-f-]{36}$/, { timeout: 35000 }).catch(() => {});
    check("template instantiates into editor", /\/workflows\/[0-9a-f-]{36}$/.test(page.url()));
  } else {
    check("a template card exists", false);
  }

  // Executions
  await page.goto(`${APP}/executions`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2000);
  check("executions page renders", (await page.textContent("body")).includes("Execution History"));

  check("no page errors", errors.length === 0);
  if (errors.length) console.log("  errors:", errors.slice(0, 5));
} finally {
  await browser.close();
}

console.log(failures ? `\n${failures} check(s) failed` : "\nAll smoke checks passed");
process.exit(failures ? 1 : 0);
