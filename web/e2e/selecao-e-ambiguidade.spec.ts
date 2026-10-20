import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

// #34: seleção de clientes além da primeira página e comando com resposta perdida depois da gravação.
const ADMIN = { Authorization: 'Bearer demo-admin' }
const LOTE = 205 // acima do limite de 200 da listagem usada antes pelos seletores

async function criarCliente(request: APIRequestContext, nome: string, email: string): Promise<string> {
  const resposta = await request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email, eligible: true, consentService: true } })
  expect(resposta.status()).toBe(201)
  return (await resposta.json()).customerId as string
}

/** Clientes "Cliente lote…" ficam antes, em ordem de nome, de qualquer cliente "Zz…" criado pelo roteiro. */
test.beforeAll(async ({ playwright }, info) => {
  const request = await playwright.request.newContext({ baseURL: info.project.use.baseURL })
  const { email } = dadosUnicos('lote')
  // Sequencial: o SQLite local dos roteiros não aceita escritas concorrentes.
  for (let i = 0; i < LOTE; i++) await criarCliente(request, `Cliente lote ${String(i).padStart(3, '0')}`, email.replace('@', `-${i}@`))
  await request.dispose()
})

/** Faz o servidor processar o comando e derruba a resposta, uma única vez. Devolve as chaves enviadas. */
async function perderPrimeiraResposta(page: Page, caminho: string) {
  const chaves: string[] = []
  let perdida = false
  await page.route(`**${caminho}`, async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    chaves.push(route.request().headers()['idempotency-key'] ?? '')
    if (perdida) return route.continue()
    perdida = true
    await route.fetch() // o servidor grava e responde; o navegador não recebe a resposta
    await route.abort('failed')
  })
  return chaves
}

test('reserva: cliente além dos 200 primeiros e resposta perdida geram um único registro', async ({ page }) => {
  const { nome, email } = dadosUnicos('zz-reserva')
  const alvo = `Zz ${nome}`
  const customerId = await criarCliente(page.request, alvo, email)
  await entrar(page, 'demo-admin')
  await irPara(page, 'Reservas e contratos')
  const form = page.getByRole('form', { name: 'Nova reserva' })
  const cliente = form.getByLabel('Cliente (CRM)', { exact: true })

  await test.step('pagina o seletor até o cliente', async () => {
    const opcao = cliente.locator(`option[value="${customerId}"]`)
    await expect(cliente.locator('option').nth(1)).toBeAttached()
    await expect(opcao).toHaveCount(0)
    for (let pagina = 0; pagina < 10 && await opcao.count() === 0; pagina++) {
      await form.getByRole('button', { name: 'Próximos' }).click()
      await expect(form.getByText(/Clientes ativos \d+–\d+/)).toBeVisible()
    }
    await cliente.selectOption(customerId)
  })

  const chaves = await perderPrimeiraResposta(page, '/api/v1/contracts/reservations')
  await test.step('resposta perdida deixa o pedido pendente', async () => {
    await form.getByRole('button', { name: 'Registrar reserva' }).click()
    await expect(page.getByRole('alert')).toContainText('Registro de reserva: não foi possível confirmar; a operação pode ter sido registrada.')
    await expect(page.getByRole('status', { name: 'Pedido sem confirmação: Registro de reserva' })).toBeVisible()
    await expect(cliente).toHaveValue(customerId)
  })

  await test.step('dados editados não viram uma nova criação', async () => {
    await form.getByLabel('Valor (R$)').fill('1300.00')
    await form.getByRole('button', { name: 'Registrar reserva' }).click()
    await expect(page.getByRole('alert')).toContainText('Há um pedido anterior sem confirmação.')
    expect(chaves).toHaveLength(1)
  })

  await test.step('repetir o pedido original reaproveita a resposta gravada', async () => {
    await page.getByRole('button', { name: 'Repetir pedido original' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Repetição idempotente' })).toBeVisible()
    await expect(page.getByRole('status', { name: 'Pedido sem confirmação: Registro de reserva' })).toHaveCount(0)
    expect(chaves).toHaveLength(2)
    expect(chaves[1]).toBe(chaves[0])
  })

  const reservas = await (await page.request.get(`/api/v1/contracts/reservations?customerId=${customerId}`, { headers: ADMIN })).json()
  expect(reservas).toHaveLength(1)
  expect(Number(reservas[0].amount)).toBe(1200)
})

test('chamado: contrato da URL de cliente além dos 200 primeiros e resposta perdida geram um único chamado', async ({ page }) => {
  const { nome, email } = dadosUnicos('zz-chamado')
  const customerId = await criarCliente(page.request, `Zz ${nome}`, email)
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  const rascunho = await page.request.post('/api/v1/contracts/drafts', {
    headers: { ...ADMIN, 'Idempotency-Key': `e2e-draft-${customerId}` },
    data: { customerId, serviceCode: 'RENTAL-FLEX', startsOn: amanha, billing: { amount: 2500, currency: 'BRL', cycle: 'MONTHLY' }, slaHours: 8 },
  })
  expect(rascunho.status()).toBe(201)
  const { contractId } = await rascunho.json()
  expect((await page.request.post(`/api/v1/contracts/${contractId}/activate`, { headers: { ...ADMIN, 'Idempotency-Key': `e2e-activate-${contractId}` } })).ok()).toBe(true)

  await entrar(page, 'demo-admin')
  await page.evaluate(destino => { window.location.hash = destino }, `/atendimento?contract=${contractId}`)
  const form = page.getByRole('form', { name: 'Abrir chamado' })

  await test.step('cliente e contrato vêm do UUID, fora da primeira página', async () => {
    await expect(form.getByLabel('Cliente', { exact: true })).toHaveValue(customerId)
    await expect(form.getByLabel('Contrato ativo')).toHaveValue(contractId)
  })

  const chaves = await perderPrimeiraResposta(page, '/api/v1/support/tickets')
  await form.getByRole('button', { name: 'Abrir chamado' }).click()
  await expect(page.getByRole('alert')).toContainText('Abertura de chamado: não foi possível confirmar')
  await page.getByRole('button', { name: 'Repetir pedido original' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Repetição idempotente' })).toBeVisible()
  expect(chaves).toEqual([chaves[0], chaves[0]])

  const chamados = (await (await page.request.get('/api/v1/support/tickets', { headers: ADMIN })).json() as { contractId: string }[])
    .filter(t => t.contractId === contractId)
  expect(chamados).toHaveLength(1)
})
