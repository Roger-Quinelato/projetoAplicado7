import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar } from './helpers'

// #73: os indicadores da Visão geral vêm dos resumos do servidor, não das listagens limitadas a 200.
const ADMIN = { Authorization: 'Bearer demo-admin' }
const ACIMA_DO_LIMITE = 205

test('Visão geral mostra o total de contratos acima do limite da listagem', async ({ page }) => {
  test.setTimeout(180_000)
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  for (let i = 0; i < ACIMA_DO_LIMITE; i++) {
    const { nome, email } = dadosUnicos(`ind${i}`)
    const cliente = await (await page.request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email, eligible: true, consentService: true } })).json()
    const rascunho = await page.request.post('/api/v1/contracts/drafts', {
      headers: { ...ADMIN, 'Idempotency-Key': `ind-${cliente.customerId}` },
      data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: amanha, billing: { amount: 100, currency: 'BRL', cycle: 'ONCE' }, slaHours: 8 },
    })
    expect(rascunho.status()).toBe(201)
  }

  const lista = await (await page.request.get('/api/v1/contracts', { headers: ADMIN })).json()
  const resumo = await (await page.request.get('/api/v1/contracts/summary', { headers: ADMIN })).json()
  expect(lista).toHaveLength(200)
  expect(resumo.total).toBeGreaterThanOrEqual(ACIMA_DO_LIMITE)

  await entrar(page, 'demo-admin')
  const situacao = page.getByRole('region', { name: 'Situação da demonstração' })
  await expect(situacao).toContainText(`de ${resumo.total} contratos`)
  await expect(situacao).not.toContainText('de 200 contratos')
})

test('indicadores acompanham os resumos de faturas, chamados e processos', async ({ page }) => {
  await entrar(page, 'demo-admin')
  const [faturas, chamados, processos] = await Promise.all(['/api/v1/finance/invoices/summary', '/api/v1/support/tickets/summary', '/api/v1/workflow/processes/summary']
    .map(async caminho => (await page.request.get(caminho, { headers: ADMIN })).json()))
  const situacao = page.getByRole('region', { name: 'Situação da demonstração' })
  await expect(situacao).toContainText(faturas.receivable ? 'a receber' : 'nada a receber')
  await expect(situacao).toContainText(chamados.open ? `de ${chamados.open} em aberto` : 'nenhum chamado em aberto')
  await expect(situacao).toContainText(`de ${processos.total} processo`)
})
