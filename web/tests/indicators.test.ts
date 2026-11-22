import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  contractIndicator, dispatchSummary, failureIndicator, invoiceIndicator, pendingLabel, processIndicator, ticketIndicator,
} from '../src/indicators.ts'

test('título da barra de pendências concorda com a quantidade', () => {
  assert.equal(pendingLabel(0), 'Nenhuma pendência para processar')
  assert.equal(pendingLabel(1), '1 pendência para processar')
  assert.equal(pendingLabel(3), '3 pendências para processar')
})

test('resumo da atualização separa itens processados de itens com problema', () => {
  const at = new Date(2026, 9, 19, 18, 42)
  assert.equal(dispatchSummary({ processed: 1, failed: 0 }, at), 'Última atualização às 18:42: 1 item processado, nenhum problema.')
  assert.equal(dispatchSummary({ processed: 0, failed: 2 }, at), 'Última atualização às 18:42: 0 itens processados, 2 itens com problema.')
})

test('contratos ativos sobre o total', () => {
  assert.deepEqual(contractIndicator({ total: 3, active: 1 }), { label: 'Contratos ativos', value: '1', detail: 'de 3 contratos' })
  assert.equal(contractIndicator({ total: 1, active: 1 }).detail, 'de 1 contrato')
})

test('faturas a receber mostram o saldo por moeda calculado no servidor', () => {
  const result = invoiceIndicator({ receivable: 3, balances: [{ currency: 'BRL', amount: 3100 }] })
  assert.equal(result.value, '3')
  assert.match(result.detail, /^R\$\s3\.100,00 a receber$/)
  assert.match(invoiceIndicator({ receivable: 2, balances: [{ currency: 'BRL', amount: 10 }, { currency: 'USD', amount: 5 }] }).detail, /^R\$\s10,00 \+ US\$\s5,00 a receber$/)
  assert.equal(invoiceIndicator({ receivable: 0, balances: [] }).detail, 'nada a receber')
})

test('chamados no prazo entre os abertos', () => {
  assert.deepEqual(ticketIndicator({ open: 2, withinSla: 1 }), { label: 'Chamados no prazo', value: '1', detail: 'de 2 em aberto' })
  assert.equal(ticketIndicator({ open: 0, withinSla: 0 }).detail, 'nenhum chamado em aberto')
})

test('processos em andamento sobre o total', () => {
  assert.deepEqual(processIndicator({ total: 3, running: 1 }), { label: 'Operações em andamento', value: '1', detail: 'de 3 operações' })
})

test('falhas de integração', () => {
  assert.equal(failureIndicator([]).detail, 'nada a reprocessar')
  assert.equal(failureIndicator([{}]).detail, 'aguardando reprocessamento')
})
