import { useEffect } from 'react'
import type { ApiResult, Api } from '../api'
import { FAILURES_CARD } from '../EventsBar'
import {
  contractIndicator, failureIndicator, invoiceIndicator, processIndicator, ticketIndicator, type Indicator,
} from '../indicators'
import {
  Card, FeedbackBanner, Id, PageIntro, ResourceView, Table, useActions, useResource, useSession,
  type Resource,
} from '../ui'

/** Passos de cada fluxo e a tela onde são feitos; sem rota, o passo é feito na barra de eventos. */
const FLOWS: { title: string, steps: [string, string | null][] }[] = [
  { title: 'Do cliente ao contrato', steps: [['Cadastre um cliente fictício', '/crm'], ['Registre a reserva desse cliente', '/reservas'], ['Ative a reserva. O contrato nasce sem novo cadastro', '/reservas']] },
  { title: 'Da ativação à retirada', steps: [['Ative uma reserva', '/reservas'], ['Clique em Atualizar processos', null], ['Confira a fatura e registre o pagamento', '/financeiro'], ['Confira a preparação da retirada', '/workflow']] },
  { title: 'Chamado com prazo', steps: [['Escolha o contrato e abra o chamado', '/atendimento'], ['Clique em Atualizar processos', null], ['Atribua e resolva o chamado', '/atendimento'], ['Atualize os processos e confira a tarefa concluída', '/workflow']] },
]
const DESTINATIONS: Record<string, string> = {
  '/crm': 'CRM', '/reservas': 'Reservas e contratos', '/financeiro': 'Financeiro', '/atendimento': 'Atendimento', '/workflow': 'Operações',
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
  const failures = useResource(a => a.listFailures(), [])
  const focus = params.get('focus')

  // Destino do link "Falhas" da barra de eventos.
  useEffect(() => {
    if (focus !== FAILURES_CARD) return
    const card = document.getElementById(FAILURES_CARD)
    card?.scrollIntoView({ block: 'start' })
    card?.focus()
  }, [focus])

  return <>
    <PageIntro>Aqui você vê como está a operação: contratos, faturas, chamados e processos. Siga os três roteiros abaixo para testar do começo ao fim. Todos os dados são fictícios.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <Card title="Situação atual">
      <div className="indicators">
        <IndicatorTile label="Contratos ativos" load={a => a.contractSummary()} compute={contractIndicator} />
        <IndicatorTile label="Faturas em aberto" load={a => a.invoiceSummary()} compute={invoiceIndicator} />
        <IndicatorTile label="Chamados no prazo" load={a => a.ticketSummary()} compute={ticketIndicator} />
        <IndicatorTile label="Operações em andamento" load={a => a.processSummary()} compute={processIndicator} />
        <IndicatorView label="Falhas de integração" resource={failures} compute={failureIndicator} />
      </div>
    </Card>

    <div className="grid three">
      {FLOWS.map(flow => <Card key={flow.title} title={flow.title}>
        <ol className="flow-steps">{flow.steps.map(([label, route]) => <li key={label}>
          <span>{label}</span>
          {route
            ? <a href={`#${route}`} onClick={e => { e.preventDefault(); navigate(route) }}>{DESTINATIONS[route]} →</a>
            : <small>No botão do topo da tela</small>}
        </li>)}</ol>
      </Card>)}
    </div>

    <Card title="Falhas de integração" id={FAILURES_CARD}>
        {failures.status === 'error' && failures.error.status === 403
          ? <p className="empty">Só os perfis operations e admin veem as falhas.</p>
          : <ResourceView resource={failures} label="falhas"
          empty={<><strong>Nenhuma falha.</strong> Se algum processamento não funcionar depois de várias tentativas, ele aparece aqui para você tentar de novo.</>}>
          {rows => <Table caption="Falhas de integração" rows={rows} rowKey={r => r.eventId} columns={[
            { key: 'event', label: 'Evento', render: r => <>{r.eventType} <Id value={r.eventId} /></> },
            { key: 'attempts', label: 'Tentativas', render: r => String(r.attempts) },
            { key: 'reason', label: 'Motivo', render: r => r.reason ?? '—' },
            { key: 'corr', label: 'Correlação', render: r => <Id value={r.correlationId} /> },
            { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline" disabled={busy}
              onClick={() => void run('Nova tentativa', () => api.reprocessFailure(r.eventId), () => 'Nova tentativa agendada. Clique em Atualizar processos para concluir.').then(x => { if (x) void failures.reload() })}>Reprocessar</button> },
          ]} />}
        </ResourceView>}
    </Card>
  </>
}
