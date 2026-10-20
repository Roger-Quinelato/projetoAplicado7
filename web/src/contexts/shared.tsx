import type { ApiResult, DispatchResult } from '../api'
import { useSession } from '../ui'

/** Resumo do despacho; com falha, diz o que acontece com os eventos que não foram processados. */
export function describeDispatch(d: DispatchResult): string {
  if (d.processed === 0 && d.failed === 0) return 'Nenhum evento pendente.'
  const summary = `${d.processed} evento(s) processado(s), ${d.failed} com falha.`
  return d.failed === 0 ? summary : `${summary} Cada falha conta uma tentativa: abaixo do limite, o evento continua pendente para o próximo despacho; ao atingir o limite, vai para Falhas de integração (Visão geral), onde pode ser reprocessado.`
}

/**
 * Despacho explícito da outbox (papéis operations e admin). No protótipo, os consumidores internos
 * de Finance, Workflow e Contracts só reagem aos eventos depois deste despacho.
 */
export function DispatchButton({ busy, run, onDone, label = 'Despachar eventos pendentes' }: {
  busy: boolean
  run: <T>(label: string, action: () => Promise<ApiResult<T>>, describe?: (data: T) => string, partial?: (data: T) => boolean) => Promise<ApiResult<T> | null>
  onDone: () => void
  label?: string
}) {
  const { api } = useSession()
  return <button type="button" disabled={busy} onClick={() => void run<DispatchResult>('Despacho da outbox', () => api.dispatchOutbox(), describeDispatch,
    d => d.failed > 0).then(r => { if (r) onDone() })}>
    {label}
  </button>
}
