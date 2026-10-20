import { useReducer, useState } from 'react'
import type { ApiResult, BillingCycle, Contract } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, date, isoDate, money,
  text, useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'

const CYCLES = [
  { value: 'ONCE', label: 'Única' }, { value: 'MONTHLY', label: 'Mensal' },
  { value: 'QUARTERLY', label: 'Trimestral' }, { value: 'YEARLY', label: 'Anual' },
]
const GROUPS = [
  { value: 'ECONOMICO', label: 'Econômico' }, { value: 'INTERMEDIARIO', label: 'Intermediário' },
  { value: 'SUV', label: 'SUV' }, { value: 'EXECUTIVO', label: 'Executivo' },
]
const PROTECTIONS = [{ value: 'BASICA', label: 'Básica' }, { value: 'COMPLETA', label: 'Completa' }]

export default function Contracts({ params }: { params: URLSearchParams }) {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [closing, setClosing] = useState<Contract | null>(null)
  const preselected = params.get('customer') ?? ''

  const customers = useResource(a => a.listCustomers({ active: true }), [version])
  const reservations = useResource(a => a.listReservations(), [version])
  const contracts = useResource(a => a.listContracts(), [version])

  const customerOptions = (customers.data ?? []).map(c => ({ value: c.customerId, label: `${c.name} · ${c.email}` }))
  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  /** Executa um comando idempotente; a chave só é reaproveitada se o corpo da nova tentativa for idêntico. */
  async function idempotent<T, B>(intent: string, label: string, body: B, call: (body: B, key: string) => Promise<ApiResult<T>>, describe?: (data: T) => string) {
    const result = await run(label, () => keys.send(intent, body, key => call(body, key)), describe)
    if (result) refresh()
    return result !== null
  }

  return <>
    <PageIntro>Reserva, contrato de locação, vigência, proteções e SLA pertencem a Contracts. O rascunho nasce da reserva usando o cliente oficial do CRM, sem recadastro. Ativar publica <code>ContractActivated.v1</code> para faturamento e preparação de retirada.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Nova reserva" roles="commercial, contracts, admin">
        <ActionForm key={preselected} submit="Registrar reserva" busy={busy} label="Nova reserva" onSubmit={f => idempotent('reservation', 'Registro de reserva', {
            customerId: text(f, 'customerId'), vehicleGroup: text(f, 'vehicleGroup'), protectionCode: text(f, 'protectionCode'),
            serviceCode: text(f, 'serviceCode'), startsOn: text(f, 'startsOn'), endsOn: text(f, 'endsOn'),
            amount: Number(text(f, 'amount')), currency: 'BRL', billingCycle: text(f, 'billingCycle') as BillingCycle,
            slaHours: Number(text(f, 'slaHours')),
          }, api.createReservation, r => `Reserva ${r.reservationId.slice(0, 8)} solicitada; gere o rascunho na tabela abaixo.`)}>
          <SelectField name="customerId" label="Cliente (CRM)" options={customerOptions} defaultValue={preselected}
            placeholder={customers.status === 'loading' ? 'Carregando…' : customerOptions.length ? 'Selecione' : 'Nenhum cliente ativo'} />
          <div className="form-grid">
            <SelectField name="vehicleGroup" label="Grupo de veículo" options={GROUPS} defaultValue="ECONOMICO" />
            <SelectField name="protectionCode" label="Proteção" options={PROTECTIONS} defaultValue="BASICA" />
          </div>
          <div className="form-grid">
            <Field name="startsOn" label="Início" type="date" defaultValue={isoDate(1)} />
            <Field name="endsOn" label="Fim" type="date" defaultValue={isoDate(8)} />
          </div>
          <div className="form-grid">
            <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue="1200.00" />
            <SelectField name="billingCycle" label="Ciclo de cobrança" options={CYCLES} defaultValue="ONCE" />
          </div>
          <div className="form-grid">
            <Field name="serviceCode" label="Código do serviço" defaultValue="RENTAL-FLEX" />
            <Field name="slaHours" label="SLA (horas)" type="number" min="1" step="1" defaultValue="8" />
          </div>
        </ActionForm>
      </Card>

      {closing ? <Card title={`Encerrar contrato ${closing.contractId.slice(0, 8)}`} roles="contracts, admin">
        <p>O encerramento publica <code>ContractClosed.v1</code> e conclui a preparação de retirada em Workflow após o despacho.</p>
        <ActionForm key={closing.contractId} submit="Confirmar encerramento" busy={busy} label="Encerrar contrato" onSubmit={async f => {
          const ok = await idempotent(`close:${closing.contractId}`, 'Encerramento de contrato',
            { endsOn: text(f, 'endsOn') || null, reason: text(f, 'reason') || null }, (body, key) => api.closeContract(closing.contractId, body, key))
          if (ok) setClosing(null)
          return ok
        }}>
          <Field name="endsOn" label="Data de encerramento" type="date" required={false} hint="Vazio: data atual em UTC ou início do contrato, o que for posterior." />
          <Field name="reason" label="Motivo" required={false} defaultValue="Devolução do veículo" />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setClosing(null)}>Voltar</button>
      </Card> : <Card title="Rascunho direto (sem reserva)" roles="commercial, contracts, admin">
        <p>Alternativa do F1 documentada no roteiro: cria o rascunho a partir do cliente do CRM, sem passar pela reserva.</p>
        <ActionForm submit="Criar rascunho" busy={busy} label="Rascunho direto" onSubmit={f => idempotent('draft', 'Criação de rascunho', {
            customerId: text(f, 'customerId'), serviceCode: text(f, 'serviceCode'), startsOn: text(f, 'startsOn'),
            billing: { amount: Number(text(f, 'amount')), currency: 'BRL', cycle: text(f, 'cycle') as BillingCycle },
            slaHours: Number(text(f, 'slaHours')),
          }, api.createDraft, c => `Contrato ${c.contractId.slice(0, 8)} em rascunho.`)}>
          <SelectField name="customerId" label="Cliente (CRM)" options={customerOptions} />
          <div className="form-grid">
            <Field name="serviceCode" label="Código do serviço" defaultValue="RENTAL-FLEX" />
            <Field name="startsOn" label="Início" type="date" defaultValue={isoDate(1)} />
          </div>
          <div className="form-grid">
            <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue="2500.00" />
            <SelectField name="cycle" label="Ciclo" options={CYCLES} defaultValue="MONTHLY" />
          </div>
          <Field name="slaHours" label="SLA (horas)" type="number" min="1" step="1" defaultValue="8" />
        </ActionForm>
      </Card>}
    </div>

    <Card title="Reservas" roles="commercial, contracts, admin">
      <ResourceView resource={reservations} label="reservas" empty="Nenhuma reserva registrada. Use o formulário acima com um cliente do CRM.">
        {rows => <Table caption="Reservas" rows={rows} rowKey={r => r.reservationId} columns={[
          { key: 'id', label: 'Reserva', render: r => <Id value={r.reservationId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'group', label: 'Grupo / proteção', render: r => `${GROUPS.find(g => g.value === r.vehicleGroup)?.label ?? r.vehicleGroup} · ${PROTECTIONS.find(g => g.value === r.protectionCode)?.label ?? r.protectionCode}` },
          { key: 'period', label: 'Período', render: r => `${date(r.startsOn)} a ${date(r.endsOn)}` },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'actions', label: 'Ações', render: r => <div className="row-actions">
            {r.status === 'REQUESTED' && <button type="button" className="inline" disabled={busy} onClick={() => void idempotent(`draft:${r.reservationId}`, 'Geração de rascunho',
              null, (_body, key) => api.draftFromReservation(r.reservationId, key), d => `Contrato ${d.contract.contractId.slice(0, 8)} em rascunho para o mesmo cliente.`)}>Gerar rascunho</button>}
            {(r.status === 'REQUESTED' || r.status === 'DRAFTED') && <button type="button" className="inline quiet" disabled={busy} onClick={() => {
              if (window.confirm('Cancelar esta reserva? O rascunho vinculado também é cancelado.')) void run('Cancelamento de reserva', () => api.cancelReservation(r.reservationId)).then(x => { if (x) refresh() })
            }}>Cancelar</button>}
            {!['REQUESTED', 'DRAFTED'].includes(r.status) && '—'}
          </div> },
        ]} />}
      </ResourceView>
    </Card>

    <Card title="Contratos" roles="leitura: commercial, contracts, finance, support, admin · ativar/encerrar: contracts, admin">
      <ResourceView resource={contracts} label="contratos" empty="Nenhum contrato. Gere um rascunho a partir de uma reserva.">
        {rows => <Table caption="Contratos" rows={rows} rowKey={r => r.contractId} columns={[
          { key: 'id', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'service', label: 'Serviço', render: r => r.serviceCode },
          { key: 'period', label: 'Vigência', render: r => `${date(r.startsOn)}${r.endsOn ? ` a ${date(r.endsOn)}` : ''}` },
          { key: 'billing', label: 'Cobrança', render: r => `${money(r.billing.amount, r.billing.currency)} · ${CYCLES.find(c => c.value === r.billing.cycle)?.label ?? r.billing.cycle}` },
          { key: 'sla', label: 'SLA', render: r => `${r.slaHours} h` },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'actions', label: 'Ações', render: r => r.status === 'DRAFT'
            ? <button type="button" className="inline" disabled={busy} onClick={() => void idempotent(`activate:${r.contractId}`, 'Ativação de contrato',
              null, (_body, key) => api.activateContract(r.contractId, key), c => `Evento ${c.eventId?.slice(0, 8) ?? ''} na outbox; despache em Visão geral, Financeiro ou Workflow.`)}>Ativar</button>
            : r.status === 'ACTIVE'
              ? <div className="row-actions">
                <button type="button" className="inline quiet" disabled={busy} onClick={() => { setClosing(r); clear() }}>Encerrar…</button>
                <button type="button" className="inline" onClick={() => navigate(`/atendimento?contract=${r.contractId}`)}>Abrir chamado</button>
              </div>
              : '—' },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
