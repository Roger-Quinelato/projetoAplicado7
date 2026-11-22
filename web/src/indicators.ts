// Textos e indicadores derivados das listas da API, sem JSX, para os testes com `node --test`.
import type { ContractSummary, DispatchResult, InvoiceSummary, ProcessSummary, TicketSummary } from './api'

export interface Indicator { label: string, value: string, detail: string }

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

/** Título da barra superior para a quantidade de pendências que aguardam a atualização dos processos. */
export function pendingLabel(pending: number): string {
  return pending === 0 ? 'Nenhuma pendência para processar' : `${plural(pending, 'pendência', 'pendências')} para processar`
}

/** Resumo da última atualização; `failed` são itens que ainda podem ser tentados de novo. */
export function dispatchSummary(result: DispatchResult, at: Date): string {
  const hour = at.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const failed = result.failed === 0 ? 'nenhum problema' : `${plural(result.failed, 'item', 'itens')} com problema`
  return `Última atualização às ${hour}: ${plural(result.processed, 'item processado', 'itens processados')}, ${failed}.`
}

function currencyTotal(balances: InvoiceSummary['balances']): string {
  return balances.map(({ currency, amount }) => {
    try { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(amount) }
    catch { return `${currency} ${amount.toFixed(2)}` }
  }).join(' + ')
}

// Os indicadores partem dos resumos contados no servidor (#73), não das listagens limitadas a 200.
export function contractIndicator({ total, active }: ContractSummary): Indicator {
  return { label: 'Contratos ativos', value: String(active), detail: `de ${plural(total, 'contrato', 'contratos')}` }
}

export function invoiceIndicator({ receivable, balances }: InvoiceSummary): Indicator {
  return { label: 'Faturas em aberto', value: String(receivable), detail: receivable ? `${currencyTotal(balances)} a receber` : 'nada a receber' }
}

export function ticketIndicator({ open, withinSla }: TicketSummary): Indicator {
  return { label: 'Chamados no prazo', value: String(withinSla), detail: open ? `de ${open} em aberto` : 'nenhum chamado em aberto' }
}

export function processIndicator({ total, running }: ProcessSummary): Indicator {
  return { label: 'Operações em andamento', value: String(running), detail: `de ${plural(total, 'operação', 'operações')}` }
}

export function failureIndicator(failures: unknown[]): Indicator {
  return { label: 'Falhas de integração', value: String(failures.length), detail: failures.length ? 'aguardando reprocessamento' : 'nada a reprocessar' }
}
