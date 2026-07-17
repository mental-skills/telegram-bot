import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  workers: 1,
  use: {
    baseURL: process.env.LIVE_BASE_URL ?? "http://127.0.0.1:8080",
    channel: process.platform === "win32" ? "chrome" : undefined,
    viewport: { width: 390, height: 844 },
    trace: "retain-on-failure"
  }
});
