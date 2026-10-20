import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

const admin = { Authorization: 'Bearer demo-admin' }

test('Workflow: processo pela origem, tarefa criada, iniciada e cancelada com confirmação', async ({ page }) => {
  const { nome, email } = dadosUnicos('wf')
  const sufixo = Math.random().toString(36).slice(2)
  const cliente = await (await page.request.post('/api/v1/crm/customers', { headers: admin, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const contrato = await (await page.request.post('/api/v1/contracts/drafts', {
    headers: { ...admin, 'Idempotency-Key': `e2e-draft-${sufixo}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: '2026-10-20', billing: { amount: 700, currency: 'BRL', cycle: 'ONCE' }, slaHours: 8 },
  })).json()
  await page.request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...admin, 'Idempotency-Key': `e2e-act-${sufixo}` } })
  await page.request.post('/api/v1/integration/outbox/dispatch', { headers: admin })

  await entrar(page, 'demo-admin')
  await irPara(page, 'Workflow')
  const processo = page.getByRole('region', { name: 'Tabela: Processos' }).getByRole('row').filter({ hasText: contrato.contractId.slice(0, 8) })
  await expect(processo).toContainText('Preparação de retirada')
  await expect(processo).toContainText('Contrato')
  await processo.getByRole('button', { name: 'Ver tarefas' }).click()

  const titulo = `Vistoriar ${sufixo}`
  await page.getByRole('button', { name: 'Criar tarefa' }).click()
  const form = page.getByRole('form', { name: 'Criar tarefa' })
  await form.getByLabel('Título da tarefa').fill(titulo)
  await form.getByRole('button', { name: 'Criar tarefa' }).click()
  await expect(page.getByRole('status').filter({ hasText: `Tarefa “${titulo}” criada.` })).toBeVisible()

  const tarefa = page.getByRole('region', { name: 'Tabela: Tarefas' }).getByRole('row').filter({ hasText: titulo })
  await tarefa.getByRole('button', { name: 'Iniciar' }).click()
  await expect(tarefa).toContainText('Em andamento')

  await tarefa.getByRole('button', { name: `Mais ações: tarefa ${titulo}` }).click()
  await page.getByRole('menuitem', { name: 'Cancelar tarefa…' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Manter tarefa' }).click()
  await expect(tarefa).toContainText('Em andamento')

  await tarefa.getByRole('button', { name: `Mais ações: tarefa ${titulo}` }).click()
  await page.getByRole('menuitem', { name: 'Cancelar tarefa…' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar tarefa' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'cancelada' })).toBeVisible()
  await expect(tarefa).toContainText('Cancelad')
})
