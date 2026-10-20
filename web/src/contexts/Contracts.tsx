import { useReducer, useState } from 'react'
import type { ApiResult, BillingCycle, Contract, Reservation } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, MoreMenu, PageIntro, Panel, ResourceView, SelectField, Stack, Status, Table, date, isoDate, money,
  text, useActions, useConfirm, useIdempotencyKeys, useResource, useSession,
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
const labelOf = (list: { value: string, label: string }[], value: string) => list.find(o => o.value === value)?.label ?? value

type PanelState = { kind: 'reservation' } | { kind: 'draft' } | { kind: 'close', contract: Contract } | null

export default function Contracts({ params }: { params: URLSearchParams }) {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const { ask, dialog } = useConfirm()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const preselected = params.get('customer') ?? ''
  // Vindo do CRM com o cliente escolhido, o painel da reserva já abre.
  const [panel, setPanel] = useState<PanelState>(preselected ? { kind: 'reservation' } : null)

  const customers = useResource(a => a.listCustomers({ active: true }), [version])
  const reservations = useResource(a => a.listReservations(), [version])
  const contracts = useResource(a => a.listContracts(), [version])

  const customerOptions = (customers.data ?? []).map(c => ({ value: c.customerId, label: `${c.name} · ${c.email}` }))
  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  /** Executa um comando idempotente; a chave só é reaproveitada se o corpo da nova tentativa for idêntico. */
  async function idempotent<T, B>(intent: string, label: string, body: B, call: (body: B, key: string) => Promise<ApiResult<T>>,
    messages: { success: (data: T) => string, failure: string }) {
    const result = await run(label, () => keys.send(intent, body, key => call(body, key)), undefined, messages)
    if (result) refresh()
    return result !== null
  }

  async function cancelReservation(r: Reservation) {
    const ok = await ask({
      title: `Cancelar a reserva ${r.reservationId.slice(0, 8)}?`,
      body: r.status === 'DRAFTED' ? 'O rascunho de contrato vinculado também será cancelado. O histórico fica preservado.' : 'A reserva deixa de poder gerar rascunho. O histórico fica preservado.',
      confirm: 'Cancelar reserva', cancel: 'Manter reserva',
    })
    if (!ok) return
    const result = await run('Cancelamento de reserva', () => api.cancelReservation(r.reservationId), undefined,
      { success: () => `Reserva ${r.reservationId.slice(0, 8)} cancelada.`, failure: 'Não foi possível cancelar a reserva.' })
    if (result) refresh()
  }

  return <>
    <PageIntro>O contrato nasce da reserva com o cliente oficial do CRM, sem recadastro. Ativar o contrato gera o evento <code>ContractActivated.v1</code>, que cria a fatura e a preparação de retirada depois do despacho.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    {dialog}

    <Card title="Reservas" aside={<div className="head-actions">
      <button type="button" className="secondary" onClick={() => { setPanel({ kind: 'draft' }); clear() }}>Rascunho sem reserva</button>
      <button type="button" onClick={() => { setPanel({ kind: 'reservation' }); clear() }}>Nova reserva</button>
    </div>}>
      <ResourceView resource={reservations} label="reservas" empty="Nenhuma reserva registrada. Use “Nova reserva” com um cliente do CRM.">
        {rows => <Table caption="Reservas" rows={rows} rowKey={r => r.reservationId} columns={[
          { key: 'id', label: 'Reserva', render: r => <Id value={r.reservationId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'group', label: 'Veículo', render: r => <Stack main={labelOf(GROUPS, r.vehicleGroup)} sub={`Proteção ${labelOf(PROTECTIONS, r.protectionCode).toLowerCase()}`} /> },
          { key: 'period', label: 'Período', render: r => <Stack main={date(r.startsOn)} sub={`a ${date(r.endsOn)}`} /> },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'actions', label: 'Ações', render: r => r.status === 'REQUESTED' ? <div className="row-actions">
            <button type="button" className="inline" disabled={busy} onClick={() => void idempotent(`draft:${r.reservationId}`, 'Geração de rascunho',
              null, (_body, key) => api.draftFromReservation(r.reservationId, key),
              { success: d => `Contrato ${d.contract.contractId.slice(0, 8)} em rascunho para o mesmo cliente. Ative-o na tabela de contratos.`, failure: 'Não foi possível gerar o rascunho.' })}>Gerar rascunho</button>
            <MoreMenu label={`reserva ${r.reservationId.slice(0, 8)}`} items={[{ label: 'Cancelar reserva…', danger: true, disabled: busy, onSelect: () => void cancelReservation(r) }]} />
          </div> : r.status === 'DRAFTED'
            ? <button type="button" className="inline danger" disabled={busy} onClick={() => void cancelReservation(r)}>Cancelar</button>
            : '—' },
        ]} />}
      </ResourceView>
    </Card>

    <Card title="Contratos">
      <ResourceView resource={contracts} label="contratos" empty="Nenhum contrato. Gere um rascunho a partir de uma reserva.">
        {rows => <Table caption="Contratos" rows={rows} rowKey={r => r.contractId} columns={[
          { key: 'id', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
          { key: 'service', label: 'Serviço', render: r => r.serviceCode },
          { key: 'period', label: 'Vigência', render: r => <Stack main={date(r.startsOn)} sub={r.endsOn ? `a ${date(r.endsOn)}` : 'sem data de fim'} /> },
          { key: 'billing', label: 'Cobrança', render: r => <Stack main={money(r.billing.amount, r.billing.currency)} sub={labelOf(CYCLES, r.billing.cycle)} /> },
          { key: 'sla', label: 'SLA', render: r => `${r.slaHours} h` },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'actions', label: 'Ações', render: r => r.status === 'DRAFT'
            ? <button type="button" className="inline" disabled={busy} onClick={() => void idempotent(`activate:${r.contractId}`, 'Ativação de contrato',
              null, (_body, key) => api.activateContract(r.contractId, key),
              { success: c => `Contrato ${c.contractId.slice(0, 8)} ativado. Despache os eventos na barra do topo para gerar a fatura e a preparação de retirada.`, failure: 'Não foi possível ativar o contrato.' })}>Ativar</button>
            : r.status === 'ACTIVE'
              ? <div className="row-actions">
                <button type="button" className="inline" onClick={() => navigate(`/atendimento?contract=${r.contractId}`)}>Abrir chamado</button>
                <MoreMenu label={`contrato ${r.contractId.slice(0, 8)}`} items={[{ label: 'Encerrar contrato…', danger: true, disabled: busy, onSelect: () => { setPanel({ kind: 'close', contract: r }); clear() } }]} />
              </div>
              : '—' },
        ]} />}
      </ResourceView>
    </Card>

    {panel && <div className="grid two">
      {panel.kind === 'reservation' && <Panel title="Nova reserva" onClose={() => setPanel(null)}>
        <ActionForm key={preselected} submit="Registrar reserva" busy={busy} label="Nova reserva" onSubmit={f => idempotent('reservation', 'Registro de reserva', {
            customerId: text(f, 'customerId'), vehicleGroup: text(f, 'vehicleGroup'), protectionCode: text(f, 'protectionCode'),
            serviceCode: text(f, 'serviceCode'), startsOn: text(f, 'startsOn'), endsOn: text(f, 'endsOn'),
            amount: Number(text(f, 'amount')), currency: 'BRL', billingCycle: text(f, 'billingCycle') as BillingCycle,
            slaHours: Number(text(f, 'slaHours')),
          }, api.createReservation, { success: r => `Reserva ${r.reservationId.slice(0, 8)} solicitada. Gere o rascunho na tabela de reservas.`, failure: 'Não foi possível registrar a reserva.' })}>
          <SelectField name="customerId" label="Cliente (CRM)" options={customerOptions} defaultValue={preselected}
            hint={preselected ? 'Já escolhido a partir do CRM.' : undefined}
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
      </Panel>}

      {panel.kind === 'draft' && <Panel title="Rascunho sem reserva" onClose={() => setPanel(null)}>
        <p>Alternativa do F1 documentada no roteiro: cria o rascunho a partir do cliente do CRM, sem passar pela reserva.</p>
        <ActionForm submit="Criar rascunho" busy={busy} label="Rascunho sem reserva" onSubmit={f => idempotent('draft', 'Criação de rascunho', {
            customerId: text(f, 'customerId'), serviceCode: text(f, 'serviceCode'), startsOn: text(f, 'startsOn'),
            billing: { amount: Number(text(f, 'amount')), currency: 'BRL', cycle: text(f, 'cycle') as BillingCycle },
            slaHours: Number(text(f, 'slaHours')),
          }, api.createDraft, { success: c => `Contrato ${c.contractId.slice(0, 8)} em rascunho. Ative-o na tabela de contratos.`, failure: 'Não foi possível criar o rascunho.' })}>
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
      </Panel>}

      {panel.kind === 'close' && <Panel title={`Encerrar contrato ${panel.contract.contractId.slice(0, 8)}`} onClose={() => setPanel(null)}>
        <p>O encerramento publica <code>ContractClosed.v1</code>. Depois do despacho, a fatura final é gerada e a preparação de retirada é concluída.</p>
        <ActionForm key={panel.contract.contractId} submit="Encerrar contrato" busy={busy} label="Encerrar contrato" onSubmit={async f => {
          const contract = panel.contract
          const ok = await idempotent(`close:${contract.contractId}`, 'Encerramento de contrato',
            { endsOn: text(f, 'endsOn') || null, reason: text(f, 'reason') || null }, (body, key) => api.closeContract(contract.contractId, body, key),
            { success: c => `Contrato ${c.contractId.slice(0, 8)} encerrado. Despache os eventos para gerar a fatura final.`, failure: 'Não foi possível encerrar o contrato.' })
          if (ok) setPanel(null)
          return ok
        }}>
          <Field name="endsOn" label="Data de encerramento" type="date" required={false} hint="Vazio: data atual ou início do contrato, o que for posterior." />
          <Field name="reason" label="Motivo" required={false} defaultValue="Devolução do veículo" hint="Não inclua dados pessoais ou sensíveis." />
        </ActionForm>
      </Panel>}

      <Card title="Como o contrato nasce">
        <ol className="flow-steps">
          <li><span>Registre a reserva com um cliente do CRM.</span></li>
          <li><span>Gere o rascunho na tabela de reservas. A mesma reserva não gera dois rascunhos.</span></li>
          <li><span>Ative o contrato. O evento <code>ContractActivated.v1</code> aparece na barra de eventos.</span></li>
          <li><span>Encerrar o contrato (em “Mais”) gera a fatura final depois do despacho.</span></li>
        </ol>
      </Card>
    </div>}
  </>
}
