import { useEffect, useState } from 'react'
import { asApiError, type ApiError, type ApiResult, type Api, type OperationTrace } from '../api'
import { FAILURES_CARD } from '../EventsBar'
import {
  contractIndicator, failureIndicator, invoiceIndicator, processIndicator, ticketIndicator, type Indicator,
} from '../indicators'
import {
  Card, ErrorPanel, Field, FeedbackBanner, Id, PageIntro, ResourceView, Status, Table, dateTime, text, useActions, useResource, useSession,
  type Resource,
} from '../ui'

/** Passos de cada fluxo e a tela onde são feitos; sem rota, o passo é feito na barra de eventos. */
const FLOWS: { title: string, steps: [string, string | null][] }[] = [
  { title: 'F1 · Contrato sem recadastro', steps: [['Cadastre um cliente fictício', '/crm'], ['Registre a reserva com esse cliente', '/reservas'], ['Gere o rascunho a partir da reserva', '/reservas']] },
  { title: 'F2 · Ativação, cobrança e retirada', steps: [['Ative o contrato em rascunho', '/reservas'], ['Despache os eventos', null], ['Confira a fatura e registre o pagamento', '/financeiro'], ['Confira a preparação de retirada', '/workflow']] },
  { title: 'F3 · Atendimento com SLA', steps: [['Consulte a elegibilidade e abra o chamado', '/atendimento'], ['Despache os eventos', null], ['Atribua e resolva o chamado', '/atendimento'], ['Despache e confira o processo concluído', '/workflow']] },
]
const DESTINATIONS: Record<string, string> = {
  '/crm': 'CRM', '/reservas': 'Reservas e contratos', '/financeiro': 'Financeiro', '/atendimento': 'Atendimento', '/workflow': 'Workflow',
}

/** Um indicador calculado a partir de uma lista; sem permissão ou com erro, mostra o motivo no lugar do número. */
function IndicatorTile<T>({ label, load, compute }: { label: string, load: (api: Api) => Promise<ApiResult<T>>, compute: (data: T) => Indicator }) {
  return <IndicatorView label={label} resource={useResource(load, [])} compute={compute} />
}

function IndicatorView<T>({ label, resource, compute }: { label: string, resource: Resource<T>, compute: (data: T) => Indicator }) {
  const value = resource.data === undefined ? null : compute(resource.data)
  const detail = resource.status === 'error'
    ? (resource.error.status === 403 ? 'sem permissão para este perfil' : 'não foi possível carregar')
    : value?.detail ?? 'carregando…'
  return <div className="indicator">
    <span>{label}</span>
    <strong>{resource.status === 'error' || !value ? '—' : value.value}</strong>
    <small>{detail}</small>
  </div>
}

export default function Overview({ params }: { params: URLSearchParams }) {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [trace, setTrace] = useState<{ status: 'idle' | 'loading' | 'success' | 'error', data?: OperationTrace, error?: ApiError }>({ status: 'idle' })
  const failures = useResource(a => a.listFailures(), [])
  const focus = params.get('focus')

  // Destino do link "Falhas" da barra de eventos.
  useEffect(() => {
    if (focus !== FAILURES_CARD) return
    const card = document.getElementById(FAILURES_CARD)
    card?.scrollIntoView({ block: 'start' })
    card?.focus()
  }, [focus])

  async function lookup(correlationId: string) {
    setTrace({ status: 'loading' })
    try { setTrace({ status: 'success', data: (await api.operationTrace(correlationId)).data }) }
    catch (error) { setTrace({ status: 'error', error: asApiError(error) }) }
  }

  return <>
    <PageIntro>Acompanhe os três fluxos integrados com dados sintéticos. Nenhum dado vem de sistemas reais da Localiza.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <Card title="Situação da demonstração">
      <div className="indicators">
        <IndicatorTile label="Contratos ativos" load={a => a.listContracts()} compute={contractIndicator} />
        <IndicatorTile label="Faturas em aberto" load={a => a.listInvoices()} compute={invoiceIndicator} />
        <IndicatorTile label="Chamados no prazo" load={a => a.listTickets()} compute={ticketIndicator} />
        <IndicatorTile label="Processos em andamento" load={a => a.listProcesses()} compute={processIndicator} />
        <IndicatorView label="Falhas de integração" resource={failures} compute={failureIndicator} />
      </div>
    </Card>

    <div className="grid three">
      {FLOWS.map(flow => <Card key={flow.title} title={flow.title}>
        <ol className="flow-steps">{flow.steps.map(([label, route]) => <li key={label}>
          <span>{label}</span>
          {route
            ? <a href={`#${route}`} onClick={e => { e.preventDefault(); navigate(route) }}>{DESTINATIONS[route]} →</a>
            : <small>Na barra de eventos, no topo da tela</small>}
        </li>)}</ol>
      </Card>)}
    </div>

    <div className="grid two">
      <Card title="Trilha por correlação">
        <p>Veja a auditoria e os eventos de uma operação a partir do ID de correlação exibido nos avisos.</p>
        <form className="filters" aria-label="Consultar trilha por correlação" onSubmit={e => { e.preventDefault(); void lookup(text(new FormData(e.currentTarget), 'correlationId')) }}>
          <Field name="correlationId" label="ID de correlação" defaultValue={params.get('trace') ?? ''} placeholder="00000000-0000-0000-0000-000000000000" />
          <button type="submit" className="secondary" disabled={trace.status === 'loading'}>Consultar</button>
        </form>
        <div aria-live="polite">
          {trace.status === 'loading' && <p className="loading" role="status"><span className="spinner" aria-hidden="true" />Consultando trilha…</p>}
          {trace.status === 'error' && trace.error && <ErrorPanel error={trace.error} context="Falha ao consultar a trilha." />}
          {trace.status === 'success' && trace.data && (trace.data.audit.length + trace.data.events.length === 0
            ? <p className="empty">Nenhuma auditoria ou evento com esta correlação.</p>
            : <>
              {trace.data.audit.length > 0 && <Table caption="Auditoria da correlação" rows={trace.data.audit} rowKey={a => `${a.occurredAt}-${a.operation}`} columns={[
                { key: 'when', label: 'Quando', render: a => dateTime(a.occurredAt) },
                { key: 'module', label: 'Módulo', render: a => a.module },
                { key: 'op', label: 'Operação', render: a => a.operation },
                { key: 'result', label: 'Resultado', render: a => a.result },
              ]} />}
              {trace.data.events.length > 0 && <Table caption="Eventos da correlação" rows={trace.data.events} rowKey={e => e.eventId} columns={[
                { key: 'type', label: 'Evento', render: e => e.eventType },
                { key: 'status', label: 'Estado', render: e => <Status value={e.status} /> },
                { key: 'attempts', label: 'Tentativas', render: e => String(e.attempts) },
              ]} />}
            </>)}
        </div>
      </Card>

      <Card title="Falhas de integração" id={FAILURES_CARD}>
        {failures.status === 'error' && failures.error.status === 403
          ? <p className="empty">As falhas de integração ficam visíveis para os perfis operations e admin.</p>
          : <ResourceView resource={failures} label="falhas"
          empty={<><strong>Nenhuma falha permanente.</strong> Eventos que esgotarem as tentativas de entrega aparecem aqui para reprocessamento.</>}>
          {rows => <Table caption="Falhas de integração" rows={rows} rowKey={r => r.eventId} columns={[
            { key: 'event', label: 'Evento', render: r => <>{r.eventType} <Id value={r.eventId} /></> },
            { key: 'attempts', label: 'Tentativas', render: r => String(r.attempts) },
            { key: 'reason', label: 'Motivo', render: r => r.reason ?? '—' },
            { key: 'corr', label: 'Correlação', render: r => <Id value={r.correlationId} /> },
            { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline" disabled={busy}
              onClick={() => void run('Reprocessamento agendado', () => api.reprocessFailure(r.eventId)).then(x => { if (x) void failures.reload() })}>Reprocessar</button> },
          ]} />}
        </ResourceView>}
      </Card>
    </div>
  </>
}
