import { useReducer, useState } from 'react'
import type { Customer, CustomerUpdate, OpportunityStatus } from '../api'
import {
  ActionForm, Card, Checkbox, Field, FeedbackBanner, Id, MoreMenu, PageIntro, Panel, ResourceView, SelectField, Stack, Status, Table, TextArea,
  text, useActions, useConfirm, useResource, useSession,
} from '../ui'

const PAGE_SIZE = 10

type CustomerPanel = { kind: 'new' } | { kind: 'edit', customer: Customer } | null

export default function Crm() {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const { ask, dialog } = useConfirm()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [filters, setFilters] = useState<{ email: string, active: string, offset: number }>({ email: '', active: 'true', offset: 0 })
  const [contactCustomer, setContactCustomer] = useState('')
  const [opportunityStatus, setOpportunityStatus] = useState<'' | OpportunityStatus>('')
  const [panel, setPanel] = useState<CustomerPanel>(null)
  const [contactForm, setContactForm] = useState(false)
  const [opportunityForm, setOpportunityForm] = useState(false)

  const customers = useResource(api => api.listCustomers({
    email: filters.email || undefined, active: filters.active === '' ? undefined : filters.active === 'true',
    limit: PAGE_SIZE, offset: filters.offset,
  }), [filters, version])
  const activeCustomers = useResource(api => api.listCustomers({ active: true }), [version])
  const contacts = useResource(api => api.listContacts(contactCustomer || undefined), [contactCustomer, version])
  const opportunities = useResource(api => api.listOpportunities({ status: opportunityStatus || undefined }), [opportunityStatus, version])

  const customerOptions = (activeCustomers.data ?? []).map(c => ({ value: c.customerId, label: `${c.name} · ${c.email}` }))
  const customerName = (id: string) => activeCustomers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  async function after<T>(result: T | null): Promise<boolean> {
    if (result) refresh()
    return result !== null
  }

  async function deactivate(customer: Customer) {
    const ok = await ask({ title: `Inativar ${customer.name}?`, body: 'O cliente deixa de aparecer para novas reservas e chamados. O histórico fica preservado.', confirm: 'Inativar cliente', cancel: 'Manter ativo' })
    if (ok) await after(await run('Inativação de cliente', () => api.deactivateCustomer(customer.customerId), undefined,
      { success: () => `Cliente ${customer.name} inativado.`, failure: 'Não foi possível inativar o cliente.' }))
  }

  async function removeContact(id: string, name: string) {
    const ok = await ask({ title: `Remover o contato ${name}?`, body: 'O contato sai da lista do cliente. Esta ação não pode ser desfeita.', confirm: 'Remover contato', cancel: 'Manter contato' })
    if (ok) await after(await run('Remoção de contato', () => api.deleteContact(id), undefined,
      { success: () => `Contato ${name} removido.`, failure: 'Não foi possível remover o contato.' }))
  }

  return <>
    <PageIntro>O CRM é a fonte oficial de clientes, contatos e oportunidades. Os outros contextos usam o mesmo cliente, sem recadastro.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />
    {dialog}

    <Card title="Clientes" aside={<div className="head-actions">
      <button type="button" onClick={() => { setPanel({ kind: 'new' }); clear() }}>Novo cliente</button>
    </div>}>
      <form className="filters" aria-label="Filtrar clientes" onSubmit={e => {
        e.preventDefault()
        const f = new FormData(e.currentTarget)
        setFilters({ email: text(f, 'email'), active: text(f, 'active'), offset: 0 })
      }}>
        <Field name="email" label="E-mail exato" type="email" required={false} placeholder="nome@example.com" />
        <SelectField name="active" label="Situação" required={false} placeholder="Todos" defaultValue="true"
          options={[{ value: 'true', label: 'Ativos' }, { value: 'false', label: 'Inativos' }]} />
        <button type="submit" className="secondary">Filtrar</button>
      </form>
      <ResourceView resource={customers} label="clientes" empty="Nenhum cliente encontrado com esses filtros. Use “Novo cliente” para cadastrar um cliente fictício.">
        {rows => <Table caption="Clientes" rows={rows} rowKey={r => r.customerId} columns={[
          { key: 'name', label: 'Cliente', render: r => <Stack main={r.name} sub={r.email} /> },
          { key: 'active', label: 'Situação', render: r => r.active === false ? <span className="status neutral">Inativo</span> : <Status value="ACTIVE" /> },
          { key: 'eligible', label: 'Elegível', render: r => r.eligible ? 'Sim' : 'Não' },
          { key: 'consent', label: 'Consentimento', render: r => r.consentService ? 'Sim' : 'Não' },
          { key: 'legacy', label: 'ID legado', render: r => r.legacyId ?? '—' },
          { key: 'id', label: 'ID', render: r => <Id value={r.customerId} /> },
          { key: 'actions', label: 'Ações', render: r => r.active === false ? '—' : <div className="row-actions">
            <button type="button" className="inline" onClick={() => navigate(`/reservas?customer=${r.customerId}`)}>Nova reserva</button>
            <MoreMenu label={r.name} items={[
              { label: 'Editar', disabled: busy, onSelect: () => { setPanel({ kind: 'edit', customer: r }); clear() } },
              { label: 'Inativar…', danger: true, disabled: busy, onSelect: () => void deactivate(r) },
            ]} />
          </div> },
        ]} />}
      </ResourceView>
      <nav className="pager" aria-label="Paginação de clientes">
        <button type="button" className="secondary small" disabled={filters.offset === 0} onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, f.offset - PAGE_SIZE) }))}>Anterior</button>
        <span>Página {filters.offset / PAGE_SIZE + 1}</span>
        <button type="button" className="secondary small" disabled={(customers.data?.length ?? 0) < PAGE_SIZE} onClick={() => setFilters(f => ({ ...f, offset: f.offset + PAGE_SIZE }))}>Próxima</button>
      </nav>
    </Card>

    {panel && <div className="grid two">
      {panel.kind === 'new' ? <Panel title="Novo cliente" onClose={() => setPanel(null)}>
        <ActionForm submit="Cadastrar cliente" busy={busy} label="Novo cliente" onSubmit={async f => {
          const name = text(f, 'name')
          const result = await run('Cadastro de cliente', () => api.createCustomer({
            name, email: text(f, 'email'), legacyId: text(f, 'legacyId') || null,
            eligible: f.get('eligible') === 'on', consentService: f.get('consentService') === 'on',
          }), undefined, { success: c => `Cliente ${c.name} cadastrado.`, failure: 'Não foi possível cadastrar o cliente.' })
          return after(result)
        }}>
          <div className="form-grid">
            <Field name="name" label="Nome (fictício)" autoComplete="off" />
            <Field name="email" label="E-mail sintético" type="email" placeholder="nome@example.com" autoComplete="off" />
          </div>
          <Field name="legacyId" label="ID legado no CRM" required={false} hint="Ex.: CRM-0001. Fica ligado ao ID global do cliente." />
          <div className="checks">
            <Checkbox name="eligible" label="Elegível para contratar" />
            <Checkbox name="consentService" label="Consentimento de serviço" />
          </div>
        </ActionForm>
      </Panel> : <Panel title={`Editar cliente · ${panel.customer.name}`} onClose={() => setPanel(null)}>
        <ActionForm key={panel.customer.customerId} submit="Salvar alterações" busy={busy} label="Editar cliente" onSubmit={async f => {
          const editing = panel.customer
          const changes: CustomerUpdate = {}
          const name = text(f, 'name'), email = text(f, 'email')
          const eligible = f.get('eligible') === 'on', consentService = f.get('consentService') === 'on'
          if (name !== editing.name) changes.name = name
          if (email !== editing.email) changes.email = email
          if (eligible !== editing.eligible) changes.eligible = eligible
          if (consentService !== editing.consentService) changes.consentService = consentService
          const result = await run('Alteração de cliente', () => api.updateCustomer(editing.customerId, changes), undefined,
            { success: c => `Cliente ${c.name} atualizado.`, failure: 'Não foi possível salvar as alterações do cliente.' })
          if (result) setPanel(null)
          return after(result)
        }}>
          <div className="form-grid">
            <Field name="name" label="Nome" defaultValue={panel.customer.name} />
            <Field name="email" label="E-mail" type="email" defaultValue={panel.customer.email} />
          </div>
          <div className="checks">
            <Checkbox name="eligible" label="Elegível para contratar" defaultChecked={panel.customer.eligible} />
            <Checkbox name="consentService" label="Consentimento de serviço" defaultChecked={panel.customer.consentService} />
          </div>
        </ActionForm>
      </Panel>}
      <Card title="Depois do cadastro">
        <ol className="flow-steps">
          <li><span>Use “Nova reserva” na linha do cliente para abrir Reservas e contratos com ele já escolhido.</span></li>
          <li><span>Contatos e oportunidades, abaixo, usam o mesmo cliente.</span></li>
          <li><span>“Mais” reúne Editar e Inativar. Inativar pede confirmação e preserva o histórico.</span></li>
        </ol>
      </Card>
    </div>}

    <div className="grid two">
      <Card title="Contatos" aside={<div className="head-actions">
        <button type="button" onClick={() => setContactForm(v => !v)} aria-expanded={contactForm}>Adicionar contato</button>
      </div>}>
        {contactForm && <>
          <ActionForm submit="Salvar contato" busy={busy} label="Novo contato" onSubmit={async f => {
            const name = text(f, 'name')
            const ok = await after(await run('Inclusão de contato',
              () => api.createContact({ customerId: text(f, 'customerId'), name, email: text(f, 'email'), phone: text(f, 'phone') || null }), undefined,
              { success: () => `Contato ${name} adicionado.`, failure: 'Não foi possível adicionar o contato.' }))
            if (ok) setContactForm(false)
            return ok
          }}>
            <SelectField name="customerId" label="Cliente" options={customerOptions} />
            <Field name="name" label="Nome do contato" />
            <div className="form-grid">
              <Field name="email" label="E-mail" type="email" />
              <Field name="phone" label="Telefone" type="tel" required={false} hint="Formato E.164, ex.: +5531999990000" />
            </div>
          </ActionForm>
          <div className="divider" />
        </>}
        <SelectField name="contactFilter" label="Mostrar contatos de" required={false} placeholder="Todos os clientes" options={customerOptions} onChange={setContactCustomer} />
        <ResourceView resource={contacts} label="contatos" empty="Nenhum contato cadastrado. Use “Adicionar contato”.">
          {rows => <Table caption="Contatos" rows={rows} rowKey={r => r.contactId} columns={[
            { key: 'name', label: 'Contato', render: r => <Stack main={r.name} sub={[r.email, r.phone].filter(Boolean).join(' · ')} /> },
            { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
            { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline danger" disabled={busy}
              onClick={() => void removeContact(r.contactId, r.name)}>Remover</button> },
          ]} />}
        </ResourceView>
      </Card>

      <Card title="Oportunidades" aside={<div className="head-actions">
        <button type="button" onClick={() => setOpportunityForm(v => !v)} aria-expanded={opportunityForm}>Nova oportunidade</button>
      </div>}>
        {opportunityForm && <>
          <ActionForm submit="Criar oportunidade" busy={busy} label="Nova oportunidade" onSubmit={async f => {
            const title = text(f, 'title')
            const ok = await after(await run('Criação de oportunidade',
              () => api.createOpportunity({ customerId: text(f, 'customerId'), title, notes: text(f, 'notes') || null }), undefined,
              { success: () => `Oportunidade “${title}” criada.`, failure: 'Não foi possível criar a oportunidade.' }))
            if (ok) setOpportunityForm(false)
            return ok
          }}>
            <SelectField name="customerId" label="Cliente" options={customerOptions} placeholder={activeCustomers.status === 'loading' ? 'Carregando…' : 'Selecione'} />
            <Field name="title" label="Título" />
            <TextArea name="notes" label="Notas" required={false} />
          </ActionForm>
          <div className="divider" />
        </>}
        <SelectField name="opportunityFilter" label="Estado" required={false} placeholder="Todos" onChange={v => setOpportunityStatus(v as '' | OpportunityStatus)}
          options={[{ value: 'OPEN', label: 'Em aberto' }, { value: 'WON', label: 'Ganha' }, { value: 'LOST', label: 'Perdida' }]} />
        <ResourceView resource={opportunities} label="oportunidades" empty="Nenhuma oportunidade neste filtro.">
          {rows => <Table caption="Oportunidades" rows={rows} rowKey={r => r.opportunityId} columns={[
            { key: 'title', label: 'Oportunidade', render: r => <Stack main={r.title} sub={customerName(r.customerId)} /> },
            { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
            { key: 'actions', label: 'Ações', render: r => r.status !== 'OPEN' ? '—' : <div className="row-actions">
              <button type="button" className="inline" disabled={busy} onClick={() => void run('Oportunidade ganha', () => api.updateOpportunity(r.opportunityId, { status: 'WON' }), undefined,
                { success: () => `Oportunidade “${r.title}” marcada como ganha.`, failure: 'Não foi possível atualizar a oportunidade.' }).then(after)}>Ganha</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => void run('Oportunidade perdida', () => api.updateOpportunity(r.opportunityId, { status: 'LOST' }), undefined,
                { success: () => `Oportunidade “${r.title}” marcada como perdida.`, failure: 'Não foi possível atualizar a oportunidade.' }).then(after)}>Perdida</button>
            </div> },
          ]} />}
        </ResourceView>
      </Card>
    </div>
  </>
}
