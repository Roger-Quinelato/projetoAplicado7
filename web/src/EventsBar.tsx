import { useState } from 'react'
import type { DispatchResult } from './api'
import { dispatchSummary, pendingLabel } from './indicators'
import { ErrorPanel, useActions, useResource, useSession } from './ui'

/**
 * Barra global de eventos: quantos eventos aguardam na outbox e o despacho explícito (operations e admin).
 * Perfis sem esses papéis recebem 403 na consulta e não veem a barra.
 */
export default function EventsBar() {
  const { api, eventsVersion, dispatched } = useSession()
  const summary = useResource(a => a.outboxSummary(), [eventsVersion])
  const { feedback, busy, run, clear } = useActions()
  const [last, setLast] = useState<{ result: DispatchResult, at: Date } | null>(null)

  if (summary.status === 'error' && summary.error.status === 403) return null

  async function dispatch() {
    const result = await run('Despacho dos eventos', () => api.dispatchOutbox())
    if (result) { setLast({ result: result.data, at: new Date() }); clear(); dispatched() }
  }

  const pending = summary.data?.pending
  const failed = summary.data?.failed ?? 0
  const title = summary.status === 'error' ? 'Não foi possível consultar os eventos pendentes'
    : pending === undefined ? 'Consultando eventos pendentes…' : pendingLabel(pending)
  const detail = last ? dispatchSummary(last.result, last.at) : 'O despacho é manual nesta demonstração: os outros contextos só reagem aos eventos depois dele.'

  return <section className="events-bar" aria-label="Eventos de integração">
    <div className="events-row">
      <span className={`events-dot ${pending ? 'pending' : ''}`} aria-hidden="true" />
      <div className="events-text" aria-live="polite">
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
      <a href="#/" className="events-failures">Falhas ({failed})</a>
      {summary.status === 'error'
        ? <button type="button" className="secondary" onClick={() => void summary.reload()}>Tentar novamente</button>
        : <button type="button" disabled={busy || !pending} onClick={() => void dispatch()}>{busy ? 'Despachando…' : 'Despachar eventos'}</button>}
    </div>
    {feedback?.kind === 'error' && <ErrorPanel error={feedback.error} context={feedback.message} onClose={clear} />}
  </section>
}
