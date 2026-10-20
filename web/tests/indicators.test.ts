import assert from 'node:assert/strict'
import { test } from 'node:test'

import type { Contract, Invoice, Process, Ticket } from '../src/api.ts'
import {
  contractIndicator, dispatchSummary, failureIndicator, invoiceIndicator, pendingLabel, processIndicator, ticketIndicator,
} from '../src/indicators.ts'

test('título da barra de eventos concorda com a quantidade', () => {
  assert.equal(pendingLabel(0), 'Nenhum evento aguardando despacho')
  assert.equal(pendingLabel(1), '1 evento aguardando despacho')
  assert.equal(pendingLabel(3), '3 eventos aguardando despacho')
})

test('resumo do despacho separa entregues de tentativas com falha', () => {
  const at = new Date(2026, 9, 19, 18, 42)
  assert.equal(dispatchSummary({ processed: 1, failed: 0 }, at), 'Último despacho às 18:42: 1 evento entregue, nenhuma falha.')
  assert.equal(dispatchSummary({ processed: 0, failed: 2 }, at), 'Último despacho às 18:42: 0 eventos entregues, 2 tentativas com falha.')
})

test('contratos ativos sobre o total', () => {
  const c = (status: Contract['status']) => ({ status }) as Contract
  assert.deepEqual(contractIndicator([c('ACTIVE'), c('DRAFT'), c('CLOSED')]), { label: 'Contratos ativos', value: '1', detail: 'de 3 contratos' })
})

test('faturas a receber somam o saldo das abertas, parciais e vencidas', () => {
  const i = (status: Invoice['status'], balance: number) => ({ status, balance, currency: 'BRL' }) as Invoice
  const result = invoiceIndicator([i('OPEN', 2500), i('OVERDUE', 500), i('PARTIALLY_PAID', 100), i('PAID', 0), i('CANCELLED', 900)])
  assert.equal(result.value, '3')
  assert.match(result.detail, /^R\$\s3\.100,00 a receber$/)
  assert.equal(invoiceIndicator([i('PAID', 0)]).detail, 'nada a receber')
})

test('chamados no prazo contam só os abertos dentro do SLA', () => {
  const t = (status: Ticket['status'], slaStatus: Ticket['slaStatus']) => ({ status, slaStatus }) as Ticket
  assert.deepEqual(ticketIndicator([t('OPEN', 'WITHIN'), t('OPEN', 'BREACHED'), t('RESOLVED', 'MET'), t('PENDING_ENTITLEMENT', 'PENDING')]),
    { label: 'Chamados no prazo', value: '1', detail: 'de 2 em aberto' })
  assert.equal(ticketIndicator([]).detail, 'nenhum chamado em aberto')
})

test('processos em andamento excluem concluídos e cancelados', () => {
  const p = (state: string) => ({ state }) as Process
  assert.deepEqual(processIndicator([p('STARTED'), p('COMPLETED'), p('CANCELLED')]), { label: 'Processos em andamento', value: '1', detail: 'de 3 processos' })
})

test('falhas de integração', () => {
  assert.equal(failureIndicator([]).detail, 'nada a reprocessar')
  assert.equal(failureIndicator([{}]).detail, 'aguardando reprocessamento')
})
