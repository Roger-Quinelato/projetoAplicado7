import { useReducer, useState } from 'react'
import type { Invoice, InvoiceStatus } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, date, dateTime, money, text,
  useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const payableStatus = (i: Invoice) => i.status !== 'PAID' && i.status !== 'CANCELLED'

export default function Finance() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [statusFilter, setStatusFilter] = useState<'' | InvoiceStatus>('')
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [reference, setReference] = useState(() => `SIM-${Date.now()}`)

  const invoices = useResource(a => a.listInvoices(), [version])
  const payments = useResource(a => a.listPayments(selected?.invoiceId), [selected?.invoiceId, version])
  const payable = (invoices.data ?? []).filter(payableStatus)
  const visible = (invoices.data ?? []).filter(i => !statusFilter || i.status === statusFilter)

  function choose(invoiceId: string) {
    setSelected(invoices.data?.find(i => i.invoiceId === invoiceId) ?? null)
  }

  return <>
    <PageIntro>Fatura, pagamento, saldo, vencimento e inadimplência pertencem a Finance. A primeira fatura nasce do evento <code>ContractActivated.v1</code> e a fatura final de <code>ContractClosed.v1</code>, depois do despacho da outbox. Pagamentos são apenas simulados: não há PSP, conciliação bancária, nota fiscal nem cobrança real.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Registrar pagamento simulado" roles="finance, admin">
        <ActionForm key={`${selected?.invoiceId ?? 'none'}-${reference}`} submit="Registrar pagamento" busy={busy} label="Pagamento simulado" onSubmit={async f => {
          const invoiceId = text(f, 'invoiceId')
          const invoice = invoices.data?.find(i => i.invoiceId === invoiceId)
          const body = { amount: Number(text(f, 'amount')), currency: invoice?.currency ?? 'BRL', reference: text(f, 'reference') }
          const result = await run('Registro de pagamento', () => keys.send('payment', { invoiceId, ...body }, key => api.recordPayment(invoiceId, body, key)),
            r => `Fatura ${r.invoice.invoiceId.slice(0, 8)}: ${money(r.invoice.paidAmount, r.invoice.currency)} pagos de ${money(r.invoice.amount, r.invoice.currency)}; saldo ${money(r.invoice.balance, r.invoice.currency)}.`)
          if (result) { setReference(`SIM-${Date.now()}`); setSelected(result.data.invoice); refresh() }
          return result !== null
        }}>
          <SelectField name="invoiceId" label="Fatura em aberto" defaultValue={selected && payableStatus(selected) ? selected.invoiceId : ''} onChange={choose}
            options={payable.map(i => ({ value: i.invoiceId, label: `${i.invoiceId.slice(0, 8)} · saldo ${money(i.balance, i.currency)} · vence ${date(i.dueDate)}` }))}
            placeholder={invoices.status === 'loading' ? 'Carregando…' : payable.length ? 'Selecione' : 'Nenhuma fatura em aberto'} />
          <div className="form-grid">
            <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue={selected && payableStatus(selected) ? selected.balance.toFixed(2) : ''} />
            <Field name="reference" label="Referência única" defaultValue={reference} hint="Repetir a mesma referência e valor não duplica o pagamento." />
          </div>
        </ActionForm>
      </Card>

      <Card title="Como a fatura nasce" roles="despacho: operations, admin">
        <ol className="steps">
          <li>Ative um contrato em Reservas e contratos.</li>
          <li>Despache a outbox: o consumidor financeiro cria a primeira fatura com vencimento na data UTC do evento mais 10 dias (prazo é premissa a validar).</li>
          <li>Registre um pagamento parcial ou total; a fatura passa a “Parcialmente paga” e a “Paga” quando o saldo zera.</li>
          <li>Encerre o contrato e despache: a fatura final cobra os ciclos iniciados ainda não faturados (regra é premissa a validar).</li>
        </ol>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>
    </div>

    <Card title="Verificar vencimento e registrar inadimplência" roles="finance, operations, admin">
      <p>Fatura com saldo e data UTC posterior ao vencimento aparece como “Vencida”. A verificação registra a inadimplência (data e auditoria) e é idempotente: repetir não marca de novo. Data de referência futura só é aceita com a simulação local <code>FINANCE_ALLOW_FUTURE_AS_OF=true</code>.</p>
      <ActionForm submit="Verificar vencimento" busy={busy} label="Verificação de vencimento" onSubmit={async f => {
        const asOf = text(f, 'asOf') || undefined
        const result = await run('Verificação de vencimento', () => api.checkOverdue(asOf),
          r => `Referência ${date(r.asOf)}: ${r.markedOverdue.length} fatura(s) marcada(s) como inadimplente(s); ${r.alreadyOverdue} já registrada(s).`)
        if (result) { setSelected(null); refresh() }
        return result !== null
      }}>
        <Field name="asOf" label="Data de referência (UTC)" type="date" required={false} hint="Vazio: data UTC atual." />
      </ActionForm>
    </Card>

    <Card title="Faturas" roles="finance, operations, admin">
      <SelectField name="invoiceStatus" label="Estado" required={false} placeholder="Todos" onChange={v => setStatusFilter(v as '' | InvoiceStatus)}
        options={[{ value: 'OPEN', label: 'Em aberto' }, { value: 'PARTIALLY_PAID', label: 'Parcialmente paga' }, { value: 'PAID', label: 'Paga' },
          { value: 'OVERDUE', label: 'Vencida' }, { value: 'CANCELLED', label: 'Cancelada' }]} />
      <ResourceView resource={invoices} label="faturas" isEmpty={() => visible.length === 0}
        empty={statusFilter ? 'Nenhuma fatura neste estado.' : 'Nenhuma fatura ainda. Ative um contrato e despache os eventos.'}>
        {() => <Table caption="Faturas" rows={visible} rowKey={r => r.invoiceId} columns={[
          { key: 'id', label: 'Fatura', render: r => <Id value={r.invoiceId} /> },
          { key: 'contract', label: 'Contrato', render: r => <Id value={r.contractId} /> },
          { key: 'kind', label: 'Tipo', render: r => r.kind === 'FINAL' ? 'Final' : 'Primeira' },
          { key: 'amount', label: 'Valor', render: r => money(r.amount, r.currency) },
          { key: 'paid', label: 'Pago', render: r => money(r.paidAmount, r.currency) },
          { key: 'balance', label: 'Saldo', render: r => money(r.balance, r.currency) },
          { key: 'due', label: 'Vencimento', render: r => date(r.dueDate) },
          { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
          { key: 'delinquency', label: 'Inadimplência', render: r => r.delinquent
            ? <>Registrada em {dateTime(r.overdueSince)}</>
            : r.overdueSince ? <>Quitada após atraso</> : r.status === 'OVERDUE' ? <>Vencida, não registrada</> : <>—</> },
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
