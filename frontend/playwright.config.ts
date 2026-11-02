import { defineConfig, devices } from "@playwright/test";

const projectDir = import.meta.dirname;

// Port for the disposable browser-smoke stack. Distinct from the app's local
// development ports (5175 frontend / 8001 backend) so the suite never attaches
// to a running workspace instance or the user's procurement database.
const FRONTEND_PORT = Number(process.env.SMOKE_FRONTEND_PORT ?? 5275);
const BACKEND_PORT = Number(process.env.SMOKE_BACKEND_PORT ?? 8101);

const BASE_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const API_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// The database URL must point at a disposable test database. It is required so
// the suite can never silently fall back to the developer's procurement data.
const DATABASE_URL =
  process.env.SMOKE_DATABASE_URL ??
  "postgresql://procurement:procurement-local-only@127.0.0.1:15433/smoke_procurement";

export default defineConfig({
  testDir: "./e2e",
  // Browser journeys share one disposable backend/database, so run serially.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  outputDir: "test-results",
  use: {
    baseURL: BASE_URL,
    // Use Playwright's own bundled Chromium; never a channel of locally
    // installed Chrome and no machine-specific executable path.
    ...devices["Desktop Chrome"],
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `uv run --project ../backend --locked python -m uvicorn procurement.app:create_app --factory --host 127.0.0.1 --port ${BACKEND_PORT} --app-dir ../backend`,
      url: `${API_URL}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: projectDir,
      env: {
        DATABASE_URL,
        SESSION_SIGNING_KEY: "browser-smoke-disposable-signing-key-000000",
        // No OpenRouter/Azure credentials are provided or required.
      },
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: projectDir,
      env: {
        SMOKE_API_PROXY: API_URL,
        SMOKE_ORIGIN: "http://127.0.0.1:5175",
      },
    },
  ],
});
