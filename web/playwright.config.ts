import { defineConfig, devices } from '@playwright/test'

// A porta padrão evita a 8000 do `docker compose up`: reaproveitá-la faria o roteiro rodar no banco persistente.
const porta = process.env.E2E_PORT ?? '8765'
const baseURL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${porta}`

// Os roteiros rodam contra a API real servindo web/dist (rode `npm run build` antes).
// Sem E2E_BASE_URL, e2e/servidor.mjs sobe a API com um SQLite novo a cada execução.
// Para testar uma API já em pé, informe E2E_BASE_URL (os cadastros ficam nesse banco).
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0, // uma nova tentativa reaproveitaria o banco da anterior e esconderia instabilidade
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL,
    locale: 'pt-BR',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'e2e', testIgnore: /a11y\.spec\.ts/, use: { ...devices['Desktop Chrome'] } },
    { name: 'a11y', testMatch: /a11y\.spec\.ts/, use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'node e2e/servidor.mjs',
    url: `${baseURL}/health/ready`,
    reuseExistingServer: false,
    timeout: 60_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
