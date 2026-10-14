import { useEffect, useReducer, useState } from 'react'
import type { Entitlement, Ticket } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, TextArea, dateTime, text,
  useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

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
  const [assigning, setAssigning] = useState<Ticket | null>(null)

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

  async function checkEntitlement() {
    if (!selectedContract) return
    const result = await run('Consulta de elegibilidade', () => api.entitlement(selectedContract.contractId, selectedContract.customerId, selectedContract.serviceCode),
      e => e.eligible ? `Elegível, SLA de ${e.slaHours} h.` : 'Sem elegibilidade para este serviço.')
    if (result) setEntitlement({ contractId: selectedContract.contractId, result: result.data })
  }

  return <>
    <PageIntro>Chamado, assistência, prioridade, SLA e resolução pertencem a Support. A abertura consulta elegibilidade e SLA no contrato ativo; o despacho do evento <code>TicketOpened.v1</code> inicia o processo de resolução em Workflow.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Abrir chamado" roles="support, admin">
        <ActionForm key={customerId} submit="Abrir chamado" busy={busy} label="Abrir chamado" onSubmit={async f => {
          const contract = contracts.data?.find(c => c.contractId === text(f, 'contractId'))
          const intent = 'ticket'
          const result = await run('Abertura de chamado', () => api.openTicket({
            customerId: contract?.customerId ?? text(f, 'customerId'), contractId: text(f, 'contractId'),
            serviceCode: contract?.serviceCode ?? 'RENTAL-FLEX', category: text(f, 'category'), description: text(f, 'description'),
          }, keys.keyFor(intent)), t => t.status === 'OPEN'
            ? `Chamado ${t.ticketId.slice(0, 8)} aberto, prioridade ${t.priority === 'HIGH' ? 'alta' : 'normal'}, SLA até ${dateTime(t.dueAt)}.`
            : `Chamado ${t.ticketId.slice(0, 8)} com elegibilidade pendente; reconcilie quando Contracts voltar.`)
          if (result) { keys.done(intent); refresh() }
          return result !== null
        }}>
          <SelectField name="customerId" label="Cliente" defaultValue={customerId} onChange={v => { setCustomerId(v); setContractId(''); setEntitlement(null) }}
            options={(customers.data ?? []).map(c => ({ value: c.customerId, label: `${c.name} · ${c.email}` }))}
            placeholder={customers.status === 'loading' ? 'Carregando…' : 'Selecione'} />
          <SelectField name="contractId" label="Contrato ativo" defaultValue={contractId} onChange={v => { setContractId(v); setEntitlement(null) }}
            options={activeContracts.map(c => ({ value: c.contractId, label: `${c.contractId.slice(0, 8)} · ${c.serviceCode} · SLA ${c.slaHours} h` }))}
            placeholder={activeContracts.length ? 'Selecione' : 'Nenhum contrato ativo para este cliente'}
            hint="Apenas contratos ativos aparecem; ative um rascunho em Reservas e contratos." />
          <SelectField name="category" label="Categoria" options={CATEGORIES} defaultValue="OUTAGE" />
          <TextArea name="description" label="Descrição (sem dados pessoais ou sensíveis)" defaultValue="Veículo não liga no pátio de retirada (cenário fictício)." />
        </ActionForm>
        <div className="divider" />
        <div className="inline-check">
          <button type="button" className="secondary" disabled={busy || !selectedContract} onClick={() => void checkEntitlement()}>Consultar elegibilidade e SLA</button>
          {entitlement && entitlement.contractId === contractId && <p role="status">
            {entitlement.result.eligible ? <><Status value="ACTIVE" /> Elegível · SLA {entitlement.result.slaHours} h</> : <><Status value="REJECTED_ENTITLEMENT" /> Sem elegibilidade</>}
          </p>}
        </div>
      </Card>

      {assigning ? <Card title={`Atribuir chamado ${assigning.ticketId.slice(0, 8)}`} roles="support, admin">
        <ActionForm key={assigning.ticketId} submit="Atribuir" busy={busy} label="Atribuir chamado" onSubmit={async f => {
          const result = await run('Atribuição de chamado', () => api.assignTicket(assigning.ticketId, text(f, 'owner')))
          if (result) { setAssigning(null); refresh() }
          return result !== null
        }}>
          <Field name="owner" label="Responsável" defaultValue={assigning.owner ?? 'Equipe de assistência 24h'} />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setAssigning(null)}>Voltar</button>
      </Card> : <Card title="Atendimento e SLA" roles="despacho: operations, admin">
        <ol className="steps">
          <li>Abra o chamado para um contrato ativo; categorias de indisponibilidade e segurança recebem prioridade alta.</li>
          <li>Despache a outbox para criar o processo de resolução em Workflow.</li>
          <li>Atribua um responsável e resolva; o novo despacho conclui o processo.</li>
        </ol>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>}
    </div>

    <Card title="Chamados" roles="support, operations, admin">
      <ResourceView resource={tickets} label="chamados" empty="Nenhum chamado aberto ainda.">
        {rows => <Table caption="Chamados" rows={rows} rowKey={r => r.ticketId} columns={[
          { key: 'id', label: 'Chamado', render: r => <Id value={r.ticketId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'category', label: 'Categoria', render: r => CATEGORIES.find(c => c.value === r.category)?.label.replace(/ \(.*\)$/, '') ?? r.category },
          { key: 'priority', label: 'Prioridade', render: r => <Status value={r.priority} /> },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'due', label: 'SLA até', render: r => dateTime(r.dueAt) },
          { key: 'owner', label: 'Responsável', render: r => r.owner ?? '—' },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'actions', label: 'Ações', render: r => <div className="row-actions">
            {(r.status === 'OPEN' || r.status === 'PENDING_ENTITLEMENT') && <button type="button" className="inline quiet" disabled={busy} onClick={() => { setAssigning(r); clear() }}>Atribuir…</button>}
            {r.status === 'OPEN' && <button type="button" className="inline" disabled={busy} onClick={() => void run('Resolução de chamado', () => api.resolveTicket(r.ticketId)).then(x => { if (x) refresh() })}>Resolver</button>}
            {r.status === 'PENDING_ENTITLEMENT' && <button type="button" className="inline" disabled={busy} onClick={() => void run('Reconciliação de elegibilidade', () => api.reconcileTicket(r.ticketId)).then(x => { if (x) refresh() })}>Reconciliar</button>}
            {(r.status === 'RESOLVED' || r.status === 'REJECTED_ENTITLEMENT') && '—'}
          </div> },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
