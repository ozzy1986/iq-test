import { defineConfig, devices } from '@playwright/test'

// Тесты сами поднимают API (на временной SQLite-базе) и dev-сервер фронтенда.
const python = process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'

export default defineConfig({
  testDir: 'e2e',
  timeout: 120_000,
  workers: 1,
  reporter: 'list',
  use: { baseURL: 'http://localhost:5173', trace: 'retain-on-failure' },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8130`,
      cwd: '..',
      url: 'http://127.0.0.1:8130/api/health',
      env: { DATABASE_URL: 'sqlite+aiosqlite:///./e2e.db' },
      reuseExistingServer: false,
    },
    { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: false },
  ],
})
