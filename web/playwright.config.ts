import { defineConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const E2E_BACKEND_PORT = 8766;
const E2E_FRONTEND_PORT = 5174;
const E2E_WS_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), ".e2e-workflows");
fs.rmSync(E2E_WS_DIR, { recursive: true, force: true });
fs.mkdirSync(E2E_WS_DIR, { recursive: true });

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${E2E_FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `python -m uvicorn app.main:app --host 127.0.0.1 --port ${E2E_BACKEND_PORT}`,
      cwd: "..",
      url: `http://127.0.0.1:${E2E_BACKEND_PORT}/api/workflows`,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        FAKE_PROPOSER: "1",
        WS_DIR: E2E_WS_DIR,
      },
    },
    {
      command: `npm run dev -- --port ${E2E_FRONTEND_PORT} --host 127.0.0.1`,
      cwd: ".",
      url: `http://127.0.0.1:${E2E_FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        VITE_API_TARGET: `http://127.0.0.1:${E2E_BACKEND_PORT}`,
      },
    },
  ],
});