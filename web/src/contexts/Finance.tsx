import { useReducer, useState } from 'react'
import type { Invoice, InvoiceStatus } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, date, money, text,
  useActions, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

function balance(invoice: Invoice): number {
  return Math.round((Number(invoice.amount) - Number(invoice.paidAmount)) * 100) / 100
}

export default function Finance() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [statusFilter, setStatusFilter] = useState<'' | InvoiceStatus>('')
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [reference, setReference] = useState(() => `SIM-${Date.now()}`)

  const invoices = useResource(a => a.listInvoices(), [version])
  const payments = useResource(a => a.listPayments(selected?.invoiceId), [selected?.invoiceId, version])
  const payable = (invoices.data ?? []).filter(i => i.status !== 'PAID')
  const visible = (invoices.data ?? []).filter(i => !statusFilter || i.status === statusFilter)

  function choose(invoiceId: string) {
    setSelected(invoices.data?.find(i => i.invoiceId === invoiceId) ?? null)
  }

  return <>
    <PageIntro>Fatura, pagamento, saldo e vencimento pertencem a Finance. A primeira fatura nasce do evento <code>ContractActivated.v1</code> depois do despacho da outbox. Pagamentos são apenas simulados: não há PSP, conciliação bancária nem cobrança real.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Registrar pagamento simulado" roles="finance, admin">
        <ActionForm key={`${selected?.invoiceId ?? 'none'}-${reference}`} submit="Registrar pagamento" busy={busy} label="Pagamento simulado" onSubmit={async f => {
          const invoiceId = text(f, 'invoiceId')
          const invoice = invoices.data?.find(i => i.invoiceId === invoiceId)
          const result = await run('Registro de pagamento', () => api.recordPayment(invoiceId, {
            amount: Number(text(f, 'amount')), currency: invoice?.currency ?? 'BRL', reference: text(f, 'reference'),
          }), r => `Fatura ${r.invoice.invoiceId.slice(0, 8)}: ${money(r.invoice.paidAmount, r.invoice.currency)} pagos de ${money(r.invoice.amount, r.invoice.currency)}.`)
          if (result) { setReference(`SIM-${Date.now()}`); setSelected(result.data.invoice); refresh() }
          return result !== null
        }}>
          <SelectField name="invoiceId" label="Fatura em aberto" defaultValue={selected && selected.status !== 'PAID' ? selected.invoiceId : ''} onChange={choose}
            options={payable.map(i => ({ value: i.invoiceId, label: `${i.invoiceId.slice(0, 8)} · saldo ${money(balance(i), i.currency)} · vence ${date(i.dueDate)}` }))}
            placeholder={invoices.status === 'loading' ? 'Carregando…' : payable.length ? 'Selecione' : 'Nenhuma fatura em aberto'} />
          <div className="form-grid">
            <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue={selected && selected.status !== 'PAID' ? balance(selected).toFixed(2) : ''} />
            <Field name="reference" label="Referência única" defaultValue={reference} hint="Repetir a mesma referência e valor não duplica o pagamento." />
          </div>
        </ActionForm>
      </Card>

      <Card title="Como a fatura nasce" roles="despacho: operations, admin">
        <ol className="steps">
          <li>Ative um contrato em Reservas e contratos.</li>
          <li>Despache a outbox: o consumidor financeiro cria a primeira fatura com vencimento em 10 dias.</li>
          <li>Registre um pagamento parcial ou total; a fatura passa a “Paga” quando o saldo zera.</li>
        </ol>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>
    </div>

    <Card title="Faturas" roles="finance, operations, admin">
      <SelectField name="invoiceStatus" label="Estado" required={false} placeholder="Todos" onChange={v => setStatusFilter(v as '' | InvoiceStatus)}
        options={[{ value: 'OPEN', label: 'Em aberto' }, { value: 'PAID', label: 'Paga' }, { value: 'OVERDUE', label: 'Vencida' }]} />
      <ResourceView resource={invoices} label="faturas" isEmpty={() => visible.length === 0}
        empty={statusFilter ? 'Nenhuma fatura neste estado.' : 'Nenhuma fatura ainda. Ative um contrato e despache os eventos.'}>
        {() => <Table caption="Faturas" rows={visible} rowKey={r => r.invoiceId} columns={[
          { key: 'id', label: 'Fatura', render: r => <Id value={r.invoiceId} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'paid', label: 'Pago', render: r => money(r.paidAmount, r.currency) },
          { key: 'balance', label: 'Saldo', render: r => money(balance(r), r.currency) },
          { key: 'due', label: 'Vencimento', render: r => date(r.dueDate) },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline" aria-pressed={selected?.invoiceId === r.invoiceId}
            onClick={() => { setSelected(r); clear() }}>{r.status === 'PAID' ? 'Ver pagamentos' : 'Selecionar'}</button> },
        ]} />}
      </ResourceView>
    </Card>

    <Card title={selected ? `Pagamentos da fatura ${selected.invoiceId.slice(0, 8)}` : 'Pagamentos (todas as faturas)'} roles="finance, admin"
      aside={selected && <button type="button" className="secondary small" onClick={() => setSelected(null)}>Mostrar todos</button>}>
      <ResourceView resource={payments} label="pagamentos" empty="Nenhum pagamento registrado.">
        {rows => <Table caption="Pagamentos" rows={rows} rowKey={r => r.paymentId} columns={[
          { key: 'id', label: 'Pagamento', render: r => <Id value={r.paymentId} /> },
          { key: 'invoice', label: 'Fatura', render: r => <Id value={r.invoiceId} /> },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'reference', label: 'Referência', render: r => r.reference },
        ]} />}
      </ResourceView>
    </Card>
  </>
}
