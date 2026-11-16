import { defineConfig, devices } from "@playwright/test";

// This repo contains only the Playwright automation - the Pixi.js
// application lives in testomut/pixijs-e2e-testing-demo. There is no
// webServer auto-start here because there is no app source to start; the
// target instance must already be running at APP_BASE_URL before tests
// run (see README "Running locally" / CI for how each case starts it).
const APP_BASE_URL = process.env.APP_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Each spin renders a real WebGL scene; several headless GPU contexts
  // competing for the same software renderer under CI/sandbox constraints
  // causes GPU-stall timeouts unrelated to test correctness (see README
  // limitations).
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: APP_BASE_URL,
    headless: true,
    screenshot: "only-on-failure",
    // "retain-on-failure" (rather than "on-first-retry") also captures a
    // trace on a first-attempt failure locally, where retries are 0.
    trace: "retain-on-failure",
    // Diagnostic default: only failed tests keep a video. RECORD_VIDEO=true
    // (see the test:video script) switches to recording every run, for
    // curating the portfolio demo clip - CI never sets this, so normal
    // successful runs never retain video there.
    video: process.env.RECORD_VIDEO === "true" ? "on" : "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
