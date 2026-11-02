/**
 * Open the shared Asrax Web OAuth client and add Email Extractor redirect URIs if missing.
 * Headed Chrome — complete Google login as admin@asrax.in if prompted, then SAVE.
 *
 * Credentials: ~/.asrax/secrets/n8n-google-oauth-web.json (same Web client as Keycloak / n8n).
 */
import { chromium } from "playwright";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const secretsPath = join(homedir(), ".asrax", "secrets", "n8n-google-oauth-web.json");
if (!existsSync(secretsPath)) {
  console.error("Missing", secretsPath);
  process.exit(1);
}

const doc = JSON.parse(readFileSync(secretsPath, "utf8"));
const web = doc.web || doc;
const clientId = web.client_id;
if (!clientId) {
  console.error("No client_id in", secretsPath);
  process.exit(1);
}

const emailRedirects = [
  "https://am-dev.asrax.in/email/api/v1/gmail/callback",
  "https://am-preprod.asrax.in/email/api/v1/gmail/callback",
  "https://am.asrax.in/email/api/v1/gmail/callback",
];

const existing = Array.isArray(web.redirect_uris) ? web.redirect_uris : [];
const merged = [...existing];
for (const u of emailRedirects) {
  if (!merged.includes(u)) merged.push(u);
}
web.redirect_uris = merged;
if (doc.web) doc.web = web;
else Object.assign(doc, web);
writeFileSync(secretsPath, JSON.stringify(doc, null, 2) + "\n", "utf8");
console.log("Updated local secrets redirect_uris (", merged.length, "total)");

const editUrl =
  "https://accounts.google.com/AccountChooser?Email=admin%40asrax.in&continue=" +
  encodeURIComponent(
    `https://console.cloud.google.com/auth/clients/edit/${encodeURIComponent(clientId)}?project=am-asrax`,
  );

console.log("Client:", clientId);
console.log("Ensure these Authorized redirect URIs exist, then click SAVE:");
for (const u of emailRedirects) console.log(" -", u);

const browser = await chromium.launch({ headless: false, channel: "chrome" }).catch(() =>
  chromium.launch({ headless: false }),
);
const page = await (await browser.newContext()).newPage();
await page.goto(editUrl, { waitUntil: "domcontentloaded", timeout: 180000 });

console.log("Waiting for Cloud Console client editor…");
try {
  await page.waitForURL(/console\.cloud\.google\.com/, { timeout: 180000 });
} catch {
  console.log("Still on login — complete sign-in in the Chrome window.");
}

const deadline = Date.now() + 9 * 60 * 1000;
let attempted = false;

while (Date.now() < deadline) {
  const url = page.url();
  if (!url.includes("console.cloud.google.com")) {
    await page.waitForTimeout(2000);
    continue;
  }

  if (!attempted) {
    attempted = true;
    console.log("Console open — attempting to add redirect URIs…");
    try {
      for (const uri of emailRedirects) {
        const already = await page.getByText(uri, { exact: false }).count();
        if (already > 0) {
          console.log("Already present:", uri);
          continue;
        }
        const addButtons = page.getByRole("button", { name: /add uri/i });
        const n = await addButtons.count();
        if (n > 0) {
          await addButtons.last().click();
          await page.waitForTimeout(500);
        }
        const boxes = page.locator('input[type="text"], input[type="url"], input:not([type])');
        const count = await boxes.count();
        for (let i = count - 1; i >= 0; i--) {
          const box = boxes.nth(i);
          const val = await box.inputValue().catch(() => "");
          const visible = await box.isVisible().catch(() => false);
          if (!visible) continue;
          if (!val || val.startsWith("http")) {
            if (!val) {
              await box.fill(uri);
              console.log("Filled:", uri);
              break;
            }
          }
        }
      }
      const save = page.getByRole("button", { name: /save/i }).first();
      if (await save.isVisible().catch(() => false)) {
        await save.click();
        console.log("Clicked SAVE — confirm success toast in browser.");
      } else {
        console.log("Could not find SAVE — please save manually in the Chrome window.");
      }
    } catch (e) {
      console.log("Auto-fill limited:", String(e).slice(0, 200));
      console.log("Please add the URIs and SAVE manually.");
    }
  }

  if (page.isClosed()) break;
  await page.waitForTimeout(5000);
}

await browser.close().catch(() => {});
console.log("Browser closed.");
