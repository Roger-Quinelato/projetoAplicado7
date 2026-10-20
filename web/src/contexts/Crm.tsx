import { useReducer, useState } from 'react'
import type { Customer, CustomerUpdate, OpportunityStatus } from '../api'
import {
  ActionForm, Card, Checkbox, CustomerPicker, Field, FeedbackBanner, Id, PageIntro, ResourceView, SelectField, Status, Table, TextArea,
  text, useActions, useResource, useSession,
} from '../ui'

const PAGE_SIZE = 10

export default function Crm() {
  const { api, navigate } = useSession()
  const { feedback, busy, run, clear } = useActions()
  const [version, refresh] = useReducer((x: number) => x + 1, 0)
  const [filters, setFilters] = useState<{ email: string, active: string, offset: number }>({ email: '', active: 'true', offset: 0 })
  const [contactCustomer, setContactCustomer] = useState('')
  const [opportunityStatus, setOpportunityStatus] = useState<'' | OpportunityStatus>('')
  const [editing, setEditing] = useState<Customer | null>(null)

  const customers = useResource(api => api.listCustomers({
    email: filters.email || undefined, active: filters.active === '' ? undefined : filters.active === 'true',
    limit: PAGE_SIZE, offset: filters.offset,
  }), [filters, version])
  const activeCustomers = useResource(api => api.listCustomers({ active: true }), [version])
  const contacts = useResource(api => api.listContacts(contactCustomer || undefined), [contactCustomer, version])
  const opportunities = useResource(api => api.listOpportunities({ status: opportunityStatus || undefined }), [opportunityStatus, version])

  const customerName = (id: string) => activeCustomers.data?.find(c => c.customerId === id)?.name ?? id.slice(0, 8)

  async function after<T>(result: T | null): Promise<boolean> {
    if (result) refresh()
    return result !== null
  }

  return <>
    <PageIntro>Cliente, contatos, consentimentos e oportunidades têm o CRM como fonte oficial. Os demais contextos reutilizam o <code>customerId</code> sem recadastro.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Novo cliente" roles="commercial, admin">
        <ActionForm submit="Cadastrar cliente" busy={busy} label="Novo cliente" onSubmit={async f => {
          const result = await run('Cadastro de cliente', () => api.createCustomer({
            name: text(f, 'name'), email: text(f, 'email'), legacyId: text(f, 'legacyId') || null,
            eligible: f.get('eligible') === 'on', consentService: f.get('consentService') === 'on',
          }), c => `Cliente ${c.name} (${c.customerId.slice(0, 8)}).`)
          return after(result)
        }}>
          <Field name="name" label="Nome (fictício)" autoComplete="off" />
          <Field name="email" label="E-mail sintético" type="email" placeholder="nome@example.com" autoComplete="off" />
          <Field name="legacyId" label="ID legado no CRM" required={false} hint="Ex.: CRM-0001. Fica mapeado ao UUID global." />
          <div className="checks">
            <Checkbox name="eligible" label="Elegível para contratar" />
            <Checkbox name="consentService" label="Consentimento de serviço" />
          </div>
        </ActionForm>
      </Card>

      {editing ? <Card title={`Editar cliente · ${editing.name}`} roles="commercial, admin">
        <ActionForm key={editing.customerId} submit="Salvar alterações" busy={busy} label="Editar cliente" onSubmit={async f => {
          const changes: CustomerUpdate = {}
          const name = text(f, 'name'), email = text(f, 'email')
          const eligible = f.get('eligible') === 'on', consentService = f.get('consentService') === 'on'
          if (name !== editing.name) changes.name = name
          if (email !== editing.email) changes.email = email
          if (eligible !== editing.eligible) changes.eligible = eligible
          if (consentService !== editing.consentService) changes.consentService = consentService
          const result = await run('Alteração de cliente', () => api.updateCustomer(editing.customerId, changes))
          if (result) setEditing(null)
          return after(result)
        }}>
          <Field name="name" label="Nome" defaultValue={editing.name} />
          <Field name="email" label="E-mail" type="email" defaultValue={editing.email} />
          <div className="checks">
            <Checkbox name="eligible" label="Elegível para contratar" defaultChecked={editing.eligible} />
            <Checkbox name="consentService" label="Consentimento de serviço" defaultChecked={editing.consentService} />
          </div>
        </ActionForm>
        <button type="button" className="secondary small spaced" onClick={() => setEditing(null)}>Cancelar edição</button>
      </Card> : <Card title="Oportunidade" roles="commercial, admin">
        <ActionForm submit="Criar oportunidade" busy={busy} label="Nova oportunidade" onSubmit={async f => after(await run('Criação de oportunidade',
          () => api.createOpportunity({ customerId: text(f, 'customerId'), title: text(f, 'title'), notes: text(f, 'notes') || null }))) }>
          <CustomerPicker label="Cliente" />
          <Field name="title" label="Título" />
          <TextArea name="notes" label="Notas" required={false} />
        </ActionForm>
      </Card>}
    </div>

    <Card title="Clientes" roles="leitura: commercial, contracts, support, admin">
      <form className="filters" aria-label="Filtrar clientes" onSubmit={e => {
        e.preventDefault()
        const f = new FormData(e.currentTarget)
        setFilters({ email: text(f, 'email'), active: text(f, 'active'), offset: 0 })
      }}>
        <Field name="email" label="E-mail exato" type="email" required={false} />
        <SelectField name="active" label="Situação" required={false} placeholder="Todos" defaultValue="true"
          options={[{ value: 'true', label: 'Ativos' }, { value: 'false', label: 'Inativos' }]} />
        <button type="submit" className="secondary">Filtrar</button>
      </form>
      <ResourceView resource={customers} label="clientes" empty="Nenhum cliente encontrado com esses filtros. Cadastre um cliente fictício acima.">
        {rows => <Table caption="Clientes" rows={rows} rowKey={r => r.customerId} columns={[
          { key: 'name', label: 'Nome', render: r => r.name },
          { key: 'email', label: 'E-mail', render: r => r.email },
          { key: 'active', label: 'Situação', render: r => <Status value={r.active === false ? 'CANCELLED' : 'ACTIVE'} /> },
          { key: 'eligible', label: 'Elegível', render: r => r.eligible ? 'Sim' : 'Não' },
          { key: 'consent', label: 'Consentimento', render: r => r.consentService ? 'Sim' : 'Não' },
          { key: 'legacy', label: 'ID legado', render: r => r.legacyId ?? '—' },
          { key: 'id', label: 'ID', render: r => <Id value={r.customerId} /> },
          { key: 'actions', label: 'Ações', render: r => r.active === false ? '—' : <div className="row-actions">
            <button type="button" className="inline" disabled={busy} onClick={() => { setEditing(r); clear() }}>Editar</button>
            <button type="button" className="inline" onClick={() => navigate(`/reservas?customer=${r.customerId}`)}>Nova reserva</button>
            <button type="button" className="inline quiet" disabled={busy} onClick={() => {
              if (window.confirm(`Inativar o cliente ${r.name}? O histórico é preservado.`)) void run('Inativação de cliente', () => api.deactivateCustomer(r.customerId)).then(after)
            }}>Inativar</button>
          </div> },
        ]} />}
      </ResourceView>
      <nav className="pager" aria-label="Paginação de clientes">
        <button type="button" className="secondary small" disabled={filters.offset === 0} onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, f.offset - PAGE_SIZE) }))}>Anterior</button>
        <span>Página {filters.offset / PAGE_SIZE + 1}</span>
        <button type="button" className="secondary small" disabled={(customers.data?.length ?? 0) < PAGE_SIZE} onClick={() => setFilters(f => ({ ...f, offset: f.offset + PAGE_SIZE }))}>Próxima</button>
      </nav>
    </Card>

    <div className="grid two">
      <Card title="Contatos" roles="commercial, admin">
        <ActionForm submit="Adicionar contato" busy={busy} label="Novo contato" onSubmit={async f => after(await run('Inclusão de contato',
          () => api.createContact({ customerId: text(f, 'customerId'), name: text(f, 'name'), email: text(f, 'email'), phone: text(f, 'phone') || null })))}>
          <CustomerPicker label="Cliente" />
          <Field name="name" label="Nome do contato" />
          <div className="form-grid">
            <Field name="email" label="E-mail" type="email" />
            <Field name="phone" label="Telefone" type="tel" required={false} hint="Formato E.164, ex.: +5531999990000" />
          </div>
        </ActionForm>
        <div className="divider" />
        <CustomerPicker name="contactFilter" label="Mostrar contatos de" required={false} placeholder="Todos os clientes" value={contactCustomer} onChange={setContactCustomer} />
        <ResourceView resource={contacts} label="contatos" empty="Nenhum contato cadastrado.">
          {rows => <Table caption="Contatos" rows={rows} rowKey={r => r.contactId} columns={[
            { key: 'name', label: 'Nome', render: r => r.name },
            { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
            { key: 'email', label: 'E-mail', render: r => r.email },
            { key: 'phone', label: 'Telefone', render: r => r.phone ?? '—' },
            { key: 'actions', label: 'Ações', render: r => <button type="button" className="inline quiet" disabled={busy} onClick={() => {
              if (window.confirm(`Remover o contato ${r.name}?`)) void run('Remoção de contato', () => api.deleteContact(r.contactId)).then(after)
            }}>Remover</button> },
          ]} />}
        </ResourceView>
      </Card>

      <Card title="Oportunidades" roles="commercial, admin">
        <SelectField name="opportunityFilter" label="Estado" required={false} placeholder="Todos" onChange={v => setOpportunityStatus(v as '' | OpportunityStatus)}
          options={[{ value: 'OPEN', label: 'Em aberto' }, { value: 'WON', label: 'Ganha' }, { value: 'LOST', label: 'Perdida' }]} />
        <ResourceView resource={opportunities} label="oportunidades" empty="Nenhuma oportunidade neste filtro.">
          {rows => <Table caption="Oportunidades" rows={rows} rowKey={r => r.opportunityId} columns={[
            { key: 'title', label: 'Título', render: r => r.title },
            { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
            { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
            { key: 'actions', label: 'Ações', render: r => r.status !== 'OPEN' ? '—' : <div className="row-actions">
              <button type="button" className="inline" disabled={busy} onClick={() => void run('Oportunidade ganha', () => api.updateOpportunity(r.opportunityId, { status: 'WON' })).then(after)}>Ganha</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => void run('Oportunidade perdida', () => api.updateOpportunity(r.opportunityId, { status: 'LOST' })).then(after)}>Perdida</button>
            </div> },
          ]} />}
        </ResourceView>
      </Card>
    </div>
  </>
}
