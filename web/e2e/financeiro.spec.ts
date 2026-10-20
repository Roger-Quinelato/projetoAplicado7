import { expect, test, type APIRequestContext } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

const admin = { Authorization: 'Bearer demo-admin' }

/** Prepara pela API um contrato ativo com a primeira fatura gerada (cliente, rascunho, ativação e despacho). */
async function contratoFaturado(request: APIRequestContext, prefixo: string) {
  const { nome, email } = dadosUnicos(prefixo)
  const cliente = await (await request.post('/api/v1/crm/customers', { headers: admin, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const sufixo = Math.random().toString(36).slice(2)
  const contrato = await (await request.post('/api/v1/contracts/drafts', {
    headers: { ...admin, 'Idempotency-Key': `e2e-draft-${sufixo}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: '2026-10-20', billing: { amount: 1000, currency: 'BRL', cycle: 'MONTHLY' }, slaHours: 8 },
  })).json()
  await request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...admin, 'Idempotency-Key': `e2e-act-${sufixo}` } })
  await request.post('/api/v1/integration/outbox/dispatch', { headers: admin })
  return contrato.contractId as string
}

test('Financeiro: pagamento parcial pela linha da fatura e painel de vencimento', async ({ page }) => {
  const contractId = await contratoFaturado(page.request, 'fin')
  await entrar(page, 'demo-admin')
  await irPara(page, 'Financeiro')

  const linha = page.getByRole('region', { name: 'Tabela: Faturas' }).getByRole('row').filter({ hasText: contractId.slice(0, 8) })
  await expect(linha).toContainText('Em aberto')
  await linha.getByRole('button', { name: 'Registrar pagamento' }).click()

  const form = page.getByRole('form', { name: 'Pagamento simulado' })
  await expect(form.getByLabel('Valor (R$)')).toHaveValue('1000.00')
  await form.getByLabel('Valor (R$)').fill('400')
  await form.getByRole('button', { name: 'Registrar pagamento' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Pagamento registrado' })).toContainText('saldo R$')
  await expect(linha).toContainText('Parcialmente paga')
  await expect(page.getByRole('region', { name: 'Tabela: Pagamentos' })).toContainText('400,00')

  await page.getByRole('button', { name: 'Verificar vencimento' }).click()
  await expect(page.getByRole('form', { name: 'Verificação de vencimento' })).toBeVisible()
  await page.getByRole('button', { name: 'Fechar' }).first().click()
  await expect(page.getByRole('form', { name: 'Verificação de vencimento' })).toHaveCount(0)
})
