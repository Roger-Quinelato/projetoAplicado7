import { expect, test, type APIRequestContext } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

// Pacote F (#62): F2 e F3 pelo navegador. O cliente e o rascunho nascem pela API (o F1 pela UI já é coberto em f1.spec.ts).
const ADMIN = { Authorization: 'Bearer demo-admin' }

async function rascunho(request: APIRequestContext, prefixo: string, valor: number) {
  const { nome, email } = dadosUnicos(prefixo)
  const cliente = await (await request.post('/api/v1/crm/customers', { headers: ADMIN, data: { name: nome, email, eligible: true, consentService: true } })).json()
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)
  const contrato = await (await request.post('/api/v1/contracts/drafts', {
    headers: { ...ADMIN, 'Idempotency-Key': `f-draft-${cliente.customerId}` },
    data: { customerId: cliente.customerId, serviceCode: 'RENTAL-FLEX', startsOn: amanha, billing: { amount: valor, currency: 'BRL', cycle: 'ONCE' }, slaHours: 8 },
  })).json()
  return { cliente, contrato, nome }
}

test('F2: ativação → uma fatura paga em duas parcelas e uma preparação de retirada', async ({ page }) => {
  const { contrato, nome } = await rascunho(page.request, 'f2', 2500.35)
  const curto = contrato.contractId.slice(0, 8)
  await entrar(page, 'demo-admin')

  await test.step('ativa o contrato e despacha o evento', async () => {
    await irPara(page, 'Reservas e contratos')
    const linha = page.getByRole('region', { name: 'Tabela: Contratos' }).getByRole('row').filter({ hasText: nome })
    await linha.getByRole('button', { name: 'Ativar' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Contrato ativado.' })).toBeVisible()
    await expect(linha).toContainText('Ativo')
    // Barra global de pendências (#67), visível em todas as telas.
    const barra = page.getByRole('region', { name: 'Pendências para processar' })
    await barra.getByRole('button', { name: 'Atualizar processos' }).click()
    await expect(barra).toContainText('1 item processado, nenhum problema.')
  })

  await test.step('paga a fatura em duas parcelas com centavos', async () => {
    await irPara(page, 'Financeiro')
    const faturas = page.getByRole('region', { name: /^Tabela: (Faturas|Pagamentos|Histórico de faturas)$/ })
    const linha = faturas.getByRole('row').filter({ hasText: curto })
    await expect(linha).toHaveCount(1)
    await expect(linha).toContainText('2.500,35')
    for (const [valor, referencia] of [['1000.10', `F2-${curto}-1`], ['1500.25', `F2-${curto}-2`]]) {
      await linha.getByRole('button', { name: 'Selecionar' }).click()
      const form = page.getByRole('form', { name: 'Pagamento simulado' })
      await form.getByLabel('Valor (R$)').fill(valor)
      await form.getByRole('button', { name: 'Registrar pagamento' }).click()
      await expect(page.getByRole('status').filter({ hasText: 'Pagamento registrado.' })).toBeVisible()
    }
    await expect(linha).toContainText('Paga')
    await expect(linha).toContainText('R$ 0,00')
  })

  await test.step('a preparação de retirada existe uma única vez, mesmo com novo despacho', async () => {
    const barra = page.getByRole('region', { name: 'Pendências para processar' })
    await expect(barra).toContainText('Nenhuma pendência para processar')
    await barra.getByRole('button', { name: 'Atualizar processos' }).click()
    await expect(barra).toContainText('0 itens processados, nenhum problema.')
    await irPara(page, 'Operações')
    const processos = await (await page.request.get('/api/v1/workflow/processes', { headers: ADMIN })).json() as { processId: string, referenceId: string }[]
    const doContrato = processos.filter(p => p.referenceId === contrato.contractId)
    expect(doContrato).toHaveLength(1)
    // O quadro não mostra o código do processo; a unicidade vem da API e a tela só precisa listar o processo.
    await expect(page.getByRole('region', { name: 'Tabela: Operações Abertas' }).getByRole('row')).not.toHaveCount(0)
    const faturas = await (await page.request.get(`/api/v1/finance/invoices?contractId=${contrato.contractId}`, { headers: ADMIN })).json()
    expect(faturas).toHaveLength(1)
  })
})

test('F3: chamado com SLA → atribuição → resolução → processo concluído', async ({ page }) => {
  const { contrato } = await rascunho(page.request, 'f3', 900)
  expect((await page.request.post(`/api/v1/contracts/${contrato.contractId}/activate`, { headers: { ...ADMIN, 'Idempotency-Key': `f3-act-${contrato.contractId}` } })).ok()).toBe(true)
  await entrar(page, 'demo-admin')
  await page.evaluate(destino => { window.location.hash = destino }, `/atendimento?contract=${contrato.contractId}`)

  let curto = ''
  await test.step('consulta elegibilidade e abre o chamado de prioridade alta', async () => {
    const form = page.getByRole('form', { name: 'Abrir chamado' })
    await expect(form.getByLabel('Contrato ativo')).toHaveValue(contrato.contractId)
    await page.getByRole('button', { name: 'Ver direito a atendimento e SLA' }).click()
    await expect(page.getByText('Tem direito a atendimento, com SLA de 8 h').first()).toBeVisible()
    await form.getByRole('button', { name: 'Abrir chamado' }).click()
    const aviso = page.getByRole('status').filter({ hasText: 'Chamado aberto para o contrato' })
    await expect(aviso).toContainText('Prioridade alta')
    // A tabela não mostra o contrato: o chamado é identificado pela API e depois procurado na lista pelo código curto.
    const chamados = await (await page.request.get('/api/v1/support/tickets', { headers: ADMIN })).json() as { ticketId: string, contractId: string }[]
    curto = chamados.find(t => t.contractId === contrato.contractId)!.ticketId.slice(0, 8)
    await page.getByRole('region', { name: 'Pendências para processar' }).getByRole('button', { name: 'Atualizar processos' }).click()
    await expect(page.getByRole('region', { name: 'Pendências para processar' })).toContainText('itens processados, nenhum problema')
  })

  await test.step('atribui e resolve dentro do SLA', async () => {
    const linha = page.getByRole('region', { name: 'Tabela: Chamados' }).getByRole('row').filter({ hasText: curto })
    await linha.getByRole('button', { name: 'Atribuir…' }).click()
    await page.getByRole('form', { name: 'Atribuir chamado' }).getByRole('button', { name: 'Atribuir' }).click()
    await expect(linha.getByRole('button', { name: 'Reatribuir…' })).toBeVisible()
    await linha.getByRole('button', { name: 'Resolver' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Chamado resolvido dentro do prazo do SLA.' })).toBeVisible()
    // Resolvido, o chamado sai de Chamados e passa para o Histórico.
    await expect(linha).toHaveCount(0)
    await expect(page.getByRole('region', { name: 'Tabela: Histórico' }).getByRole('row').filter({ hasText: curto })).toContainText('Resolvido')
    await page.getByRole('region', { name: 'Pendências para processar' }).getByRole('button', { name: 'Atualizar processos' }).click()
    await expect(page.getByRole('region', { name: 'Pendências para processar' })).toContainText('item processado')
  })

  await test.step('o processo de resolução fica concluído', async () => {
    await irPara(page, 'Operações')
    const processos = await (await page.request.get('/api/v1/workflow/processes', { headers: ADMIN })).json() as { processId: string, referenceId: string, state: string }[]
    const doChamado = processos.find(p => p.referenceId.startsWith(curto))!
    expect(doChamado.state).toBe('COMPLETED')
    // Concluído, o processo sai de Operações Abertas e a tarefa concluída aparece no Histórico de Operações.
    await expect(page.getByRole('region', { name: 'Tabela: Histórico de Operações' })).toContainText('Concluída')
  })
})
