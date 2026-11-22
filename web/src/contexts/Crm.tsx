import { useReducer, useState } from 'react'
import type { Contact, ContactUpdate, Customer, CustomerUpdate, OpportunityStatus } from '../api'
import { PHONE_INPUT_PATTERN, formatPhone, toE164 } from '../phone'
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
  const [editingContact, setEditingContact] = useState<Contact | null>(null)

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
    <PageIntro>Aqui você cadastra clientes, contatos e oportunidades. Cadastre o cliente uma vez e use o mesmo cadastro nas reservas, nos contratos e nos chamados. Para reservar um veículo, clique em Nova reserva na linha do cliente.</PageIntro>
    <FeedbackBanner feedback={feedback} onClose={clear} />

    <div className="grid two">
      <Card title="Novo cliente">
        <ActionForm submit="Cadastrar cliente" busy={busy} label="Novo cliente" onSubmit={async f => {
          const result = await run('Cadastro de cliente', () => api.createCustomer({
            name: text(f, 'name'), email: text(f, 'email'), legacyId: text(f, 'legacyId') || null,
            eligible: f.get('eligible') === 'on', consentService: f.get('consentService') === 'on',
          }), c => `Cliente ${c.name} cadastrado. Clique em Nova reserva na lista para reservar um veículo.`)
          return after(result)
        }}>
          <Field name="name" label="Nome" autoComplete="off" />
          <Field name="email" label="E-mail" type="email" placeholder="nome@example.com" autoComplete="off" />
          <Field name="legacyId" label="Código" required={false} hint="Use se o cliente já tinha um código em outro sistema, como CRM-0001." />
          <div className="checks">
            <Checkbox name="eligible" label="Elegível para contratar" />
            <Checkbox name="consentService" label="Consentimento de serviço" />
          </div>
        </ActionForm>
      </Card>

      {editing ? <Card title={`Editar cliente · ${editing.name}`}>
        <ActionForm key={editing.customerId} submit="Salvar alterações" busy={busy} label="Editar cliente" onSubmit={async f => {
          const changes: CustomerUpdate = {}
          const name = text(f, 'name'), email = text(f, 'email')
          const eligible = f.get('eligible') === 'on', consentService = f.get('consentService') === 'on'
          if (name !== editing.name) changes.name = name
          if (email !== editing.email) changes.email = email
          if (eligible !== editing.eligible) changes.eligible = eligible
          if (consentService !== editing.consentService) changes.consentService = consentService
          const result = await run('Alteração do cliente', () => api.updateCustomer(editing.customerId, changes), () => 'Dados do cliente atualizados.')
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
      </Card> : <Card title="Negociação com o cliente">
        <ActionForm submit="Criar oportunidade" busy={busy} label="Nova oportunidade" onSubmit={async f => after(await run('Criação da oportunidade',
          () => api.createOpportunity({ customerId: text(f, 'customerId'), title: text(f, 'title'), notes: text(f, 'notes') || null }),
          () => 'Oportunidade criada. Marque como Ganha ou Perdida na lista quando houver resposta do cliente.')) }>
          <CustomerPicker label="Cliente" tools={false} />
          <Field name="title" label="Título" />
          <TextArea name="notes" label="Notas" required={false} showOptional />
        </ActionForm>
      </Card>}
    </div>

    <Card title="Clientes">
      <form className="filters" aria-label="Filtrar clientes" onSubmit={e => {
        e.preventDefault()
        const f = new FormData(e.currentTarget)
        setFilters({ email: text(f, 'email'), active: text(f, 'active'), offset: 0 })
      }}>
        <Field name="email" label="E-mail" type="email" required={false} />
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
              if (window.confirm(`Inativar o cliente ${r.name}? O histórico continua guardado.`)) void run('Inativação do cliente', () => api.deactivateCustomer(r.customerId), () => 'Cliente inativado. Ele some das listas de escolha, mas o histórico continua guardado.').then(after)
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
      <Card title="Representantes comerciais">
        {editingContact ? <>
          <h3 className="subhead">Editar contato · {editingContact.name}</h3>
          <ActionForm key={editingContact.contactId} submit="Salvar contato" busy={busy} label="Editar contato" onSubmit={async f => {
            // Envia só o que mudou; telefone vazio remove o telefone (null).
            const changes: ContactUpdate = {}
            const name = text(f, 'name'), email = text(f, 'email'), phone = toE164(text(f, 'phone')) ?? null
            if (name !== editingContact.name) changes.name = name
            if (email !== editingContact.email) changes.email = email
            if (phone !== editingContact.phone) changes.phone = phone
            const result = await run('Alteração do contato', () => api.updateContact(editingContact.contactId, changes), () => 'Contato atualizado.')
            if (result) setEditingContact(null)
            return after(result)
          }}>
            <Field name="name" label="Nome do contato" defaultValue={editingContact.name} />
            <div className="form-grid">
              <Field name="email" label="E-mail" type="email" defaultValue={editingContact.email} />
              <Field name="phone" label="Telefone" type="tel" required={false} showOptional={false} placeholder="(31) 99999-0000" pattern={PHONE_INPUT_PATTERN} title="DDD e número, como (31) 99999-0000"
                defaultValue={editingContact.phone ? formatPhone(editingContact.phone) : ''} />
            </div>
          </ActionForm>
          <button type="button" className="secondary small spaced" onClick={() => setEditingContact(null)}>Cancelar edição</button>
        </> : <ActionForm submit="Adicionar contato" busy={busy} label="Novo contato" onSubmit={async f => after(await run('Inclusão do contato',
          () => api.createContact({ customerId: text(f, 'customerId'), name: text(f, 'name'), email: text(f, 'email'), phone: toE164(text(f, 'phone')) ?? null }),
          () => 'Contato adicionado.'))}>
          <CustomerPicker label="Cliente" tools={false} />
          <Field name="name" label="Nome do contato" />
          <div className="form-grid">
            <Field name="email" label="E-mail" type="email" />
            <Field name="phone" label="Telefone" type="tel" required={false} showOptional={false} placeholder="(31) 99999-0000" pattern={PHONE_INPUT_PATTERN} title="DDD e número, como (31) 99999-0000" />
          </div>
        </ActionForm>}
        <div className="divider" />
        <CustomerPicker name="contactFilter" label="Mostrar contatos de clientes" required={false} tools={false} placeholder="Todos os clientes" value={contactCustomer} onChange={setContactCustomer} />
        <ResourceView resource={contacts} label="contatos" empty="Nenhum contato cadastrado.">
          {rows => <Table caption="Contatos" rows={rows} rowKey={r => r.contactId} columns={[
            { key: 'name', label: 'Nome', render: r => r.name },
            { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
            { key: 'email', label: 'E-mail', render: r => r.email },
            { key: 'phone', label: 'Telefone', render: r => formatPhone(r.phone) },
            { key: 'actions', label: 'Ações', render: r => <div className="row-actions">
              <button type="button" className="inline" disabled={busy} onClick={() => { setEditingContact(r); clear() }}>Editar</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => {
                if (window.confirm(`Remover o contato ${r.name}?`)) void run('Remoção do contato', () => api.deleteContact(r.contactId), () => 'Contato removido.').then(after)
              }}>Remover</button>
            </div> },
          ]} />}
        </ResourceView>
      </Card>

      <Card title="Histórico de Negociação">
        <SelectField name="opportunityFilter" label="Estado" required={false} placeholder="Todos" onChange={v => setOpportunityStatus(v as '' | OpportunityStatus)}
          options={[{ value: 'OPEN', label: 'Em aberto' }, { value: 'WON', label: 'Ganha' }, { value: 'LOST', label: 'Perdida' }]} />
        <ResourceView resource={opportunities} label="oportunidades" empty="Nenhuma oportunidade neste filtro.">
          {rows => <Table caption="Oportunidades" rows={rows} rowKey={r => r.opportunityId} columns={[
            { key: 'title', label: 'Título', render: r => r.title },
            { key: 'customer', label: 'Cliente', render: r => customerName(r.customerId) },
            { key: 'status', label: 'Estado', render: r => <Status value={r.status} /> },
            { key: 'actions', label: 'Ações', render: r => r.status !== 'OPEN' ? '—' : <div className="row-actions">
              <button type="button" className="inline" disabled={busy} onClick={() => void run('Oportunidade ganha', () => api.updateOpportunity(r.opportunityId, { status: 'WON' }), () => 'Oportunidade marcada como ganha.').then(after)}>Ganha</button>
              <button type="button" className="inline quiet" disabled={busy} onClick={() => void run('Oportunidade perdida', () => api.updateOpportunity(r.opportunityId, { status: 'LOST' }), () => 'Oportunidade marcada como perdida.').then(after)}>Perdida</button>
            </div> },
          ]} />}
        </ResourceView>
      </Card>
    </div>
  </>
}
