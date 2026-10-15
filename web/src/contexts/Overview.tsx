import { useReducer, useState } from 'react'
import { asApiError, type ApiError, type OperationTrace } from '../api'
import {
  Card, ErrorPanel, Field, FeedbackBanner, Id, PageIntro, ResourceView, Status, Table, dateTime, text, useActions, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const FLOWS: { title: string, steps: [string, string][] }[] = [
  { title: 'F1 · Contrato sem recadastro', steps: [['Cadastre um cliente fictício', '/crm'], ['Registre a reserva com o cliente do CRM', '/reservas'], ['Gere o rascunho a partir da reserva', '/reservas']] },
  { title: 'F2 · Ativação, cobrança e retirada', steps: [['Ative o contrato em rascunho', '/reservas'], ['Despache os eventos (abaixo)', '/'], ['Confira a fatura e registre o pagamento', '/financeiro'], ['Confira a preparação de retirada', '/workflow']] },
  { title: 'F3 · Atendimento com SLA', steps: [['Consulte elegibilidade e abra o chamado', '/atendimento'], ['Despache os eventos', '/'], ['Atribua e resolva o chamado', '/atendimento'], ['Despache e confira o processo concluído', '/workflow']] },
]

export default function Overview({ params }: { params: URLSearchParams }) {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [trace, setTrace] = useState<{ status: 'idle' | 'loading' | 'success' | 'error', data?: OperationTrace, error?: ApiError }>({ status: 'idle' })

  const state = useResource(a => a.demoState(), [version])
  const failures = useResource(a => a.listFailures(), [version])

  async function lookup(correlationId: string) {
    setTrace({ status: 'loading' })
    try { setTrace({ status: 'success', data: (await api.operationTrace(correlationId)).data }) }
    catch (error) { setTrace({ status: 'error', error: asApiError(error) }) }
  }

  return <>
    <PageIntro>Protótipo acadêmico com dados sintéticos: CRM, reservas e contratos, financeiro, atendimento e workflow compartilham identificadores e eventos. Pagamentos, frota e atendimentos externos são simulados; não há conexão com sistemas reais da Localiza.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <Card title="Totais do ambiente" roles="admin">
      <ResourceView resource={state} label="totais" empty="" isEmpty={() => false}>
        {d => <div className="stats">{([['Clientes', d.customers], ['Contratos', d.contracts], ['Faturas', d.invoices], ['Chamados', d.tickets], ['Processos', d.processes], ['IDs legados', d.legacyMappings]] as const)
          .map(([label, count]) => <div className="stat" key={label}><span>{label}</span><strong>{count}</strong></div>)}</div>}
      </ResourceView>
    </Card>

    <div className="grid three">
      {FLOWS.map(flow => <Card key={flow.title} title={flow.title}>
        <ol className="steps">{flow.steps.map(([label, route]) => <li key={label}>
          {route === '/' ? label : <a href={`#${route}`} onClick={e => { e.preventDefault(); navigate(route) }}>{label}</a>}
        </li>)}</ol>
      </Card>)}
    </div>

    <div className="grid two">
      <Card title="Integração · outbox" roles="operations, admin">
        <p>O despacho é explícito no protótipo: executa os consumidores internos (Finance, Workflow, projeção de Contracts) e registra falhas após o limite de tentativas.</p>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>
      <Card title="Trilha por correlação" roles="operations, admin">
        <form className="filters" aria-label="Consultar trilha por correlação" onSubmit={e => { e.preventDefault(); void lookup(text(new FormData(e.currentTarget), 'correlationId')) }}>
          <Field name="correlationId" label="Correlation ID (UUID)" defaultValue={params.get('trace') ?? ''} hint="Copie o valor exibido nos avisos de sucesso ou erro." />
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
    </div>

    <Card title="Falhas de integração" roles="operations, admin">
      <ResourceView resource={failures} label="falhas" empty="Nenhuma mensagem com falha permanente.">
        {rows => <Table caption="Falhas de integração" rows={rows} rowKey={r => r.eventId} columns={[
          { key: 'event', label: 'Evento', render: r => <>{r.eventType} <Id value={r.eventId} /></> },
          { key: 'attempts', label: 'Tentativas', render: r => String(r.attempts) },
          { key: 'reason', label: 'Motivo', render: r => r.reason ?? '—' },
          { key: 'corr', label: 'Correlação', render: r => <Id value={r.correlationId} /> },
          { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline" disabled={busy}
            onClick={() => void run('Reprocessamento agendado', () => api.reprocessFailure(r.eventId)).then(x => { if (x) refresh() })}>Reprocessar</button> },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
