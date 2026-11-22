import { useReducer, useState } from 'react'
import type { Invoice } from '../api'
import {
  ActionForm, Card, Field, FeedbackBanner, Id, PageIntro, PendingIntents, ResourceView, SelectField, Status, Table, date, dateTime, money, text,
  useActions, useIdempotencyKeys, useResource, useSession,
} from '../ui'
import { DispatchButton } from './shared'

const payableStatus = (i: Invoice) => i.status !== 'PAID' && i.status !== 'CANCELLED'
/** Regra do domínio (ADR-003): só fatura em aberto, sem pagamento, pode ser cancelada. */
const cancellable = (i: Invoice) => i.status === 'OPEN' && i.paidAmount === 0

export default function Finance() {
  const { api } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const keys = useIdempotencyKeys()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [cancelling, setCancelling] = useState<Invoice | null>(null)
  const [reference, setReference] = useState(() => `SIM-${Date.now()}`)

  const invoices = useResource(a => a.listInvoices(), [version])
  const customers = useResource(a => a.listCustomers(), [])
  const customerName = (id: string) => customers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)
  const payable = (invoices.data ?? []).filter(payableStatus)
  const all = invoices.data ?? []
  // Faturas: sem nenhum pagamento; Pagamentos: já receberam a primeira parcela e ainda têm saldo; Histórico: pagas ou canceladas.
  const pending = all.filter(i => payableStatus(i) && i.paidAmount === 0)
  const paying = all.filter(i => payableStatus(i) && i.paidAmount > 0)
  const history = all.filter(i => !payableStatus(i))

  function choose(invoiceId: string) {
    setSelected(invoices.data?.find(i => i.invoiceId === invoiceId) ?? null)
  }

  const invoiceColumns = [
    { key: 'customer', label: 'Cliente', render: (r: Invoice) => customerName(r.customerId) },
    { key: 'contract', label: 'Contrato', render: (r: Invoice) => <Id value={r.contractId} /> },
    { key: 'kind', label: 'Tipo', render: (r: Invoice) => r.kind === 'FINAL' ? 'Final' : 'Primeira' },
    { key: 'amount', label: 'Valor do contrato', render: (r: Invoice) => money(r.amount, r.currency) },
    { key: 'paid', label: 'Pago', render: (r: Invoice) => money(r.paidAmount, r.currency) },
    { key: 'balance', label: 'Valor devido', render: (r: Invoice) => money(Math.round((r.amount - r.paidAmount) * 100) / 100, r.currency) },
    { key: 'due', label: 'Vencimento', render: (r: Invoice) => date(r.dueDate) },
    { key: 'status', label: 'Estado', render: (r: Invoice) => <Status value={r.status} /> },
    { key: 'delinquency', label: 'Inadimplência', render: (r: Invoice) => r.delinquent
      ? <>Registrada em {dateTime(r.overdueSince)}</>
      : r.overdueSince ? <>Quitada após atraso</> : r.status === 'OVERDUE' ? <>Vencida, não registrada</> : <>—</> },
    { key: 'actions', label: 'Ações', render: (r: Invoice) => <div className="row-actions">
      {payableStatus(r) && <button type="button" className="inline" aria-pressed={selected?.invoiceId === r.invoiceId}
        onClick={() => { setSelected(r); clear() }}>Selecionar</button>}
      {cancellable(r) && <button type="button" className="inline quiet" disabled={busy} onClick={() => { setCancelling(r); clear() }}>Cancelar…</button>}
      {!payableStatus(r) && '—'}
    </div> },
  ]
  const invoiceTable = (rows: Invoice[], caption: string, empty: string) =>
    <ResourceView resource={invoices} label="faturas" isEmpty={() => rows.length === 0} empty={empty}>
      {() => <Table caption={caption} rows={rows} rowKey={r => r.invoiceId} columns={invoiceColumns} />}
    </ResourceView>
  return <>
    <PageIntro>Aqui você acompanha as faturas, registra pagamentos e confere o que está atrasado. Faturas sem pagamento ficam em Faturas; ao registrar a primeira parcela, vão para Pagamentos; quando são pagas ou canceladas, vão para o Histórico. Escolha uma fatura, informe o valor e registre o pagamento.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    <PendingIntents keys={keys} busy={busy} run={run} onCheck={refresh} />

    <div className="grid two">
      <Card title="Registrar pagamento">
        <ActionForm key={`${selected?.invoiceId ?? 'none'}-${reference}`} submit="Registrar pagamento" busy={busy} label="Pagamento simulado" onSubmit={async f => {
          const invoiceId = text(f, 'invoiceId')
          const invoice = invoices.data?.find(i => i.invoiceId === invoiceId)
          const body = { amount: Number(text(f, 'amount')), currency: invoice?.currency ?? 'BRL', reference }
          const result = await run('Registro do pagamento', () => keys.send(`payment:${invoiceId}`, body, key => api.recordPayment(invoiceId, body, key), 'Registro do pagamento'),
            r => r.invoice.balance > 0
              ? `Pagamento registrado. Já foram pagos ${money(r.invoice.paidAmount, r.invoice.currency)} de ${money(r.invoice.amount, r.invoice.currency)}. Falta pagar ${money(r.invoice.balance, r.invoice.currency)}.`
              : `Pagamento registrado. A fatura de ${money(r.invoice.amount, r.invoice.currency)} está paga.`)
          if (result) { setReference(`SIM-${Date.now()}`); setSelected(result.data.invoice); refresh() }
          return result !== null
        }}>
          <SelectField name="invoiceId" label="Fatura em aberto" defaultValue={selected && payableStatus(selected) ? selected.invoiceId : ''} onChange={choose}
            options={payable.map(i => ({ value: i.invoiceId, label: `${i.invoiceId.slice(0, 8)} · deve ${money(i.balance, i.currency)} · vence ${date(i.dueDate)}` }))}
            placeholder={invoices.status === 'loading' ? 'Carregando…' : payable.length ? 'Selecione' : 'Nenhuma fatura em aberto'} />
          <Field name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" defaultValue={selected && payableStatus(selected) ? selected.balance.toFixed(2) : ''}
            hint="Já vem com o valor devido da fatura. Informe um valor menor para registrar um pagamento parcial." />
        </ActionForm>
      </Card>

      {cancelling ? <Card title={`Cancelar fatura ${cancelling.invoiceId.slice(0, 8)}`}>
        <p>O cancelamento não pode ser desfeito. A fatura deixa de receber pagamentos e o valor não será cobrado de novo. Escreva o motivo sem dados pessoais.</p>
        <ActionForm key={cancelling.invoiceId} submit="Confirmar cancelamento" busy={busy} label="Cancelar fatura" onSubmit={async f => {
          const result = await run('Cancelamento da fatura', () => api.cancelInvoice(cancelling.invoiceId, text(f, 'reason')), () => 'Fatura cancelada.')
          if (result) { setCancelling(null); setSelected(null); refresh() }
          return result !== null
        }}>
          <Field name="reason" label="Motivo" defaultValue="Emitida em duplicidade (cenário fictício)" hint="De 3 a 200 caracteres." />
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setCancelling(null)}>Voltar</button>
      </Card> : <Card title="Como a fatura nasce">
        <ol className="steps">
          <li>Ative uma reserva em Reservas e contratos.</li>
          <li>Clique em Atualizar processos. A primeira fatura aparece aqui e vence em 10 dias.</li>
          <li>Registre um pagamento parcial ou total. A fatura fica Parcialmente paga e depois Paga.</li>
          <li>Ao encerrar o contrato, clique em Atualizar processos de novo para gerar a fatura final.</li>
        </ol>
        <DispatchButton busy={busy} run={run} onDone={refresh} />
      </Card>}
    </div>

    <Card title="Verificar vencimento e registrar inadimplência">
      <p>Faturas com valor devido e vencimento passado aparecem como Vencida. Clique em Verificar vencimento para registrar o atraso. Repetir a verificação não marca a mesma fatura duas vezes.</p>
      <ActionForm submit="Verificar vencimento" busy={busy} label="Verificação de vencimento" onSubmit={async f => {
        const asOf = text(f, 'asOf') || undefined
        const result = await run('Verificação de vencimento', () => api.checkOverdue(asOf),
          r => r.markedOverdue.length > 0
            ? `${r.markedOverdue.length === 1 ? '1 fatura foi registrada' : `${r.markedOverdue.length} faturas foram registradas`} como atrasada.`
            : 'Nenhuma fatura nova está atrasada.')
        if (result) { setSelected(null); refresh() }
        return result !== null
      }}>
        <Field name="asOf" label="Data de referência" type="date" required={false} hint="Se deixar vazio, usamos a data de hoje." />
      </ActionForm>
    </Card>

    <Card title="Faturas">
      {invoiceTable(pending, 'Faturas', 'Nenhuma fatura sem pagamento. Ative uma reserva e clique em Atualizar processos para gerar a primeira.')}
    </Card>

    <Card title="Pagamentos">
      {invoiceTable(paying, 'Pagamentos', 'Nenhuma fatura com pagamento em andamento.')}
    </Card>

    <Card title="Histórico">
      {invoiceTable(history, 'Histórico de faturas', 'Nenhuma fatura encerrada ainda. Faturas pagas ou canceladas aparecem aqui.')}
    </Card>
  </>
}
