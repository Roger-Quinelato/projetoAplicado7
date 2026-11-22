import { useEffect, useReducer, useState } from 'react'
import type { ApiResult, BillingCycle, Contract, Reservation, ReservationUpdate } from '../api'
import {
  ActionForm, Card, type Column, CustomerPicker, Field, FeedbackBanner, Id, PageIntro, PendingIntents, ResourceView, SelectField, Status, Table, date,
  isoDate, money, revealElement, text, useActions, useIdempotencyKeys, useResource, useSession,
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
      <SelectField name="vehicleGroup" label="Grupo de veículo" options={withCurrent(GROUPS, initial?.vehicleGroup)} defaultValue={initial?.vehicleGroup} />
      <SelectField name="protectionCode" label="Proteção" options={withCurrent(PROTECTIONS, initial?.protectionCode)} defaultValue={initial?.protectionCode} />
    </div>
    <div className="form-grid">
      <Field name="startsOn" label="Início" type="date" defaultValue={initial?.startsOn ?? isoDate(0)} />
      <Field name="endsOn" label="Fim" type="date" defaultValue={initial?.endsOn} />
    </div>
    <div className="form-grid">
      <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" placeholder="Ex.: 1200.00" defaultValue={initial ? initial.amount.toFixed(2) : ''} />
      <SelectField name="billingCycle" label="Ciclo de cobrança" options={CYCLES} defaultValue={initial?.billingCycle} />
    </div>
    <div className="form-grid">
      <Field name="serviceCode" label="Código do serviço" placeholder="Ex.: RENTAL-FLEX" defaultValue={initial?.serviceCode ?? ''} />
      <Field name="slaHours" label="SLA (horas)" type="number" min="1" step="1" placeholder="Ex.: 8" defaultValue={initial ? String(initial.slaHours) : ''} />
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

  // O formulário de encerramento abre no topo; leva a tela até ele e foca o primeiro campo.
  useEffect(() => {
    if (!closing) return
    const card = document.getElementById('encerrar-contrato')
    revealElement(card)
    card?.querySelector<HTMLInputElement>('input')?.focus({ preventScroll: true })
  }, [closing])

  // O mesmo vale para a edição da reserva: o formulário fica no topo e o botão Editar, na tabela.
  const editingId = editing?.reservationId
  useEffect(() => {
    if (!editingId) return
    const card = document.getElementById('editar-reserva')
    revealElement(card)
    card?.querySelector<HTMLElement>('input, select')?.focus({ preventScroll: true })
  }, [editingId])

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
    }, () => 'Reserva ativada. O contrato já vale. Clique em Atualizar processos para criar a fatura e a preparação da retirada.')
    if (done) refresh()
  }

  const editingNow = editing ? reservations.data?.find(r => r.reservationId === editing.reservationId) ?? editing : null

  const contractColumns: Column<Contract>[] = [
          { key: 'id', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'service', label: 'Serviço', render: r => r.serviceCode },
          { key: 'period', label: 'Vigência', render: r => `${date(r.startsOn)}${r.endsOn ? ` a ${date(r.endsOn)}` : ''}` },
          { key: 'billing', label: 'Cobrança', render: r => `${money(r.billing.amount, r.billing.currency)} · ${CYCLES.find(c => c.value === r.billing.cycle)?.label ?? r.billing.cycle}` },
          { key: 'sla', label: 'SLA', render: r => `${r.slaHours} h` },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'actions', label: 'Ações', render: r => r.status === 'DRAFT'
            ? <button type="button" className="inline" disabled={busy} onClick={() => void idempotent(`activate:${r.contractId}`, 'Ativação do contrato',
              null, (_body, key) => api.activateContract(r.contractId, key), () => 'Contrato ativado. Clique em Atualizar processos para criar a fatura e a preparação da retirada.')}>Ativar</button>
            : r.status === 'ACTIVE'
              ? <div className="row-actions">
                <button type="button" className="inline quiet" disabled={busy} onClick={() => { setClosing(r); setEditing(null); clear() }}>Encerrar…</button>
                <button type="button" className="inline" onClick={() => navigate(`/atendimento?contract=${r.contractId}`)}>Abrir chamado</button>
              </div>
              : '—' },
  ]
  const contractTable = (rows: Contract[], caption: string, empty: string, withActions = true) =>
    <ResourceView resource={contracts} label="contratos" isEmpty={() => rows.length === 0} empty={empty}>
      {() => <Table caption={caption} rows={rows} rowKey={r => r.contractId} columns={withActions ? contractColumns : contractColumns.filter(c => c.key !== 'actions')} />}
    </ResourceView>
  // Contratos: só os ativos. Histórico: encerrados e cancelados.
  const active = (contracts.data ?? []).filter(c => c.status === 'ACTIVE')
  const history = (contracts.data ?? []).filter(c => c.status === 'CLOSED' || c.status === 'CANCELLED')

  return <>
    <PageIntro>Aqui você registra a reserva de um veículo para um cliente já cadastrado e acompanha os contratos. Preencha o formulário para registrar a reserva. Depois use Ativar para o contrato valer, Editar para mudar dados ou Cancelar.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    <PendingIntents keys={keys} busy={busy} run={run} onCheck={refresh} />

    <div className="grid two">
      <Card title="Nova reserva">
        <ActionForm key={preselected} submit="Registrar reserva" busy={busy} label="Nova reserva" onSubmit={f => idempotent('reservation', 'Registro de reserva',
          { customerId: text(f, 'customerId'), ...reservationBody(f) }, api.createReservation,
          () => 'Reserva registrada. Use Ativar, Editar ou Cancelar na lista abaixo.')}>
          <CustomerPicker label="Cliente" defaultValue={preselected} tools={false} />
          <ReservationFields />
        </ActionForm>
      </Card>

      {closing ? <Card id="encerrar-contrato" title={`Encerrar contrato ${closing.contractId.slice(0, 8)}`}>
        <p>Informe a data e o motivo do encerramento. Depois clique em Atualizar processos para gerar a fatura final e concluir a preparação da retirada.</p>
        <ActionForm key={closing.contractId} submit="Confirmar encerramento" busy={busy} label="Encerrar contrato" onSubmit={async f => {
          const ok = await idempotent(`close:${closing.contractId}`, 'Encerramento do contrato',
            { endsOn: text(f, 'endsOn') || null, reason: text(f, 'reason') || null }, (body, key) => api.closeContract(closing.contractId, body, key),
            () => 'Contrato encerrado. Clique em Atualizar processos para gerar a fatura final.')
          if (ok) setClosing(null)
          return ok
        }}>
          <Field name="endsOn" label="Data de encerramento" type="date" required={false} hint="Se deixar vazio, usamos hoje ou o início do contrato, o que for mais tarde." />
          <Field name="reason" label="Motivo" required={false} defaultValue="Devolução do veículo" />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setClosing(null)}>Voltar</button>
      </Card> : editingNow ? <Card id="editar-reserva" title={`Editar reserva ${editingNow.reservationId.slice(0, 8)}`}>
        {editingNow.status !== 'REQUESTED' ? <p role="status">Esta reserva já não está solicitada e não pode mais ser editada.</p> : <>
          <p>Cliente: <strong>{customerName(editingNow.customerId)}</strong>. Para trocar o cliente, cancele esta reserva e registre outra.</p>
          <ActionForm key={editingNow.reservationId} submit="Salvar alterações" busy={busy} label="Editar reserva" onSubmit={async f => {
            const result = await run('Edição da reserva', () => api.updateReservation(editingNow.reservationId, reservationBody(f)), () => 'Reserva atualizada.')
            if (result) setEditing(null)
            refresh()
            return result !== null
          }}>
            <ReservationFields initial={editingNow} />
          </ActionForm>
        </>}
        <button type="button" className="secondary small spaced" onClick={() => setEditing(null)}>Voltar</button>
      </Card> : <Card title="Como funciona">
        <ol className="steps">
          <li>Registre a reserva do cliente. Ela fica <strong>Solicitada</strong>.</li>
          <li>Se o cliente mudou algo, use <strong>Editar</strong>. Para desistir, use <strong>Cancelar</strong>.</li>
          <li>Use <strong>Ativar</strong> para o contrato passar a valer. Depois clique em <strong>Atualizar processos</strong> para criar a fatura e a preparação da retirada.</li>
        </ol>
      </Card>}
    </div>

    <Card title="Reservas">
      <ResourceView resource={reservations} label="reservas" empty="Nenhuma reserva registrada. Use o formulário acima.">
        {rows => rows.some(isOpen) ? <Table caption="Reservas" rows={rows.filter(isOpen)} rowKey={r => r.reservationId} columns={[
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'id', label: 'Reserva', render: r => <Id value={r.reservationId} /> },
          { key: 'group', label: 'Grupo / proteção', render: r => `${GROUPS.find(g => g.value === r.vehicleGroup)?.label ?? r.vehicleGroup} · ${PROTECTIONS.find(g => g.value === r.protectionCode)?.label ?? r.protectionCode}` },
          { key: 'period', label: 'Período', render: r => `${date(r.startsOn)} a ${date(r.endsOn)}` },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'status', label: 'Estado', render: r => <ReservationState value={r.status} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'actions', label: 'Ações', render: r => isOpen(r) ? <div className="row-actions">
            <button type="button" className="inline" disabled={busy} onClick={() => void activateReservation(r)}>Ativar</button>
            {r.status === 'REQUESTED' && <button type="button" className="inline quiet" disabled={busy} onClick={() => { setEditing(r); setClosing(null); clear() }}>Editar…</button>}
            <button type="button" className="inline quiet" disabled={busy} onClick={() => {
              if (window.confirm('Cancelar esta reserva?')) void run('Cancelamento da reserva', () => api.cancelReservation(r.reservationId), () => 'Reserva cancelada.').then(x => { if (x) refresh() })
            }}>Cancelar</button>
          </div> : '—' },
        ]} /> : <p className="empty">Nenhuma reserva solicitada. As reservas ativas seguem como contratos, logo abaixo.</p>}
      </ResourceView>
    </Card>

    <Card title="Contratos">
      {contractTable(active, 'Contratos', 'Nenhum contrato ativo. Ative uma reserva.')}
    </Card>

    <Card title="Histórico de Contratos">
      {contractTable(history, 'Histórico de contratos', 'Nenhum contrato encerrado ou cancelado ainda.', false)}
    </Card>
  </>
}
