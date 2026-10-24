import { defineConfig } from '@playwright/test';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectDirectory = path.resolve(frontendDirectory, '..');
const testDataDirectory = mkdtempSync(path.join(tmpdir(), 'academic-reservations-e2e-'));
const databasePath = path.join(testDataDirectory, 'reservations.sqlite3');
const localPython = process.platform === 'win32'
  ? path.join(projectDirectory, '.venv', 'Scripts', 'python.exe')
  : path.join(projectDirectory, '.venv', 'bin', 'python');
const pythonExecutable = process.env.PYTHON_EXECUTABLE
  || (existsSync(localPython) ? localPython : process.platform === 'win32' ? 'py' : 'python3');
const pythonPrefix = pythonExecutable === 'py' ? '-3 ' : '';
const quote = (value) => `"${value.replaceAll('"', '\\"')}"`;

process.env.E2E_DATABASE_PATH = databasePath;
process.env.E2E_DATA_DIRECTORY = testDataDirectory;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  globalSetup: './tests/e2e/global-setup.js',
  globalTeardown: './tests/e2e/global-teardown.js',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `${quote(pythonExecutable)} ${pythonPrefix}-m uvicorn backend.main:app --host 127.0.0.1 --port 8000`,
      cwd: projectDirectory,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
      timeout: 30_000,
      env: { ACADEMIC_RESERVATIONS_DB_PATH: databasePath },
    },
    {
      command: `${quote(process.execPath)} ${quote(path.join(frontendDirectory, 'node_modules/vite/bin/vite.js'))} --host 127.0.0.1 --port 5173`,
      cwd: frontendDirectory,
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: '/api' },
    },
  ],
});
