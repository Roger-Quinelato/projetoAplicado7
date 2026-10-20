import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

// Pacote E (#61): acesso por papel, feedback do despacho, conectividade observada, edição de contato,
// cancelamento de fatura e contraste com registros preenchidos.
const ADMIN = { Authorization: 'Bearer demo-admin' }

async function contratoFaturado(request: APIRequestContext, prefixo: string) {
  const { nome, email } = dadosUnicos(prefixo)
  const cliente = await (await request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  const contrato = await (await request.post('/api/v1/contracts/drafts', {
    headers: { ...ADMIN, 'Idempotency-Key': `e-draft-${cliente.customerId}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: amanha, billing: { amount: 1234.56, currency: 'BRL', cycle: 'MONTHLY' }, slaHours: 8 },
  })).json()
  expect((await request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...ADMIN, 'Idempotency-Key': `e-act-${contrato.contractId}` } })).ok()).toBe(true)
  expect((await request.post('/api/v1/integration/outbox/dispatch', { headers: ADMIN })).ok()).toBe(true)
  const [fatura] = await (await request.get(`/api/v1/finance/invoices?contractId=${contrato.contractId}`, { headers: ADMIN })).json()
  return { cliente, contrato, fatura, nome, email }
}

/** O cartão carregou: nenhum alerta de erro dentro dele. */
async function cartaoCarregado(page: Page, titulo: string) {
  const cartao = page.getByRole('region', { name: titulo, exact: true })
  await expect(cartao).toBeVisible()
  await expect(cartao.getByText('Carregando', { exact: false })).toHaveCount(0)
  await expect(cartao.getByRole('alert')).toHaveCount(0)
}

const PAPEIS = [
  { token: 'demo-commercial', contexto: 'CRM', cartao: 'Clientes' },
  { token: 'demo-contracts', contexto: 'Reservas e contratos', cartao: 'Reservas' },
  { token: 'demo-finance', contexto: 'Financeiro', cartao: 'Faturas' },
  { token: 'demo-support', contexto: 'Atendimento', cartao: 'Chamados' },
  { token: 'demo-operations', contexto: 'Workflow', cartao: 'Processos' },
]

for (const { token, contexto, cartao } of PAPEIS) {
  test(`${token} entra e usa ${contexto}; consulta proibida mostra a negativa, não lista vazia`, async ({ page }) => {
    await entrar(page, token)
    await irPara(page, contexto)
    await cartaoCarregado(page, cartao)
    await irPara(page, 'Visão geral')
    await expect(page.getByRole('region', { name: 'Totais do ambiente' }).getByRole('alert')).toContainText('Seu papel não tem permissão')
  })
}

test('despacho com falhas não é anunciado como sucesso', async ({ page }) => {
  await entrar(page, 'demo-admin')
  await page.route('**/api/v1/integration/outbox/dispatch', route => route.fulfill({ status: 200, json: { processed: 1, failed: 2 } }))
  await page.getByRole('button', { name: 'Despachar eventos pendentes' }).click()
  const aviso = page.getByRole('alert').filter({ hasText: 'Despacho da outbox' })
  await expect(aviso).toContainText('concluído com falhas. 1 evento(s) processado(s), 2 com falha.')
  await expect(aviso).toContainText('Falhas de integração')
  await expect(page.getByText('Despacho da outbox: concluído.')).toHaveCount(0)
})

test('indicador de conexão reflete a resposta observada da API, não a autenticação', async ({ page }) => {
  await entrar(page, 'demo-admin')
  const estado = page.locator('.link-status .link-text')
  await expect(estado).toContainText('API respondeu às')
  await page.route('**/health/ready', route => route.abort('failed'))
  await page.locator('.link-status').getByRole('button', { name: 'Verificar' }).click()
  await expect(estado).toContainText('Sem resposta da API às')
  await page.unroute('**/health/ready')
  await page.route('**/health/ready', route => route.fulfill({ status: 503, json: { detail: 'Banco indisponível' } }))
  await page.locator('.link-status').getByRole('button', { name: 'Verificar' }).click()
  await expect(estado).toContainText('mas o banco está indisponível')
  await expect(page.locator('.link-status').getByRole('status')).toHaveText('Conexão com a API: banco indisponível')
})

test('contato é editado na tela do CRM', async ({ page }) => {
  const { nome, email } = dadosUnicos('contato')
  const cliente = await (await page.request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email } })).json()
  const contato = `Contato ${nome}`
  expect((await page.request.post('/api/v1/crm/contacts', { headers: ADMIN, data: { customerId: cliente.customerId, name: contato, email: `c-${email}`, phone: '+5531999990000' } })).ok()).toBe(true)
  await entrar(page, 'demo-commercial')
  await irPara(page, 'CRM')
  const linha = page.getByRole('region', { name: 'Tabela: Contatos' }).getByRole('row').filter({ hasText: contato })
  await linha.getByRole('button', { name: 'Editar' }).click()
  const form = page.getByRole('form', { name: 'Editar contato' })
  await form.getByLabel('Telefone').fill('+5531988880000')
  await form.getByRole('button', { name: 'Salvar contato' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Alteração de contato: concluído.' })).toBeVisible()
  await expect(linha).toContainText('+5531988880000')
})

test('fatura em aberto e sem pagamento é cancelada com motivo', async ({ page }) => {
  const { fatura } = await contratoFaturado(page.request, 'cancela')
  await entrar(page, 'demo-finance')
  await irPara(page, 'Financeiro')
  const linha = page.getByRole('region', { name: 'Tabela: Faturas' }).getByRole('row').filter({ hasText: fatura.invoiceId.slice(0, 8) })
  await linha.getByRole('button', { name: 'Cancelar…' }).click()
  await page.getByRole('form', { name: 'Cancelar fatura' }).getByRole('button', { name: 'Confirmar cancelamento' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Cancelamento de fatura: concluído.' })).toBeVisible()
  await expect(linha).toContainText('Cancelado')
  await expect(linha.getByRole('button', { name: 'Cancelar…' })).toHaveCount(0)
})

test('contraste WCAG AA com registros preenchidos em todos os contextos', async ({ page }, info) => {
  const { cliente, contrato } = await contratoFaturado(page.request, 'contraste')
  await page.request.post('/api/v1/support/tickets', { headers: { ...ADMIN, 'Idempotency-Key': `e-ticket-${contrato.contractId}` }, data: {
    customerId: cliente.customerId, contractId: contrato.contractId, serviceCode: 'RENTAL-FLEX', category: 'OUTAGE', description: 'Chamado sintético',
  } })
  await page.request.post('/api/v1/integration/outbox/dispatch', { headers: ADMIN })
  await entrar(page, 'demo-admin')
  const violacoes: Record<string, string[]> = {}
  for (const rota of ['#/', '#/crm', '#/reservas', '#/financeiro', '#/atendimento', '#/workflow']) {
    await page.evaluate(destino => { window.location.hash = destino }, rota.slice(1))
    await page.getByRole('heading', { level: 1 }).waitFor()
    await expect(page.getByText('Carregando', { exact: false })).toHaveCount(0)
    const { violations } = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
    violacoes[rota] = violations.flatMap(v => v.nodes.map(n => n.target.join(' ')))
  }
  await info.attach('contraste.json', { body: JSON.stringify(violacoes, null, 2), contentType: 'application/json' })
  expect(violacoes).toEqual({ '#/': [], '#/crm': [], '#/reservas': [], '#/financeiro': [], '#/atendimento': [], '#/workflow': [] })
})
