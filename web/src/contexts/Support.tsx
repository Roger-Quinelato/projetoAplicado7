import { useEffect, useReducer, useState } from 'react'
import type { Entitlement, PendingReconciliation, SlaStatus, Ticket } from '../api'
import {
  ActionForm, Card, type Column, CustomerPicker, Field, FeedbackBanner, Id, PageIntro, PendingIntents, ResourceView, SelectField, Status, Table,
  TextArea, dateTime, text, useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const SLA_LABELS: Record<SlaStatus, [string, 'good' | 'bad' | 'warn' | 'neutral']> = {
  PENDING: ['SLA pendente', 'warn'], WITHIN: ['No prazo', 'good'], BREACHED: ['Vencido', 'bad'],
  MET: ['Cumprido', 'good'], NOT_APPLICABLE: ['Sem SLA', 'neutral'],
}
/** Estado de SLA calculado pela API (relógio do servidor), não pelo navegador. */
function SlaBadge({ value }: { value: SlaStatus | null | undefined }) {
  if (!value) return <>—</>
  const [label, tone] = SLA_LABELS[value]
  return <span className={`status ${tone}`} title={value}>{label}</span>
}

/** Atendimento encerrado: resolvido ou recusado por falta de direito; vai para o Histórico. */
const isClosed = (t: Ticket) => t.status === 'RESOLVED' || t.status === 'REJECTED_ENTITLEMENT'
const isAssignable = (t: Ticket) => t.status === 'OPEN' || t.status === 'PENDING_ENTITLEMENT'

type Panel ={ kind: 'assign', ticket: Ticket } | null

const CATEGORIES = [
  { value: 'OUTAGE', label: 'Indisponibilidade ou pane (prioridade alta)' },
  { value: 'SECURITY', label: 'Segurança (prioridade alta)' },
  { value: 'ASSISTANCE', label: 'Assistência 24h' },
  { value: 'QUESTION', label: 'Dúvida' },
]

export default function Support({ params }: { params: URLSearchParams }) {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const preselectedContract = params.get('contract') ?? ''
  const [customerId, setCustomerId] = useState('')
  const [contractId, setContractId] = useState(preselectedContract)
  const [entitlement, setEntitlement] = useState<{ contractId: string, result: Entitlement } | null>(null)
  const [panel, setPanel] = useState<Panel>(null)

  const customers = useResource(a => a.listCustomers({ active: true }), [version])
  // Com cliente escolhido, a consulta é filtrada na API: contratos de clientes fora da primeira página também aparecem.
  const contracts = useResource(a => a.listContracts(customerId || undefined), [version, customerId])
  const tickets = useResource(a => a.listTickets(), [version])
  // O painel guarda o chamado do momento em que abriu; o estado atual vem da lista, que pode ter mudado (ex.: resolvido).
  const assignTicket = panel?.kind === 'assign'
    ? tickets.data?.find(t => t.ticketId === panel.ticket.ticketId) ?? panel.ticket
    : null

  // Contrato vindo da URL: carregado pelo UUID para identificar o cliente, sem depender da listagem.
  useEffect(() => {
    if (!preselectedContract || customerId) return
    let current = true
    api.getContract(preselectedContract).then(r => { if (current) setCustomerId(r.data.customerId) }, () => { /* o seletor segue vazio; a abertura valida o contrato */ })
    return () => { current = false }
  }, [api, preselectedContract, customerId])

  const activeContracts = (contracts.data ?? []).filter(c => c.status === 'ACTIVE' && (!customerId || c.customerId === customerId))
  const selectedContract = contracts.data?.find(c => c.contractId === contractId)
  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  /** Após abrir o chamado, limpa só a descrição; cliente e contrato são controlados pelo estado. */
  function resetDescription(form: HTMLFormElement) {
    const description = form.elements.namedItem('description')
    if (description instanceof HTMLTextAreaElement) description.value = description.defaultValue
  }

  async function reconcilePending() {
    const result = await run<PendingReconciliation>('Atualização dos chamados pendentes', () => api.reconcilePendingTickets(),
      r => r.contractsAvailable
        ? `Chamados atualizados: ${r.confirmed} confirmados, ${r.rejected} recusados e ${r.remaining} ainda pendentes.`
        : `Chamados atualizados: ${r.confirmed} confirmados e ${r.remaining} ainda pendentes. O sistema de contratos ficou fora do ar. Tente de novo mais tarde.`)
    if (result) refresh()
  }

  async function checkEntitlement() {
    if (!selectedContract) return
    const result = await run('Consulta de elegibilidade', () => api.entitlement(selectedContract.contractId, selectedContract.customerId, selectedContract.serviceCode),
      e => e.eligible ? `Este contrato tem direito a atendimento, com SLA de ${e.slaHours} horas.` : 'Este contrato não tem direito a atendimento para este serviço.')
    if (result) setEntitlement({ contractId: selectedContract.contractId, result: result.data })
  }

  const columns: Column<Ticket>[] = [
      { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
      { key: 'id', label: 'Chamado', render: r => <Id value={r.ticketId} /> },
      { key: 'category', label: 'Categoria', render: r => CATEGORIES.find(c => c.value === r.category)?.label.replace(/ \(.*\)$/, '') ?? r.category },
      { key: 'priority', label: 'Prioridade', render: r => <Status value={r.priority} /> },
      { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
      { key: 'due', label: 'Prazo', render: r => dateTime(r.dueAt) },
      { key: 'sla', label: 'Status', render: r => <SlaBadge value={r.slaStatus} /> },
      { key: 'actions', label: 'Ações', render: r => <div className="row-actions">
        {isAssignable(r) && <button type="button" className="inline quiet" disabled={busy} onClick={() => { setPanel({ kind: 'assign', ticket: r }); clear() }}>{r.owner ? 'Reatribuir…' : 'Atribuir…'}</button>}
        {r.status === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => void run('Resolução do chamado', () => keys.send(`resolve:${r.ticketId}`, null, key => api.resolveTicket(r.ticketId, key), 'Resolução do chamado'),
          t => t.slaStatus === 'BREACHED' ? 'Chamado resolvido, mas depois do prazo do SLA.' : 'Chamado resolvido dentro do prazo do SLA.').then(x => { if (x) refresh() })}>Resolver</button>}
        {r.status === 'PENDING_ENTITLEMENT' && <button type="button" className="inline" disabled={busy} onClick={() => void run('Atualização do chamado', () => keys.send(`reconcile:${r.ticketId}`, null, key => api.reconcileTicket(r.ticketId, key), 'Atualização do chamado'),
          t => t.status === 'OPEN' ? 'Chamado confirmado e aberto.' : 'Ainda não foi possível confirmar o contrato deste chamado.').then(x => { if (x) refresh() })}>Atualizar</button>}
      </div> },
    ]

  // No Histórico não há ações; a coluna de prazo dá lugar à data em que o chamado foi resolvido.
  const closedColumns: Column<Ticket>[] = columns.filter(c => c.key !== 'actions')
    .map(c => c.key === 'due' ? { key: 'resolved', label: 'Conclusão', render: r => dateTime(r.resolvedAt) } : c)

  return <>
    <PageIntro>Aqui você abre chamados de clientes com contrato ativo e acompanha o prazo de atendimento, o SLA. Escolha o cliente e o contrato, descreva o problema e abra o chamado. Depois atribua um responsável e resolva.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    <PendingIntents keys={keys} busy={busy} run={run} onCheck={refresh} />

    <div className="grid two">
      <Card title="Abrir chamado">
        <ActionForm submit="Abrir chamado" busy={busy} label="Abrir chamado" reset={resetDescription} onSubmit={async f => {
          const contract = contracts.data?.find(c => c.contractId === contractId)
          const body = {
            customerId: contract?.customerId ?? customerId, contractId,
            serviceCode: contract?.serviceCode ?? 'RENTAL-FLEX', category: text(f, 'category'), description: text(f, 'description'),
          }
          const result = await run('Abertura do chamado', () => keys.send('ticket', body, key => api.openTicket(body, key), 'Abertura do chamado'), t => t.status === 'OPEN'
            ? `Chamado aberto para o contrato ${t.contractId.slice(0, 8)}. Prioridade ${t.priority === 'HIGH' ? 'alta' : 'normal'}. O prazo é ${dateTime(t.dueAt)}.`
            : `Chamado aberto para o contrato ${t.contractId.slice(0, 8)}, mas ainda falta confirmar o direito a atendimento. Clique em Atualizar chamados pendentes mais tarde.`)
          if (result) refresh()
          return result !== null
        }}>
          <CustomerPicker label="Cliente" tools={false} value={customerId} onChange={v => { setCustomerId(v); setContractId(''); setEntitlement(null) }} />
          <SelectField name="contractId" label="Contrato ativo" value={contractId} onChange={v => { setContractId(v); setEntitlement(null) }}
            options={activeContracts.map(c => ({ value: c.contractId, label: `Contrato ${c.contractId.slice(0, 8)} · SLA ${c.slaHours} h` }))}
            placeholder={activeContracts.length ? 'Selecione' : 'Nenhum contrato ativo para este cliente'}
            hint="Só aparecem contratos ativos. Para ativar um, vá em Reservas e contratos." />
          {selectedContract && <p className="meta" role="status">Contrato <Id value={selectedContract.contractId} /> de {customerName(selectedContract.customerId)}</p>}
          <SelectField name="category" label="Categoria" options={CATEGORIES} defaultValue="OUTAGE" />
          <TextArea name="description" label="Descrição (sem dados pessoais ou sensíveis)" defaultValue="Veículo não liga no pátio de retirada (cenário fictício)." />
        </ActionForm>
        <div className="divider" />
        <div className="inline-check">
          <button type="button" className="secondary" disabled={busy || !selectedContract} onClick={() => void checkEntitlement()}>Ver direito a atendimento e SLA</button>
          {entitlement && entitlement.contractId === contractId && <p role="status">
            {entitlement.result.eligible ? <><Status value="ACTIVE" /> Tem direito a atendimento, com SLA de {entitlement.result.slaHours} h</> : <><Status value="REJECTED_ENTITLEMENT" /> Sem direito a atendimento</>}
          </p>}
        </div>
      </Card>

      {panel?.kind === 'assign' ? <Card title={`Atribuir chamado ${panel.ticket.ticketId.slice(0, 8)}`}>
        {assignTicket && !isAssignable(assignTicket) ? <p role="status">
          Este chamado está {assignTicket.status === 'RESOLVED' ? 'resolvido' : 'encerrado'} e não aceita atribuição ou reatribuição.
        </p> : <ActionForm key={panel.ticket.ticketId} submit={assignTicket?.owner ? 'Reatribuir' : 'Atribuir'} busy={busy} label="Atribuir chamado" onSubmit={async f => {
          const result = await run('Atribuição do chamado', () => api.assignTicket(panel.ticket.ticketId, text(f, 'owner')), () => 'Responsável definido.')
          if (result) setPanel(null)
          // Falha (ex.: conflito por mudança de estado): recarrega a lista para o painel refletir o estado atual.
          refresh()
          return result !== null
        }}>
          <Field name="owner" label="Responsável" defaultValue={assignTicket?.owner ?? 'Equipe de assistência 24h'}
            hint="Informe uma equipe ou função, sem e-mail ou telefone. Cada mudança fica no histórico do chamado." />
        </ActionForm>}
        <button type="button" className="secondary small spaced" onClick={() => setPanel(null)}>Voltar</button>
      </Card> : <Card title="Atendimento e SLA">
        <ol className="steps">
          <li>Abra o chamado para um contrato ativo. Indisponibilidade e segurança têm prioridade alta. O prazo é a abertura mais o SLA do contrato.</li>
          <li>Clique em Atualizar processos para criar a tarefa de resolução em Operações.</li>
          <li>Atribua um responsável e resolva o chamado. A coluna SLA mostra se está no prazo, vencido ou cumprido.</li>
          <li>Se o chamado ficou pendente porque o contrato não pôde ser confirmado, clique em Atualizar chamados pendentes.</li>
        </ol>
        <div className="row-actions">
          <DispatchButton busy={busy} run={run} onDone={refresh} />
          <button type="button" className="secondary" disabled={busy} onClick={() => void reconcilePending()}>Atualizar chamados pendentes</button>
        </div>
      </Card>}
    </div>

    <Card title="Chamados">
      <ResourceView resource={tickets} label="chamados" empty="Nenhum chamado ainda.">
        {rows => {
          const open = rows.filter(r => !isClosed(r))
          return open.length
            ? <Table caption="Chamados" rows={open} rowKey={r => r.ticketId} columns={columns} />
            : <p>Nenhum chamado em aberto.</p>
        }}
      </ResourceView>
    </Card>

    <Card title="Histórico">
      <ResourceView resource={tickets} label="histórico de chamados" empty="Nenhum atendimento encerrado ainda.">
        {rows => {
          const closed = rows.filter(isClosed)
          return closed.length
            ? <Table caption="Histórico" rows={closed} rowKey={r => r.ticketId} columns={closedColumns} />
            : <p>Nenhum atendimento encerrado ainda.</p>
        }}
      </ResourceView>
    </Card>
  </>
}
