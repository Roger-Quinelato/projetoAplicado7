import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'

type Row = Record<string, any>
type Module = 'Visão geral' | 'CRM' | 'Reservas e contratos' | 'Financeiro' | 'Atendimento' | 'Workflow'
const modules: Module[] = ['Visão geral', 'CRM', 'Reservas e contratos', 'Financeiro', 'Atendimento', 'Workflow']
const endpoints = {
  customers: '/api/v1/crm/customers', contacts: '/api/v1/crm/contacts', opportunities: '/api/v1/crm/opportunities',
  reservations: '/api/v1/contracts/reservations', contracts: '/api/v1/contracts', invoices: '/api/v1/finance/invoices',
  tickets: '/api/v1/support/tickets', processes: '/api/v1/workflow/processes', tasks: '/api/v1/workflow/tasks',
} as const
type Collection = keyof typeof endpoints
type Collections = Record<Collection, Row[]>
const empty: Collections = { customers: [], contacts: [], opportunities: [], reservations: [], contracts: [], invoices: [], tickets: [], processes: [], tasks: [] }

function field(form: FormData, name: string): string { return String(form.get(name) ?? '').trim() }
function Label({ children }: { children: ReactNode }) { return <span className="label">{children}</span> }
function Card({ title, children, aside }: { title: string, children: ReactNode, aside?: ReactNode }) {
  return <section className="card"><div className="card-head"><h2>{title}</h2>{aside}</div>{children}</section>
}
function Input({ name, label, type = 'text', required = true, value, min, step }: { name: string, label: string, type?: string, required?: boolean, value?: string, min?: string, step?: string }) {
  return <label><Label>{label}</Label><input name={name} type={type} required={required} defaultValue={value} min={min} step={step} /></label>
}
function Select({ name, label, values, required = true, placeholder = 'Selecione', defaultValue }: { name: string, label: string, values: { value: string, label: string }[], required?: boolean, placeholder?: string, defaultValue?: string }) {
  return <label><Label>{label}</Label><select name={name} required={required} defaultValue={defaultValue ?? ''}><option value="">{placeholder}</option>{values.map(x => <option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
}
function ActionForm({ children, submit, onSubmit }: { children: ReactNode, submit: string, onSubmit: (data: FormData) => void | Promise<void> }) {
  return <form onSubmit={e => { e.preventDefault(); void onSubmit(new FormData(e.currentTarget)); e.currentTarget.reset() }}>{children}<button type="submit">{submit}</button></form>
}
function Table({ rows, columns, emptyText = 'Sem registros ainda.' }: { rows: Row[], columns: { key: string, label: string, render?: (row: Row) => ReactNode }[], emptyText?: string }) {
  if (!rows.length) return <p className="empty">{emptyText}</p>
  return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={r.id ?? r.customerId ?? r.reservationId ?? r.contractId ?? r.invoiceId ?? r.ticketId ?? r.processId ?? r.taskId ?? i}>{columns.map(c => <td key={c.key}>{c.render ? c.render(r) : String(r[c.key] ?? '—')}</td>)}</tr>)}</tbody></table></div>
}
function short(value: string | undefined) { return value ? value.slice(0, 8) + '…' : '—' }
function money(value: unknown) { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value ?? 0)) }
function formatDate(value: string | undefined) { return value ? new Date(value).toLocaleString('pt-BR') : '—' }
function status(value: string) { return <span className={'status ' + (['ACTIVE', 'OPEN', 'PAID', 'COMPLETED', 'DONE', 'RESOLVED'].includes(value) ? 'good' : ['OVERDUE', 'REJECTED_ENTITLEMENT', 'CANCELLED'].includes(value) ? 'bad' : '')}>{value}</span> }

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('archcorp-demo-token') || (import.meta.env.DEV ? 'demo-admin' : ''))
  const [entry, setEntry] = useState(token)
  const [module, setModule] = useState<Module>('Visão geral')
  const [data, setData] = useState<Collections>(empty)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [connected, setConnected] = useState(false)

  const request = useCallback(async (path: string, method = 'GET', body?: unknown, idempotent = false) => {
    const response = await fetch(path, { method, headers: {
      Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(idempotent ? { 'Idempotency-Key': crypto.randomUUID() } : {}),
    }, body: body ? JSON.stringify(body) : undefined })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = typeof result.detail === 'string' ? result.detail
        : Array.isArray(result.detail) ? result.detail.map((item: Row) => item.msg).join('; ')
        : `Erro HTTP ${response.status}`
      throw new Error(detail)
    }
    return result
  }, [token])

  const refresh = useCallback(async () => {
    if (!token) return
    const results = await Promise.all(Object.entries(endpoints).map(async ([key, path]) => [key, await request(path)] as const))
    setData(Object.fromEntries(results) as Collections)
    setConnected(true)
  }, [request, token])

  useEffect(() => { void refresh().catch(err => { setConnected(false); setNotice(`Falha ao carregar: ${err.message}`) }) }, [refresh])

  async function act(label: string, action: () => Promise<unknown>) {
    setBusy(true); setNotice('')
    try { await action(); await refresh(); setNotice(`${label} concluído.`) }
    catch (err) { setNotice(`Não foi possível concluir: ${err instanceof Error ? err.message : String(err)}`) }
    finally { setBusy(false) }
  }
  function login(event: FormEvent) {
    event.preventDefault()
    const next = entry.trim()
    sessionStorage.setItem('archcorp-demo-token', next)
    setToken(next)
    setNotice('')
  }
  const customerOptions = data.customers.map(x => ({ value: x.customerId, label: x.name }))
  const contractOptions = data.contracts.map(x => ({ value: x.contractId, label: `${short(x.contractId)} · ${x.serviceCode} · ${x.status}` }))
  const invoiceOptions = data.invoices.filter(x => x.status !== 'PAID').map(x => ({ value: x.invoiceId, label: `${short(x.invoiceId)} · ${money(x.amount)} · ${x.status}` }))
  const ticketOptions = data.tickets.filter(x => x.status === 'OPEN').map(x => ({ value: x.ticketId, label: `${short(x.ticketId)} · ${x.category}` }))

  if (!token || !connected) return <div className="gate"><div className="gate-card"><div className="mark">A</div><p className="eyebrow">ARCHCORP · AMBIENTE ACADÊMICO</p><h1>Operações integradas</h1><p>Entre com a credencial de demonstração para testar os fluxos com dados sintéticos. Solicite a credencial ao responsável pelo projeto.</p><form onSubmit={login}><label><Label>Credencial de acesso</Label><input type="password" value={entry} onChange={e => setEntry(e.target.value)} required autoComplete="off" /></label><button type="submit">Acessar demonstração</button></form>{notice && <p className="alert">{notice}</p>}<small>Projeto conceitual; sem conexão com sistemas reais da Localiza.</small></div></div>

  return <div className="shell">
    <aside className="sidebar"><div className="brand"><div className="mark">A</div><div><strong>ArchCorp</strong><span>Integração aplicada</span></div></div><p className="sidebar-title">ÁREAS DE TRABALHO</p><nav>{modules.map(m => <button className={module === m ? 'active' : ''} key={m} onClick={() => setModule(m)}>{m}</button>)}</nav><div className="side-bottom"><span className="online-dot" />API conectada<button onClick={() => { sessionStorage.removeItem('archcorp-demo-token'); setToken(''); setConnected(false); setEntry('') }}>Sair</button></div></aside>
    <main><header className="topbar"><div><p className="eyebrow">PROJETO APLICADO 7 / CENÁRIO 4</p><h1>{module}</h1></div><div className="top-actions"><a href="/docs" target="_blank" rel="noreferrer">Documentação da API ↗</a><button className="secondary" onClick={() => void act('Atualização', refresh)} disabled={busy}>Atualizar</button></div></header>
    {notice && <div className="notice" role="status">{notice}<button aria-label="Fechar aviso" onClick={() => setNotice('')}>×</button></div>}
    {module === 'Visão geral' && <><div className="stats">{([['Clientes', data.customers.length], ['Contratos', data.contracts.length], ['Faturas', data.invoices.length], ['Chamados', data.tickets.length], ['Processos', data.processes.length]] as const).map(([label, count]) => <div className="stat" key={label}><span>{label}</span><strong>{count}</strong></div>)}</div><div className="grid two"><Card title="Fluxo de ponta a ponta"><ol className="steps"><li>Cadastre um cliente no CRM.</li><li>Crie uma reserva, gere o contrato e ative.</li><li>Despache os eventos em Integração para gerar fatura e processo.</li><li>Registre um pagamento simulado e abra um chamado.</li><li>Despache o evento do chamado, atribua e resolva o atendimento.</li></ol><button onClick={() => void act('Despacho de eventos', () => request('/api/v1/integration/outbox/dispatch', 'POST'))} disabled={busy}>Despachar eventos pendentes</button></Card><Card title="Escopo desta demonstração"><p>CRM, reservas e contratos, financeiro, atendimento e workflow compartilham identificadores e eventos. Os pagamentos, a frota e os atendimentos externos são simulados.</p><p className="muted">Use apenas dados fictícios. Este ambiente acadêmico não acessa a Localiza.</p><div className="quick"><button onClick={() => setModule('CRM')}>Começar no CRM →</button></div></Card></div></>}

    {module === 'CRM' && <><div className="grid two"><Card title="Novo cliente"><ActionForm submit="Cadastrar cliente" onSubmit={f => act('Cliente cadastrado', () => request(endpoints.customers, 'POST', { name: field(f, 'name'), email: field(f, 'email'), eligible: true, consentService: true }))}><Input name="name" label="Nome" /><Input name="email" label="E-mail sintético" type="email" /></ActionForm></Card><Card title="Contato e oportunidade"><ActionForm submit="Adicionar contato" onSubmit={f => act('Contato adicionado', () => request(endpoints.contacts, 'POST', { customerId: field(f, 'customerId'), name: field(f, 'name'), email: field(f, 'email') }))}><Select name="customerId" label="Cliente" values={customerOptions} /><Input name="name" label="Nome do contato" /><Input name="email" label="E-mail" type="email" /></ActionForm><div className="divider" /><ActionForm submit="Criar oportunidade" onSubmit={f => act('Oportunidade criada', () => request(endpoints.opportunities, 'POST', { customerId: field(f, 'customerId'), title: field(f, 'title') }))}><Select name="customerId" label="Cliente" values={customerOptions} /><Input name="title" label="Oportunidade" /></ActionForm></Card></div><Card title="Clientes"><Table rows={data.customers} columns={[{ key: 'name', label: 'Nome' }, { key: 'email', label: 'E-mail' }, { key: 'customerId', label: 'ID', render: r => <code title={r.customerId}>{short(r.customerId)}</code> }]} /></Card><div className="grid two"><Card title="Contatos"><Table rows={data.contacts} columns={[{ key: 'name', label: 'Nome' }, { key: 'email', label: 'E-mail' }]} /></Card><Card title="Oportunidades"><Table rows={data.opportunities} columns={[{ key: 'title', label: 'Título' }, { key: 'status', label: 'Estado', render: r => status(r.status) }, { key: 'action', label: 'Ação', render: r => r.status === 'OPEN' ? <button className="inline" onClick={() => void act('Oportunidade ganha', () => request(`${endpoints.opportunities}/${r.opportunityId}`, 'PATCH', { status: 'WON' }))}>Marcar ganha</button> : '—' }]} /></Card></div></>}

    {module === 'Reservas e contratos' && <><div className="grid two"><Card title="Nova reserva"><ActionForm submit="Registrar reserva" onSubmit={f => act('Reserva registrada', () => request(endpoints.reservations, 'POST', { customerId: field(f, 'customerId'), vehicleGroup: field(f, 'vehicleGroup'), protectionCode: field(f, 'protectionCode'), serviceCode: 'RENTAL-FLEX', startsOn: field(f, 'startsOn'), endsOn: field(f, 'endsOn'), amount: Number(field(f, 'amount')), currency: 'BRL', billingCycle: 'ONCE', slaHours: 8 }))}><Select name="customerId" label="Cliente" values={customerOptions} /><Input name="vehicleGroup" label="Grupo de veículo" value="Economico" /><Input name="protectionCode" label="Proteção" value="BASICA" /><div className="form-grid"><Input name="startsOn" label="Início" type="date" /><Input name="endsOn" label="Fim" type="date" /></div><Input name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" /></ActionForm></Card><Card title="Ciclo da reserva"><p>Uma reserva vincula cliente, período, grupo e proteção. Gerar contrato cria um rascunho; ativar publica um evento para faturamento e workflow.</p><p className="muted">O ciclo da reserva é demonstrativo. Não há disponibilidade real de frota.</p></Card></div><Card title="Reservas"><Table rows={data.reservations} columns={[{ key: 'reservationId', label: 'Reserva', render: r => <code title={r.reservationId}>{short(r.reservationId)}</code> }, { key: 'vehicleGroup', label: 'Grupo' }, { key: 'startsOn', label: 'Início' }, { key: 'status', label: 'Estado', render: r => status(r.status) }, { key: 'action', label: 'Ação', render: r => !r.contractId ? <button className="inline" onClick={() => void act('Contrato gerado', () => request(`${endpoints.reservations}/${r.reservationId}/draft`, 'POST', undefined, true))}>Gerar contrato</button> : <code title={r.contractId}>{short(r.contractId)}</code> }]} /></Card><Card title="Contratos"><Table rows={data.contracts} columns={[{ key: 'contractId', label: 'Contrato', render: r => <code title={r.contractId}>{short(r.contractId)}</code> }, { key: 'serviceCode', label: 'Serviço' }, { key: 'billing', label: 'Valor', render: r => money(r.billing?.amount) }, { key: 'status', label: 'Estado', render: r => status(r.status) }, { key: 'action', label: 'Ação', render: r => r.status === 'DRAFT' ? <button className="inline" onClick={() => void act('Contrato ativado', () => request(`${endpoints.contracts}/${r.contractId}/activate`, 'POST', undefined, true))}>Ativar</button> : r.status === 'ACTIVE' ? <button className="inline quiet" onClick={() => void act('Contrato encerrado', () => request(`${endpoints.contracts}/${r.contractId}/close`, 'POST'))}>Encerrar</button> : '—' }]} /></Card></>}

    {module === 'Financeiro' && <><div className="grid two"><Card title="Registrar pagamento simulado"><ActionForm submit="Registrar pagamento" onSubmit={f => act('Pagamento registrado', () => request(`${endpoints.invoices}/${field(f, 'invoiceId')}/payments`, 'POST', { amount: Number(field(f, 'amount')), currency: 'BRL', reference: field(f, 'reference') }))}><Select name="invoiceId" label="Fatura" values={invoiceOptions} /><Input name="amount" label="Valor (R$)" type="number" min="0.01" step="0.01" /><Input name="reference" label="Referência única" value={`SIM-${Date.now()}`} /></ActionForm></Card><Card title="Como a fatura nasce"><p>Após ativar um contrato, despache o evento de integração. O consumidor financeiro cria a primeira fatura. O pagamento registrado aqui é apenas uma simulação.</p><button onClick={() => void act('Despacho de eventos', () => request('/api/v1/integration/outbox/dispatch', 'POST'))}>Despachar eventos</button></Card></div><Card title="Faturas"><Table rows={data.invoices} columns={[{ key: 'invoiceId', label: 'Fatura', render: r => <code title={r.invoiceId}>{short(r.invoiceId)}</code> }, { key: 'amount', label: 'Valor', render: r => money(r.amount) }, { key: 'paidAmount', label: 'Pago', render: r => money(r.paidAmount) }, { key: 'dueDate', label: 'Vencimento' }, { key: 'status', label: 'Estado', render: r => status(r.status) }]} /></Card></>}

    {module === 'Atendimento' && <><div className="grid two"><Card title="Abrir chamado"><ActionForm submit="Abrir chamado" onSubmit={f => act('Chamado aberto', () => request(endpoints.tickets, 'POST', { customerId: field(f, 'customerId'), contractId: field(f, 'contractId'), serviceCode: 'RENTAL-FLEX', category: field(f, 'category'), description: field(f, 'description') }, true))}><Select name="customerId" label="Cliente" values={customerOptions} /><Select name="contractId" label="Contrato ativo" values={contractOptions.filter(x => x.label.includes('ACTIVE'))} /><Select name="category" label="Categoria" values={[{ value: 'OUTAGE', label: 'Indisponibilidade' }, { value: 'QUESTION', label: 'Dúvida' }]} /><Input name="description" label="Descrição" /></ActionForm></Card><Card title="Atendimento e SLA"><p>Um contrato ativo determina a elegibilidade e o prazo do chamado. O fluxo registra prioridade, vencimento e um processo de resolução após o despacho do evento.</p><button onClick={() => void act('Despacho de eventos', () => request('/api/v1/integration/outbox/dispatch', 'POST'))}>Despachar eventos</button></Card></div><Card title="Chamados"><Table rows={data.tickets} columns={[{ key: 'ticketId', label: 'Chamado', render: r => <code title={r.ticketId}>{short(r.ticketId)}</code> }, { key: 'category', label: 'Tipo' }, { key: 'status', label: 'Estado', render: r => status(r.status) }, { key: 'priority', label: 'Prioridade' }, { key: 'dueAt', label: 'SLA até', render: r => formatDate(r.dueAt) }, { key: 'owner', label: 'Responsável' }, { key: 'action', label: 'Ação', render: r => r.status === 'OPEN' ? <button className="inline" onClick={() => void act('Chamado resolvido', () => request(`${endpoints.tickets}/${r.ticketId}/resolve`, 'POST'))}>Resolver</button> : '—' }]} /></Card><Card title="Atribuir chamado"><ActionForm submit="Atribuir" onSubmit={f => act('Chamado atribuído', () => request(`${endpoints.tickets}/${field(f, 'ticketId')}/assign`, 'POST', { owner: field(f, 'owner') }))}><Select name="ticketId" label="Chamado aberto" values={ticketOptions} /><Input name="owner" label="Responsável" value="Equipe de suporte" /></ActionForm></Card></>}

    {module === 'Workflow' && <><div className="grid two"><Card title="Gestão de tarefas"><p>Os eventos de contrato e chamado iniciam processos. Conclua tarefas ou altere o responsável para demonstrar as transições.</p><button onClick={() => void act('Despacho de eventos', () => request('/api/v1/integration/outbox/dispatch', 'POST'))}>Despachar eventos</button></Card><Card title="Criar tarefa"><ActionForm submit="Criar tarefa" onSubmit={f => act('Tarefa criada', () => request(endpoints.tasks, 'POST', { processId: field(f, 'processId'), title: field(f, 'title'), owner: field(f, 'owner') }))}><Select name="processId" label="Processo" values={data.processes.filter(x => !['COMPLETED', 'CANCELLED'].includes(x.state)).map(x => ({ value: x.processId, label: `${x.processType} · ${short(x.processId)}` }))} /><Input name="title" label="Título" /><Input name="owner" label="Responsável" value="operations" /></ActionForm></Card></div><Card title="Processos"><Table rows={data.processes} columns={[{ key: 'processType', label: 'Tipo' }, { key: 'referenceId', label: 'Referência', render: r => <code title={r.referenceId}>{short(r.referenceId)}</code> }, { key: 'state', label: 'Estado', render: r => status(r.state) }, { key: 'dueAt', label: 'Prazo', render: r => formatDate(r.dueAt) }]} /></Card><Card title="Tarefas"><Table rows={data.tasks} columns={[{ key: 'title', label: 'Título' }, { key: 'state', label: 'Estado', render: r => status(r.state) }, { key: 'owner', label: 'Responsável' }, { key: 'dueAt', label: 'Prazo', render: r => formatDate(r.dueAt) }, { key: 'action', label: 'Ação', render: r => r.state !== 'DONE' && r.state !== 'CANCELLED' ? <button className="inline" onClick={() => void act('Tarefa concluída', () => request(`${endpoints.tasks}/${r.taskId}`, 'PATCH', { state: 'DONE' }))}>Concluir</button> : '—' }]} /></Card></>}
    <footer>Demonstração acadêmica ArchCorp · Dados sintéticos · Integrações externas simuladas</footer></main>
  </div>
}
