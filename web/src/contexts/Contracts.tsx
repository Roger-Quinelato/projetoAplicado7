import { useReducer, useState } from 'react'
import type { ApiResult, BillingCycle, Contract, Reservation, ReservationUpdate } from '../api'
import {
  ActionForm, Card, CustomerPicker, Field, FeedbackBanner, Id, PageIntro, PendingIntents, ResourceView, SelectField, Status, Table, date,
  isoDate, money, text, useActions, useIdempotencyKeys, useResource, useSession,
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

// A tela trata só a reserva: "com rascunho" é um passo interno da ativação e aparece como solicitada.
const RESERVATION_STATE: Record<string, [string, 'good' | 'bad' | 'warn' | 'neutral']> = {
  REQUESTED: ['Solicitada', 'warn'], DRAFTED: ['Solicitada', 'warn'],
  ACTIVE: ['Ativa', 'good'], CLOSED: ['Encerrada', 'neutral'], CANCELLED: ['Cancelada', 'bad'],
}
function ReservationState({ value }: { value: string }) {
  const [label, tone] = RESERVATION_STATE[value] ?? [value, 'neutral']
  return <span className={`status ${tone}`} title={value}>{label}</span>
}
const isOpen = (r: Reservation) => r.status === 'REQUESTED' || r.status === 'DRAFTED'

/** Mantém na lista o valor atual da reserva mesmo quando ele não é uma das opções padrão. */
const withCurrent = (options: { value: string, label: string }[], current?: string) =>
  current && !options.some(o => o.value === current) ? [...options, { value: current, label: current }] : options

/** Campos compartilhados pelo registro e pela edição da reserva. */
function ReservationFields({ initial }: { initial?: Reservation }) {
  return <>
    <div className="form-grid">
      <SelectField name="vehicleGroup" label="Grupo de veículo" options={withCurrent(GROUPS, initial?.vehicleGroup)} defaultValue={initial?.vehicleGroup ?? 'ECONOMICO'} />
      <SelectField name="protectionCode" label="Proteção" options={withCurrent(PROTECTIONS, initial?.protectionCode)} defaultValue={initial?.protectionCode ?? 'BASICA'} />
    </div>
    <div className="form-grid">
      <Field name="startsOn" label="Início" type="date" defaultValue={initial?.startsOn ?? isoDate(1)} />
      <Field name="endsOn" label="Fim" type="date" defaultValue={initial?.endsOn ?? isoDate(8)} />
    </div>
    <div className="form-grid">
      <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue={initial ? initial.amount.toFixed(2) : '1200.00'} />
      <SelectField name="billingCycle" label="Ciclo de cobrança" options={CYCLES} defaultValue={initial?.billingCycle ?? 'ONCE'} />
    </div>
    <div className="form-grid">
      <Field name="serviceCode" label="Código do serviço" defaultValue={initial?.serviceCode ?? 'RENTAL-FLEX'} />
      <Field name="slaHours" label="SLA (horas)" type="number" min="1" step="1" defaultValue={String(initial?.slaHours ?? 8)} />
    </div>
  </>
}

function reservationBody(f: FormData): ReservationUpdate {
  return {
    vehicleGroup: text(f, 'vehicleGroup'), protectionCode: text(f, 'protectionCode'), serviceCode: text(f, 'serviceCode'),
    startsOn: text(f, 'startsOn'), endsOn: text(f, 'endsOn'), amount: Number(text(f, 'amount')), currency: 'BRL',
    billingCycle: text(f, 'billingCycle') as BillingCycle, slaHours: Number(text(f, 'slaHours')),
  }
}

export default function Contracts({ params }: { params: URLSearchParams }) {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [closing, setClosing] = useState<Contract | null>(null)
  const [editing, setEditing] = useState<Reservation | null>(null)
  const preselected = params.get('customer') ?? ''

  const customers = useResource(a => a.listCustomers({ active: true }), [version])
  const reservations = useResource(a => a.listReservations(), [version])
  const contracts = useResource(a => a.listContracts(), [version])

  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  /** Executa um comando idempotente; a chave só é reaproveitada se o corpo da nova tentativa for idêntico. */
  async function idempotent<T, B>(intent: string, label: string, body: B, call: (body: B, key: string) => Promise<ApiResult<T>>, describe?: (data: T) => string) {
    const result = await run(label, () => keys.send(intent, body, key => call(body, key), label), describe)
    if (result) refresh()
    return result !== null
  }

  /** Ativar a reserva gera o contrato e o ativa; se o segundo passo falhar, repetir Ativar continua de onde parou. */
  async function activateReservation(r: Reservation) {
    const label = 'Ativação da reserva'
    const done = await run(label, async () => {
      const draft = await keys.send(`draft:${r.reservationId}`, null, key => api.draftFromReservation(r.reservationId, key), label)
      const contractId = draft.data.contract.contractId
      return keys.send(`activate:${contractId}`, null, key => api.activateContract(contractId, key), label)
    }, () => 'A cobrança e a preparação da retirada começam depois que os eventos forem despachados.')
    if (done) refresh()
  }

  const editingNow = editing ? reservations.data?.find(r => r.reservationId === editing.reservationId) ?? editing : null

  return <>
    <PageIntro>Aqui você registra a reserva de um veículo para um cliente já cadastrado. Enquanto estiver solicitada, a reserva pode ser editada ou cancelada; ao ativá-la, o contrato passa a valer e a cobrança e a preparação da retirada começam.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    <PendingIntents keys={keys} busy={busy} run={run} onCheck={refresh} />

    <div className="grid two">
      <Card title="Nova reserva" roles="commercial, contracts, admin">
        <ActionForm key={preselected} submit="Registrar reserva" busy={busy} label="Nova reserva" onSubmit={f => idempotent('reservation', 'Registro de reserva',
          { customerId: text(f, 'customerId'), ...reservationBody(f) }, api.createReservation,
          r => `Reserva ${r.reservationId.slice(0, 8)} solicitada. Use Ativar, Editar ou Cancelar na tabela abaixo.`)}>
          <CustomerPicker label="Cliente (CRM)" defaultValue={preselected} />
          <ReservationFields />
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
      </Card> : editingNow ? <Card title={`Editar reserva ${editingNow.reservationId.slice(0, 8)}`} roles="commercial, contracts, admin">
        {editingNow.status !== 'REQUESTED' ? <p role="status">Esta reserva já não está solicitada e não pode mais ser editada.</p> : <>
          <p>Cliente: <strong>{customerName(editingNow.customerId)}</strong>. Para trocar o cliente, cancele esta reserva e registre outra.</p>
          <ActionForm key={editingNow.reservationId} submit="Salvar alterações" busy={busy} label="Editar reserva" onSubmit={async f => {
            const result = await run('Edição da reserva', () => api.updateReservation(editingNow.reservationId, reservationBody(f)), () => 'Dados atualizados.')
            if (result) setEditing(null)
            refresh()
            return result !== null
          }}>
            <ReservationFields initial={editingNow} />
          </ActionForm>
        </>}
        <button type="button" className="secondary small spaced" onClick={() => setEditing(null)}>Voltar</button>
      </Card> : <Card title="Como funciona" roles="commercial, contracts, admin">
        <ol className="steps">
          <li>Registre a reserva do cliente: ela fica <strong>Solicitada</strong>.</li>
          <li>Enquanto estiver solicitada, use <strong>Editar</strong> (por exemplo, se o cliente mudou a data) ou <strong>Cancelar</strong>.</li>
          <li>Use <strong>Ativar</strong> para o contrato passar a valer; a cobrança e a preparação da retirada começam em seguida.</li>
        </ol>
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
          { key: 'status', label: 'Estado', render: r => <ReservationState value={r.status} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'actions', label: 'Ações', render: r => isOpen(r) ? <div className="row-actions">
            <button type="button" className="inline" disabled={busy} onClick={() => void activateReservation(r)}>Ativar</button>
            {r.status === 'REQUESTED' && <button type="button" className="inline quiet" disabled={busy} onClick={() => { setEditing(r); setClosing(null); clear() }}>Editar…</button>}
            <button type="button" className="inline quiet" disabled={busy} onClick={() => {
              if (window.confirm('Cancelar esta reserva?')) void run('Cancelamento de reserva', () => api.cancelReservation(r.reservationId)).then(x => { if (x) refresh() })
            }}>Cancelar</button>
          </div> : '—' },
        ]} />}
      </ResourceView>
    </Card>

    <Card title="Contratos" roles="leitura: commercial, contracts, finance, support, admin · ativar/encerrar: contracts, admin">
      <ResourceView resource={contracts} label="contratos" empty="Nenhum contrato ainda. Ative uma reserva.">
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
                <button type="button" className="inline quiet" disabled={busy} onClick={() => { setClosing(r); setEditing(null); clear() }}>Encerrar…</button>
                <button type="button" className="inline" onClick={() => navigate(`/atendimento?contract=${r.contractId}`)}>Abrir chamado</button>
              </div>
              : '—' },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
