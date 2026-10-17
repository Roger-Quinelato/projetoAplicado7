// Sobe a API para os roteiros E2E com um SQLite temporário novo, sem RabbitMQ e sem modo público.
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')

if (!existsSync(join(raiz, 'web', 'dist', 'index.html'))) {
  console.error('web/dist não existe: rode `npm run build` em web/ antes dos roteiros E2E.')
  process.exit(1)
}

// O Playwright encerra este processo à força no Windows; por isso as sobras de execuções anteriores são apagadas aqui.
for (const antiga of readdirSync(tmpdir()).filter(nome => nome.startsWith('archcorp-e2e-'))) {
  try { rmSync(join(tmpdir(), antiga), { recursive: true, force: true }) } catch { /* em uso por outra execução */ }
}
const pasta = mkdtempSync(join(tmpdir(), 'archcorp-e2e-'))
const banco = join(pasta, 'archcorp.db')
const limpar = () => rmSync(pasta, { recursive: true, force: true })

const python = process.env.E2E_PYTHON
  ?? [join(raiz, '.venv', 'Scripts', 'python.exe'), join(raiz, '.venv', 'bin', 'python')].find(existsSync)
  ?? 'python'

const env = {
  ...process.env,
  PYTHONPATH: join(raiz, 'src'),
  DATABASE_URL: `sqlite:///${banco.split('\\').join('/')}`,
  PUBLIC_DEMO: 'false',
}
delete env.RABBITMQ_URL
delete env.DEMO_ACCESS_TOKEN

const api = spawn(python, ['-m', 'uvicorn', 'archcorp.main:app', '--host', '127.0.0.1', '--port', process.env.E2E_PORT ?? '8765'], {
  cwd: raiz, env, stdio: 'inherit',
})
for (const sinal of ['SIGINT', 'SIGTERM']) process.on(sinal, () => api.kill())
api.on('exit', codigo => {
  limpar()
  process.exit(codigo ?? 0)
})
