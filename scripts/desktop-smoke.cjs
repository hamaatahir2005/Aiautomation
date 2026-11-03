// Runs against the installed Windows executable and its real isolated CI user profile.
const { _electron } = require("playwright");
const path = require("node:path");
const fs = require("node:fs/promises");
(async () => {
  const executablePath = path.join(
    process.env.LOCALAPPDATA,
    "Programs",
    "AI Company OS",
    "AI Company OS.exe",
  );
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath, timeout: 120000 });
    const page = await desktop.firstWindow({ timeout: 120000 });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.stack || error.message));
    await page
      .getByLabel("Create an owner password (12+ characters)")
      .fill("windows-ci-owner-password");
    await page.getByRole("button", { name: "Create local workspace" }).click();
    await page.getByRole("button", { name: "Set up later" }).click();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await page.getByRole("heading", { name: "Company overview" }).waitFor();
    await page.locator("canvas").waitFor();
    await page.waitForTimeout(3000);
    await page.locator("canvas").hover();
    await page.mouse.wheel(0, 80);
    await fs.mkdir("release/evidence", { recursive: true });
    await page.screenshot({
      path: "release/evidence/windows-office.png",
      fullPage: true,
    });
    await page.getByRole("button", { name: "Customers", exact: true }).click();
    await page
      .getByLabel("Name", { exact: true })
      .fill("Windows acceptance customer");
    await page
      .getByLabel("Email", { exact: true })
      .fill("windows-acceptance@example.com");
    await page.getByRole("button", { name: "Save customer" }).click();
    await page
      .getByRole("cell", {
        name: "windows-acceptance@example.com",
        exact: true,
      })
      .waitFor();
    await desktop.close();
    desktop = await _electron.launch({ executablePath, timeout: 120000 });
    const restarted = await desktop.firstWindow({ timeout: 120000 });
    await restarted
      .getByLabel("Owner password")
      .fill("windows-ci-owner-password");
    await restarted.getByRole("button", { name: "Unlock workspace" }).click();
    await restarted
      .getByRole("button", { name: "Customers", exact: true })
      .click();
    await restarted
      .getByRole("cell", {
        name: "windows-acceptance@example.com",
        exact: true,
      })
      .waitFor();
    if (errors.length)
      throw Error("Desktop renderer errors: " + errors.join("; "));
    console.log(
      "Windows installed desktop acceptance passed: real preload, owner setup, WebGL office, native application restart and persisted customer.",
    );
  } finally {
    await desktop?.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
