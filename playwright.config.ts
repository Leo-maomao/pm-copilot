import { defineConfig, devices } from '@playwright/test';

const port = process.env.PM_COPILOT_E2E_PORT ?? '57392';
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  // The suite writes to one local requirement library and browser session store.
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL,
    browserName: 'chromium',
    channel: 'chrome',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop-chrome',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'node tests/e2e/start-server.mjs',
    url: baseURL,
    reuseExistingServer: false,
  },
});
