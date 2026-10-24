import { expect, test } from '@playwright/test'
import { entrar, irPara } from './helpers'

const contextos = [
  { rotulo: 'Visão geral', hash: '#/' },
  { rotulo: 'CRM', hash: '#/crm' },
  { rotulo: 'Reservas e contratos', hash: '#/reservas' },
  { rotulo: 'Financeiro', hash: '#/financeiro' },
  { rotulo: 'Atendimento', hash: '#/atendimento' },
  { rotulo: 'Workflow', hash: '#/workflow' },
]

test.beforeEach(async ({ page }) => entrar(page, 'demo-admin'))

test('os seis destinos abrem pelo menu com título e item ativo', async ({ page }) => {
  for (const { rotulo, hash } of contextos) {
    await irPara(page, rotulo)
    await expect(page.getByRole('heading', { level: 1, name: rotulo })).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'CONTEXTOS' }).getByRole('link', { name: rotulo, exact: true }))
      .toHaveAttribute('aria-current', 'page')
    expect(new URL(page.url()).hash).toBe(hash)
  }
})

test('abrir a URL com hash mantém a sessão e mostra o contexto', async ({ page }) => {
  for (const { rotulo, hash } of contextos.slice(1)) {
    await page.goto(`/${hash}`)
    await expect(page.getByRole('heading', { level: 1, name: rotulo })).toBeVisible()
  }
})

test('hash desconhecido cai na Visão geral', async ({ page }) => {
  await page.goto('/#/nao-existe')
  await expect(page.getByRole('heading', { level: 1, name: 'Visão geral' })).toBeVisible()
})
