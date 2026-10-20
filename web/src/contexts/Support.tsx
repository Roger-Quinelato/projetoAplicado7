import { useEffect, useReducer, useState } from 'react'
import type { Entitlement, PendingReconciliation, SlaStatus, Ticket, TicketHistoryAction } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, MoreMenu, PageIntro, Panel, ResourceView, SelectField, Stack, Status, Table, TextArea, dateTime, text,
  useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'

const SLA_LABELS: Record<SlaStatus, [string, 'good' | 'bad' | 'warn' | 'neutral']> = {
  PENDING: ['SLA pendente', 'warn'], WITHIN: ['No prazo', 'good'], BREACHED: ['Vencido', 'bad'],
  MET: ['Cumprido', 'good'], NOT_APPLICABLE: ['Sem SLA', 'neutral'],
}
const HISTORY_LABELS: Record<TicketHistoryAction, string> = {
  OPENED: 'Abertura', ASSIGNED: 'Atribuição', REASSIGNED: 'Reatribuição',
  ENTITLEMENT_CONFIRMED: 'Elegibilidade confirmada', ENTITLEMENT_REJECTED: 'Elegibilidade rejeitada', RESOLVED: 'Resolução',
}

/** Estado de SLA calculado pela API (relógio do servidor), não pelo navegador. */
function SlaBadge({ value }: { value: SlaStatus | null | undefined }) {
  if (!value) return <>—</>
  const [label, tone] = SLA_LABELS[value]
  return <span className={`status ${tone}`} title={value}>{label}</span>
}

function TicketHistory({ ticket, version, onClose }: { ticket: Ticket, version: number, onClose: () => void }) {
  const history = useResource(a => a.ticketHistory(ticket.ticketId), [ticket.ticketId, version])
  return <Panel title={`Histórico do chamado ${ticket.ticketId.slice(0, 8)}`} onClose={onClose}>
    <ResourceView resource={history} label="histórico" empty="Chamado sem histórico registrado (anterior à T15).">
      {rows => <Table caption="Histórico do chamado" rows={rows} rowKey={r => `${r.occurredAt}-${r.action}-${r.owner ?? ''}`} columns={[
        { key: 'when', label: 'Quando', render: r => dateTime(r.occurredAt) },
        { key: 'action', label: 'Ação', render: r => HISTORY_LABELS[r.action] ?? r.action },
        { key: 'status', label: 'Estado', render: r => <Status value={r.toStatus} /> },
        { key: 'owner', label: 'Responsável', render: r => r.previousOwner ? `${r.previousOwner} → ${r.owner ?? '—'}` : (r.owner ?? '—') },
        { key: 'sla', label: 'SLA', render: r => <SlaBadge value={r.slaStatus} /> },
        { key: 'correlation', label: 'Correlação', render: r => <Id value={r.correlationId} /> },
      ]} />}
    </ResourceView>
  </Panel>
}

type PanelState = { kind: 'open' } | { kind: 'assign', ticket: Ticket } | { kind: 'history', ticket: Ticket } | null

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
  const [contractError, setContractError] = useState('')
  const [entitlement, setEntitlement] = useState<{ contractId: string, result: Entitlement } | null>(null)
  // Vindo de Contratos com o contrato escolhido, o painel de abertura já abre.
  const [panel, setPanel] = useState<PanelState>(preselectedContract ? { kind: 'open' } : null)

  const customers = useResource(a => a.listCustomers({ active: true }), [version])
  const contracts = useResource(a => a.listContracts(), [version])
  const tickets = useResource(a => a.listTickets(), [version])

  useEffect(() => {
    if (!preselectedContract || customerId) return
    const contract = contracts.data?.find(c => c.contractId === preselectedContract)
    if (contract) setCustomerId(contract.customerId)
  }, [contracts.data, preselectedContract, customerId])

  const activeContracts = (contracts.data ?? []).filter(c => c.status === 'ACTIVE' && (!customerId || c.customerId === customerId))
  const selectedContract = contracts.data?.find(c => c.contractId === contractId)
  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  /** Após abrir o chamado, limpa só a descrição; cliente e contrato são controlados pelo estado. */
  function resetDescription(form: HTMLFormElement) {
    const description = form.elements.namedItem('description')
    if (description instanceof HTMLTextAreaElement) description.value = description.defaultValue
  }

  async function reconcilePending() {
    const result = await run<PendingReconciliation>('Reconciliação dos chamados pendentes', () => api.reconcilePendingTickets(), undefined, {
      success: r => `Reconciliação concluída: ${r.confirmed} confirmado(s), ${r.rejected} rejeitado(s), ${r.remaining} ainda pendente(s)${r.contractsAvailable ? '' : '. Contracts caiu durante o lote; repita depois'}.`,
      failure: 'Não foi possível reconciliar os chamados pendentes.',
    })
    if (result) refresh()
  }

  async function checkEntitlement() {
    if (!selectedContract) { setContractError('Escolha um contrato ativo para consultar a elegibilidade e o SLA.'); return }
    const result = await run('Consulta de elegibilidade', () => api.entitlement(selectedContract.contractId, selectedContract.customerId, selectedContract.serviceCode), undefined, {
      success: e => e.eligible ? `Contrato elegível, com SLA de ${e.slaHours} h.` : 'Contrato sem elegibilidade para este serviço.',
      failure: 'Não foi possível consultar a elegibilidade.',
    })
    if (result) setEntitlement({ contractId: selectedContract.contractId, result: result.data })
  }

  function resolve(t: Ticket) {
    void run('Resolução de chamado', () => api.resolveTicket(t.ticketId), undefined, {
      success: r => `Chamado ${r.ticketId.slice(0, 8)} resolvido${r.slaStatus === 'BREACHED' ? ' depois do prazo do SLA' : r.slaStatus === 'MET' ? ' dentro do SLA' : ''}. Despache os eventos para concluir o processo.`,
      failure: 'Não foi possível resolver o chamado.',
    }).then(x => { if (x) refresh() })
  }

  function reconcile(t: Ticket) {
    void run('Reconciliação de elegibilidade', () => api.reconcileTicket(t.ticketId), undefined, {
      success: r => r.status === 'OPEN' ? `Chamado ${r.ticketId.slice(0, 8)} confirmado e aberto.` : `Chamado ${r.ticketId.slice(0, 8)} sem elegibilidade.`,
      failure: 'Não foi possível reconciliar o chamado.',
    }).then(x => { if (x) refresh() })
  }

  return <>
    <PageIntro>Abra chamados para contratos ativos. O prazo do SLA vem do contrato, e o despacho do evento <code>TicketOpened.v1</code> inicia o processo de resolução em Workflow.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <Card title="Chamados" aside={<div className="head-actions">
      <button type="button" className="secondary" disabled={busy} onClick={() => void reconcilePending()}>Reconciliar pendentes</button>
      <button type="button" onClick={() => { setPanel({ kind: 'open' }); clear() }}>Abrir chamado</button>
    </div>}>
      <ResourceView resource={tickets} label="chamados" empty="Nenhum chamado aberto ainda. Use “Abrir chamado” com um contrato ativo.">
        {rows => <Table caption="Chamados" rows={rows} rowKey={r => r.ticketId} columns={[
          { key: 'id', label: 'Chamado', render: r => <Stack main={<Id value={r.ticketId} />} sub={<>Contrato <Id value={r.contractId} /></>} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'category', label: 'Categoria', render: r => CATEGORIES.find(c => c.value === r.category)?.label.replace(/ \(.*\)$/, '') ?? r.category },
          { key: 'priority', label: 'Prioridade', render: r => <Status value={r.priority} /> },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'sla', label: 'SLA', render: r => <Stack main={<SlaBadge value={r.slaStatus} />} sub={r.dueAt ? `até ${dateTime(r.dueAt)}` : undefined} /> },
          { key: 'owner', label: 'Responsável', render: r => r.owner ?? <span className="muted">Ninguém</span> },
          { key: 'actions', label: 'Ações', render: r => {
            const more = [
              ...(r.status === 'OPEN' || r.status === 'PENDING_ENTITLEMENT' ? [{ label: r.owner ? 'Reatribuir…' : 'Atribuir…', disabled: busy, onSelect: () => { setPanel({ kind: 'assign', ticket: r }); clear() } }] : []),
              { label: 'Histórico', onSelect: () => { setPanel({ kind: 'history', ticket: r }); clear() } },
            ]
            return <div className="row-actions">
              {r.status === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => resolve(r)}>Resolver</button>}
              {r.status === 'PENDING_ENTITLEMENT' && <button type="button" className="inline" disabled={busy} onClick={() => reconcile(r)}>Reconciliar</button>}
              <MoreMenu label={`chamado ${r.ticketId.slice(0, 8)}`} items={more} />
            </div>
          } },
        ]} />}
      </ResourceView>
    </Card>

    {panel && <div className="grid two">
      {panel.kind === 'open' && <Panel title="Abrir chamado" onClose={() => setPanel(null)}>
        <ActionForm submit="Abrir chamado" busy={busy} label="Abrir chamado" reset={resetDescription} onSubmit={async f => {
          const contract = contracts.data?.find(c => c.contractId === contractId)
          const body = {
            customerId: contract?.customerId ?? customerId, contractId,
            serviceCode: contract?.serviceCode ?? 'RENTAL-FLEX', category: text(f, 'category'), description: text(f, 'description'),
          }
          const result = await run('Abertura de chamado', () => keys.send('ticket', body, key => api.openTicket(body, key)), undefined, {
            success: t => t.status === 'OPEN'
              ? `Chamado ${t.ticketId.slice(0, 8)} aberto com prioridade ${t.priority === 'HIGH' ? 'alta' : 'normal'}. Prazo do SLA: ${dateTime(t.dueAt)}.`
              : `Chamado ${t.ticketId.slice(0, 8)} aberto com elegibilidade pendente. Reconcilie quando Contracts voltar.`,
            failure: 'Não foi possível abrir o chamado.',
          })
          if (result) refresh()
          return result !== null
        }}>
          <div className="form-grid">
            <SelectField name="customerId" label="Cliente" value={customerId} onChange={v => { setCustomerId(v); setContractId(''); setEntitlement(null) }}
              options={(customers.data ?? []).map(c => ({ value: c.customerId, label: `${c.name} · ${c.email}` }))}
              placeholder={customers.status === 'loading' ? 'Carregando…' : 'Selecione'} />
            <SelectField name="contractId" label="Contrato ativo" value={contractId} onChange={v => { setContractId(v); setContractError(''); setEntitlement(null) }}
              options={activeContracts.map(c => ({ value: c.contractId, label: `${c.contractId.slice(0, 8)} · ${c.serviceCode} · SLA ${c.slaHours} h` }))}
              placeholder={activeContracts.length ? 'Selecione' : 'Nenhum contrato ativo para este cliente'}
              hint="Apenas contratos ativos aparecem; ative um rascunho em Reservas e contratos." error={contractError} />
          </div>
          <div className="inline-check">
            <button type="button" className="secondary" disabled={busy} onClick={() => void checkEntitlement()}>Consultar elegibilidade e SLA</button>
            {entitlement && entitlement.contractId === contractId
              ? <p role="status">{entitlement.result.eligible ? <><Status value="ACTIVE" /> Elegível · SLA {entitlement.result.slaHours} h</> : <><Status value="REJECTED_ENTITLEMENT" /> Sem elegibilidade</>}</p>
              : <p className="muted">Elegibilidade e SLA ainda não consultados.</p>}
          </div>
          <SelectField name="category" label="Categoria" options={CATEGORIES} defaultValue="OUTAGE" />
          <TextArea name="description" label="Descrição (sem dados pessoais ou sensíveis)" defaultValue="Veículo não liga no pátio de retirada (cenário fictício)." />
        </ActionForm>
      </Panel>}

      {panel.kind === 'assign' && <Panel title={`${panel.ticket.owner ? 'Reatribuir' : 'Atribuir'} chamado ${panel.ticket.ticketId.slice(0, 8)}`} onClose={() => setPanel(null)}>
        <ActionForm key={panel.ticket.ticketId} submit={panel.ticket.owner ? 'Reatribuir' : 'Atribuir'} busy={busy} label="Atribuir chamado" onSubmit={async f => {
          const owner = text(f, 'owner')
          const result = await run('Atribuição de chamado', () => api.assignTicket(panel.ticket.ticketId, owner), undefined,
            { success: t => `Chamado ${t.ticketId.slice(0, 8)} atribuído a ${owner}.`, failure: 'Não foi possível atribuir o chamado.' })
          if (result) { setPanel(null); refresh() }
          return result !== null
        }}>
          <Field name="owner" label="Responsável" defaultValue={panel.ticket.owner ?? 'Equipe de assistência 24h'}
            hint="Equipe ou função, sem e-mail ou telefone. Cada atribuição e reatribuição fica no histórico do chamado." />
        </ActionForm>
      </Panel>}

      {panel.kind === 'history' && <TicketHistory ticket={panel.ticket} version={version} onClose={() => setPanel(null)} />}

      <Card title="Como funciona o SLA">
        <ol className="flow-steps">
          <li><span>O prazo é a abertura mais o SLA do contrato. Indisponibilidade e segurança têm prioridade alta.</span></li>
          <li><span>Despachar os eventos na barra do topo cria o processo de resolução em Workflow.</span></li>
          <li><span>Ao resolver e despachar de novo, o processo é concluído.</span></li>
          <li><span>Se Contracts estiver fora do ar, o chamado fica com elegibilidade pendente. Use “Reconciliar pendentes” quando ele voltar.</span></li>
        </ol>
      </Card>
    </div>}
  </>
}
