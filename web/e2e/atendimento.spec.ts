import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

const admin = { Authorization: 'Bearer demo-admin' }

test('Atendimento: erro de campo em texto, abertura pelo contrato, resolução e histórico', async ({ page }) => {
  const { nome, email } = dadosUnicos('chamado')
  const sufixo = Math.random().toString(36).slice(2)
  const cliente = await (await page.request.post('/api/v1/crm/customers', { headers: admin, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const contrato = await (await page.request.post('/api/v1/contracts/drafts', {
    headers: { ...admin, 'Idempotency-Key': `e2e-draft-${sufixo}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: '2026-10-20', billing: { amount: 900, currency: 'BRL', cycle: 'ONCE' }, slaHours: 8 },
  })).json()
  await page.request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...admin, 'Idempotency-Key': `e2e-act-${sufixo}` } })

  await entrar(page, 'demo-admin')
  await irPara(page, 'Atendimento')
  await page.getByRole('button', { name: 'Abrir chamado' }).click()
  const form = page.getByRole('form', { name: 'Abrir chamado' })
  await form.getByRole('button', { name: 'Consultar elegibilidade e SLA' }).click()
  await expect(form.getByText('Escolha um contrato ativo para consultar a elegibilidade e o SLA.')).toBeVisible()
  await expect(form.getByLabel('Contrato ativo')).toHaveAttribute('aria-invalid', 'true')

  await page.goto(`/#/atendimento?contract=${contrato.contractId}`)
  const aberto = page.getByRole('form', { name: 'Abrir chamado' })
  await expect(aberto.getByLabel('Contrato ativo')).toHaveValue(contrato.contractId)
  await aberto.getByRole('button', { name: 'Consultar elegibilidade e SLA' }).click()
  await expect(aberto.getByRole('status')).toContainText('Elegível · SLA 8 h')
  await aberto.getByRole('button', { name: 'Abrir chamado' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'aberto com prioridade alta' })).toContainText('Prazo do SLA')

  const linha = page.getByRole('region', { name: 'Tabela: Chamados' }).getByRole('row').filter({ hasText: contrato.contractId.slice(0, 8) })
  await expect(linha).toContainText('No prazo')
  await linha.getByRole('button', { name: 'Resolver' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'resolvido' })).toBeVisible()
  await expect(linha).toContainText('Resolvido')

  await linha.getByRole('button', { name: /^Mais ações: chamado/ }).click()
  await page.getByRole('menuitem', { name: 'Histórico' }).click()
  await expect(page.getByRole('region', { name: 'Tabela: Histórico do chamado' })).toContainText('Resolução')
})
