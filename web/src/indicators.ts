// Textos e indicadores derivados das listas da API, sem JSX, para os testes com `node --test`.
import type { Contract, DispatchResult, Invoice, Process, Ticket } from './api'

export interface Indicator { label: string, value: string, detail: string }

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

/** Título da barra de eventos para a quantidade de eventos pendentes na outbox. */
export function pendingLabel(pending: number): string {
  return pending === 0 ? 'Nenhum evento aguardando despacho' : `${plural(pending, 'evento', 'eventos')} aguardando despacho`
}

/** Resumo do último despacho; `failed` são tentativas desta rodada, que ainda podem ser repetidas. */
export function dispatchSummary(result: DispatchResult, at: Date): string {
  const hour = at.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const failed = result.failed === 0 ? 'nenhuma falha' : `${plural(result.failed, 'tentativa', 'tentativas')} com falha`
  return `Último despacho às ${hour}: ${plural(result.processed, 'evento entregue', 'eventos entregues')}, ${failed}.`
}

function currencyTotal(invoices: Invoice[]): string {
  const totals = new Map<string, number>()
  for (const i of invoices) totals.set(i.currency, (totals.get(i.currency) ?? 0) + Number(i.balance))
  return [...totals].map(([currency, value]) => {
    try { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(value) }
    catch { return `${currency} ${value.toFixed(2)}` }
  }).join(' + ')
}

export function contractIndicator(contracts: Contract[]): Indicator {
  const active = contracts.filter(c => c.status === 'ACTIVE').length
  return { label: 'Contratos ativos', value: String(active), detail: `de ${plural(contracts.length, 'contrato', 'contratos')}` }
}

const RECEIVABLE = new Set(['OPEN', 'PARTIALLY_PAID', 'OVERDUE'])
export function invoiceIndicator(invoices: Invoice[]): Indicator {
  const open = invoices.filter(i => RECEIVABLE.has(i.status))
  return { label: 'Faturas em aberto', value: String(open.length), detail: open.length ? `${currencyTotal(open)} a receber` : 'nada a receber' }
}

export function ticketIndicator(tickets: Ticket[]): Indicator {
  const open = tickets.filter(t => t.status === 'OPEN')
  const within = open.filter(t => t.slaStatus === 'WITHIN').length
  return { label: 'Chamados no prazo', value: String(within), detail: open.length ? `de ${open.length} em aberto` : 'nenhum chamado em aberto' }
}

const FINISHED = new Set(['COMPLETED', 'CANCELLED'])
export function processIndicator(processes: Process[]): Indicator {
  const running = processes.filter(p => !FINISHED.has(p.state)).length
  return { label: 'Processos em andamento', value: String(running), detail: `de ${plural(processes.length, 'processo', 'processos')}` }
}

export function failureIndicator(failures: unknown[]): Indicator {
  return { label: 'Falhas de integração', value: String(failures.length), detail: failures.length ? 'aguardando reprocessamento' : 'nada a reprocessar' }
}
