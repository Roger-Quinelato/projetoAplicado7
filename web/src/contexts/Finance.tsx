import { useReducer, useState } from 'react'
import type { Invoice, InvoiceStatus } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, Panel, ResourceView, SelectField, Stack, Status, Table, date, dateTime, money, text,
  useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'

const payableStatus = (i: Invoice) => i.status !== 'PAID' && i.status !== 'CANCELLED'
const STATUS_FILTER = [{ value: 'OPEN', label: 'Em aberto' }, { value: 'PARTIALLY_PAID', label: 'Parcialmente paga' }, { value: 'PAID', label: 'Paga' },
  { value: 'OVERDUE', label: 'Vencida' }, { value: 'CANCELLED', label: 'Cancelada' }]

export default function Finance() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [statusFilter, setStatusFilter] = useState<'' | InvoiceStatus>('')
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [paying, setPaying] = useState(false)
  const [overduePanel, setOverduePanel] = useState(false)
  const [reference, setReference] = useState(() => `SIM-${Date.now()}`)

  const invoices = useResource(a => a.listInvoices(), [version])
  const payments = useResource(a => a.listPayments(selected?.invoiceId), [selected?.invoiceId, version])
  const all = invoices.data ?? []
  const payable = all.filter(payableStatus)
  const visible = all.filter(i => !statusFilter || i.status === statusFilter)
  const overdue = all.filter(i => i.status === 'OVERDUE')
  const paid = all.filter(i => i.status === 'PAID')
  const receivable = payable.reduce((sum, i) => sum + Number(i.balance), 0)

  function pay(invoice: Invoice) { setSelected(invoice); setPaying(true); clear() }

  return <>
    <PageIntro>Faturas e pagamentos são simulados: não há meio de pagamento, conciliação bancária nem nota fiscal. A primeira fatura nasce da ativação do contrato (<code>ContractActivated.v1</code>), e a final, do encerramento (<code>ContractClosed.v1</code>), depois do despacho.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <Card title="Faturas" aside={<div className="head-actions">
      <div className="inline-filter">
        <label htmlFor="invoice-status">Estado</label>
        <select id="invoice-status" value={statusFilter} onChange={e => setStatusFilter(e.target.value as '' | InvoiceStatus)}>
          <option value="">Todos</option>
          {STATUS_FILTER.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
      <button type="button" className="secondary" aria-expanded={overduePanel} onClick={() => { setOverduePanel(v => !v); clear() }}>Verificar vencimento</button>
    </div>}>
      {invoices.data && <div className="summary" aria-label="Resumo das faturas">
        <div><span>A receber</span><strong>{money(receivable, payable[0]?.currency ?? 'BRL')}</strong><small>{payable.length === 1 ? '1 fatura com saldo' : `${payable.length} faturas com saldo`}</small></div>
        <div><span>Vencidas</span><strong>{overdue.length}</strong><small>{overdue.filter(i => !i.delinquent).length} sem inadimplência registrada</small></div>
        <div><span>Pagas</span><strong>{paid.length}</strong><small>{money(paid.reduce((s, i) => s + Number(i.paidAmount), 0), paid[0]?.currency ?? 'BRL')} recebidos</small></div>
      </div>}
      <ResourceView resource={invoices} label="faturas" isEmpty={() => visible.length === 0}
        empty={statusFilter ? 'Nenhuma fatura neste estado.' : 'Nenhuma fatura ainda. Ative um contrato e despache os eventos na barra do topo.'}>
        {() => <Table caption="Faturas" rows={visible} rowKey={r => r.invoiceId} rowClass={r => selected?.invoiceId === r.invoiceId ? 'selected' : undefined} columns={[
          { key: 'id', label: 'Fatura', render: r => <Stack main={<Id value={r.invoiceId} />} sub={<>Contrato <Id value={r.contractId} /></>} /> },
          { key: 'kind', label: 'Tipo', render: r => r.kind === 'FINAL' ? 'Final' : 'Primeira' },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'paid', label: 'Pago', render: r => money(r.paidAmount, r.currency) },
          { key: 'balance', label: 'Saldo', render: r => money(r.balance, r.currency) },
          { key: 'due', label: 'Vencimento', render: r => date(r.dueDate) },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'delinquency', label: 'Inadimplência', render: r => r.delinquent
            ? <>Registrada em {dateTime(r.overdueSince)}</>
            : r.overdueSince ? <>Quitada após atraso</> : r.status === 'OVERDUE' ? <strong className="field-error-text">Não registrada</strong> : <>—</> },
          { key: 'actions', label: 'Ações', render: r => payableStatus(r)
            ? <button type="button" className="inline" aria-pressed={selected?.invoiceId === r.invoiceId && paying} onClick={() => pay(r)}>Registrar pagamento</button>
            : <button type="button" className="inline quiet" aria-pressed={selected?.invoiceId === r.invoiceId} onClick={() => { setSelected(r); setPaying(false); clear() }}>Ver pagamentos</button> },
        ]} />}
      </ResourceView>
    </Card>

    {overduePanel && <Panel title="Verificar vencimento e registrar inadimplência" onClose={() => setOverduePanel(false)}>
      <p>Fatura com saldo e data UTC posterior ao vencimento aparece como “Vencida”. A verificação registra a inadimplência (data e auditoria) e pode ser repetida sem marcar de novo. Data de referência futura só é aceita com a simulação local <code>FINANCE_ALLOW_FUTURE_AS_OF=true</code>.</p>
      <ActionForm submit="Verificar vencimento" busy={busy} label="Verificação de vencimento" onSubmit={async f => {
        const asOf = text(f, 'asOf') || undefined
        const result = await run('Verificação de vencimento', () => api.checkOverdue(asOf), undefined, {
          success: r => r.markedOverdue.length === 0
            ? `Nenhuma fatura nova inadimplente na referência ${date(r.asOf)}${r.alreadyOverdue ? `; ${r.alreadyOverdue} já registrada(s)` : ''}.`
            : `${r.markedOverdue.length} fatura(s) registrada(s) como inadimplente(s) na referência ${date(r.asOf)}.`,
          failure: 'Não foi possível verificar o vencimento.',
        })
        if (result) { setSelected(null); refresh() }
        return result !== null
      }}>
        <Field name="asOf" label="Data de referência (UTC)" type="date" required={false} hint="Vazio: data UTC atual." />
      </ActionForm>
    </Panel>}

    <div className="grid two">
      {selected && paying && payableStatus(selected)
        ? <Panel title={`Registrar pagamento · fatura ${selected.invoiceId.slice(0, 8)}`} onClose={() => setPaying(false)}>
          <ActionForm key={`${selected.invoiceId}-${reference}`} submit="Registrar pagamento" busy={busy} label="Pagamento simulado" onSubmit={async f => {
            const invoiceId = text(f, 'invoiceId')
            const invoice = invoices.data?.find(i => i.invoiceId === invoiceId)
            const body = { amount: Number(text(f, 'amount')), currency: invoice?.currency ?? 'BRL', reference: text(f, 'reference') }
            const result = await run('Registro de pagamento', () => keys.send('payment', { invoiceId, ...body }, key => api.recordPayment(invoiceId, body, key)), undefined, {
              success: r => `Pagamento registrado na fatura ${r.invoice.invoiceId.slice(0, 8)}: ${money(r.invoice.paidAmount, r.invoice.currency)} pagos de ${money(r.invoice.amount, r.invoice.currency)}; saldo ${money(r.invoice.balance, r.invoice.currency)}.`,
              failure: 'Não foi possível registrar o pagamento.',
            })
            if (result) { setReference(`SIM-${Date.now()}`); setSelected(result.data.invoice); if (!payableStatus(result.data.invoice)) setPaying(false); refresh() }
            return result !== null
          }}>
            <SelectField name="invoiceId" label="Fatura" defaultValue={selected.invoiceId} onChange={id => { const i = payable.find(x => x.invoiceId === id); if (i) setSelected(i) }}
              options={payable.map(i => ({ value: i.invoiceId, label: `${i.invoiceId.slice(0, 8)} · saldo ${money(i.balance, i.currency)} · vence ${date(i.dueDate)}` }))} />
            <div className="form-grid">
              <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue={selected.balance.toFixed(2)} hint="Preenchido com o saldo; pode ser parcial." />
              <Field name="reference" label="Referência única" defaultValue={reference} hint="Repetir a mesma referência e valor não duplica o pagamento." />
            </div>
          </ActionForm>
        </Panel>
        : <Card title="Como a fatura nasce">
          <ol className="flow-steps">
            <li><span>Ative um contrato em Reservas e contratos e despache os eventos na barra do topo.</span></li>
            <li><span>A primeira fatura vence na data UTC do evento mais 10 dias (prazo é premissa a validar).</span></li>
            <li><span>Pagamento parcial deixa a fatura “Parcialmente paga”; quando o saldo zera, ela fica “Paga”.</span></li>
            <li><span>Encerrar o contrato e despachar gera a fatura final dos ciclos iniciados ainda não faturados (regra é premissa a validar).</span></li>
          </ol>
        </Card>}

      <Card title={selected ? `Pagamentos da fatura ${selected.invoiceId.slice(0, 8)}` : 'Pagamentos (todas as faturas)'}
        aside={selected && <button type="button" className="secondary small" onClick={() => { setSelected(null); setPaying(false) }}>Mostrar todos</button>}>
        <ResourceView resource={payments} label="pagamentos" empty="Nenhum pagamento registrado.">
          {rows => <Table caption="Pagamentos" rows={rows} rowKey={r => r.paymentId} columns={[
            { key: 'id', label: 'Pagamento', render: r => <Stack main={<Id value={r.paymentId} />} sub={<>Fatura <Id value={r.invoiceId} /></>} /> },
            { key: 'amount', label: 'Valor e referência', render: r => <Stack main={money(r.amount, r.currency)} sub={r.reference} /> },
          ]} />}
        </ResourceView>
        {selected && <p className="muted">Saldo restante: {money(selected.balance, selected.currency)}.</p>}
      </Card>
    </div>
  </>
}
