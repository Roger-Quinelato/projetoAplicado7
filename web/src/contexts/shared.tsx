import type { ApiResult, DispatchResult } from '../api'
import { useSession } from '../ui'

/**
 * Despacho explícito da outbox (papéis operations e admin). No protótipo, os consumidores internos
 * de Finance, Workflow e Contracts só reagem aos eventos depois deste despacho.
 */
export function DispatchButton({ busy, run, onDone, label = 'Despachar eventos pendentes' }: {
  busy: boolean
  run: <T>(label: string, action: () => Promise<ApiResult<T>>, describe?: (data: T) => string) => Promise<ApiResult<T> | null>
  onDone: () => void
  label?: string
}) {
  const { api } = useSession()
  return <button type="button" disabled={busy} onClick={() => void run<DispatchResult>('Despacho da outbox', () => api.dispatchOutbox(),
    d => `${d.processed} evento(s) processado(s), ${d.failed} com falha.`).then(r => { if (r) onDone() })}>
    {label}
  </button>
}
