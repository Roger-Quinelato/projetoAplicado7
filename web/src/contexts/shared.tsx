import type { ApiResult, DispatchResult } from '../api'
import { useSession } from '../ui'

const items = (n: number) => `${n} ${n === 1 ? 'item' : 'itens'}`

/** Resumo da atualização dos processos. Com problema, diz o que a pessoa pode fazer. */
export function describeDispatch(d: DispatchResult): string {
  if (d.processed === 0 && d.failed === 0) return 'Não havia nada para atualizar.'
  const done = `${items(d.processed)} ${d.processed === 1 ? 'processado' : 'processados'}.`
  return d.failed === 0 ? done : `${done} ${items(d.failed)} não ${d.failed === 1 ? 'pôde' : 'puderam'} ser ${d.failed === 1 ? 'processado' : 'processados'} agora. Tente de novo em instantes. Se continuar, veja as Falhas na Visão geral.`
}

/**
 * Botão que faz a cobrança e as tarefas andarem depois de uma reserva ou de um chamado novo
 * (papéis operations e admin). No protótipo, essa atualização é manual.
 */
export function DispatchButton({ busy, run, onDone, label = 'Atualizar processos' }: {
  busy: boolean
  run: <T>(label: string, action: () => Promise<ApiResult<T>>, describe?: (data: T) => string, partial?: (data: T) => boolean) => Promise<ApiResult<T> | null>
  onDone: () => void
  label?: string
}) {
  const { api } = useSession()
  return <button type="button" disabled={busy} onClick={() => void run<DispatchResult>('Atualização dos processos', () => api.dispatchOutbox(), describeDispatch,
    d => d.failed > 0).then(r => { if (r) onDone() })}>
    {label}
  </button>
}
