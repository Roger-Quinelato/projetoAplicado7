import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

// Revisão do #67: a barra de eventos não pode travar com um resumo desatualizado, e o link "Falhas" leva ao cartão.
const ADMIN = { Authorization: 'Bearer demo-admin' }

test('evento criado fora da aba aparece quando a janela volta a ficar visível e pode ser despachado', async ({ page }) => {
  expect((await page.request.post('/api/v1/integration/outbox/dispatch', { headers: ADMIN })).ok()).toBe(true)
  await entrar(page, 'demo-admin')
  const barra = page.getByRole('region', { name: 'Eventos de integração' })
  await expect(barra).toContainText('Nenhum evento aguardando despacho')

  // Outro cliente da API (outra aba, /docs ou script) ativa um contrato: o evento fica pendente na outbox.
  const { nome, email } = dadosUnicos('barra')
  const cliente = await (await page.request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  const contrato = await (await page.request.post('/api/v1/contracts/drafts', {
    headers: { ...ADMIN, 'Idempotency-Key': `barra-draft-${cliente.customerId}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: amanha, billing: { amount: 100, currency: 'BRL', cycle: 'ONCE' }, slaHours: 8 },
  })).json()
  expect((await page.request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...ADMIN, 'Idempotency-Key': `barra-act-${contrato.contractId}` } })).ok()).toBe(true)

  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  await expect(barra).toContainText('1 evento aguardando despacho')
  await barra.getByRole('button', { name: 'Despachar eventos' }).click()
  await expect(barra).toContainText('1 evento entregue, nenhuma falha.')
  await expect(barra).toContainText('Nenhum evento aguardando despacho')
})

test('link "Falhas" leva o foco ao cartão de falhas, de outra tela e da própria Visão geral', async ({ page }) => {
  await entrar(page, 'demo-admin')
  const barra = page.getByRole('region', { name: 'Eventos de integração' })
  const cartao = page.getByRole('region', { name: 'Falhas de integração' })

  await irPara(page, 'CRM')
  await barra.getByRole('link', { name: /Falhas/ }).click()
  await expect(cartao).toBeFocused()

  await page.getByRole('heading', { level: 1 }).focus()
  await barra.getByRole('link', { name: /Falhas/ }).click()
  await expect(cartao).toBeFocused()
})
