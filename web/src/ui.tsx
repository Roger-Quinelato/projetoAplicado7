import { createContext, useCallback, useContext, useEffect, useId, useReducer, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, asApiError, describeIssue, errorHeadline, type Api, type ApiResult, type Customer } from './api'
import { IdempotentIntents, isAmbiguous } from './intents'

// ---------- Sessão compartilhada ----------

export interface Session {
  api: Api
  /** Volta à tela de credencial (usado em respostas 401). */
  signOut: () => void
  navigate: (route: string) => void
  /** Muda após cada despacho; as consultas de todas as telas recarregam quando ela muda. */
  dataVersion: number
  /** Muda após cada comando concluído; a barra de eventos reconsulta a outbox quando ela muda. */
  eventsVersion: number
  dispatched: () => void
  commandDone: () => void
}

export const SessionContext = createContext<Session | null>(null)

export function useSession(): Session {
  const session = useContext(SessionContext)
  if (!session) throw new Error('SessionContext ausente')
  return session
}

// ---------- Formatação ----------

export function shortId(value: string | null | undefined): string {
  return value ? value.slice(0, 8) : '—'
}
export function money(value: unknown, currency = 'BRL'): string {
  const number = Number(value ?? 0)
  try { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(number) }
  catch { return `${currency} ${number.toFixed(2)}` }
}
export function dateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}
export function date(value: string | null | undefined): string {
  if (!value) return '—'
  const [y, m, d] = value.split('-')
  return d && m && y ? `${d}/${m}/${y}` : value
}
export function isoDate(offsetDays = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
export function text(form: FormData, name: string): string {
  return String(form.get(name) ?? '').trim()
}

const STATUS_LABELS: Record<string, [string, 'good' | 'bad' | 'warn' | 'neutral']> = {
  OPEN: ['Em aberto', 'warn'], WON: ['Ganha', 'good'], LOST: ['Perdida', 'bad'],
  REQUESTED: ['Solicitada', 'warn'], DRAFTED: ['Com rascunho', 'neutral'], DRAFT: ['Rascunho', 'neutral'],
  ACTIVE: ['Ativo', 'good'], CLOSED: ['Encerrado', 'neutral'], CANCELLED: ['Cancelado', 'bad'],
  PAID: ['Paga', 'good'], OVERDUE: ['Vencida', 'bad'], PARTIALLY_PAID: ['Parcialmente paga', 'warn'],
  PENDING_ENTITLEMENT: ['Elegibilidade pendente', 'warn'], REJECTED_ENTITLEMENT: ['Sem elegibilidade', 'bad'],
  RESOLVED: ['Resolvido', 'good'], IN_PROGRESS: ['Em andamento', 'warn'], DONE: ['Concluída', 'good'],
  STARTED: ['Iniciado', 'warn'], COMPLETED: ['Concluído', 'good'], HIGH: ['Alta', 'bad'], NORMAL: ['Normal', 'neutral'],
  PENDING: ['Pendente', 'warn'], PUBLISHED: ['Publicado', 'good'], FAILED: ['Falhou', 'bad'],
}
export function Status({ value }: { value: string | null | undefined }) {
  if (!value) return <>—</>
  const [label, tone] = STATUS_LABELS[value] ?? [value, 'neutral']
  return <span className={`status ${tone}`} title={value}>{label}</span>
}

export function Id({ value }: { value: string | null | undefined }) {
  if (!value) return <>—</>
  return <code title={value} aria-label={`Identificador ${value}`}>{shortId(value)}</code>
}

// ---------- Recursos (consultas) ----------

export type Resource<T> =
  | { status: 'loading', data?: T, error?: undefined, reload: () => Promise<void> }
  | { status: 'success', data: T, error?: undefined, reload: () => Promise<void> }
  | { status: 'error', data?: T, error: ApiError, reload: () => Promise<void> }

/** Carrega um recurso da API com estados explícitos de carregamento, sucesso e erro. */
export function useResource<T>(load: (api: Api) => Promise<ApiResult<T>>, deps: unknown[]): Resource<T> {
  const { api, dataVersion } = useSession()
  const [state, setState] = useState<{ status: 'loading' | 'success' | 'error', data?: T, error?: ApiError }>({ status: 'loading' })
  const sequence = useRef(0)
  const loader = useRef(load)
  loader.current = load

  const reload = useCallback(async () => {
    const current = ++sequence.current
    setState(previous => ({ status: 'loading', data: previous.data }))
    try {
      const result = await loader.current(api)
      if (current === sequence.current) setState({ status: 'success', data: result.data })
    } catch (error) {
      if (current === sequence.current) setState(previous => ({ status: 'error', data: previous.data, error: asApiError(error) }))
    }
  }, [api])

  useEffect(() => { void reload() }, [reload, dataVersion, ...deps])
  return { ...state, reload } as Resource<T>
}

/** Renderiza carregando, erro, vazio ou conteúdo de um recurso. */
export function ResourceView<T>({ resource, label, isEmpty, empty, children }: {
  resource: Resource<T>
  label: string
  isEmpty?: (data: T) => boolean
  empty: ReactNode
  children: (data: T) => ReactNode
}) {
  if (resource.status === 'error') {
    return <ErrorPanel error={resource.error} context={`Falha ao carregar ${label}.`} onRetry={() => void resource.reload()} />
  }
  if (resource.data === undefined) {
    return <p className="loading" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />Carregando {label}…</p>
  }
  const emptyNow = isEmpty ? isEmpty(resource.data) : Array.isArray(resource.data) && resource.data.length === 0
  return <div aria-busy={resource.status === 'loading'}>
    {resource.status === 'loading' && <p className="refreshing" role="status">Atualizando…</p>}
    {emptyNow ? <p className="empty">{empty}</p> : children(resource.data)}
  </div>
}

// ---------- Ações (comandos) ----------

export type Feedback =
  | { kind: 'success', message: string, correlationId: string, replayed: boolean | null }
  /** HTTP 2xx cujo corpo relata falha parcial (ex.: despacho com `failed > 0`): nunca exibido como sucesso integral. */
  | { kind: 'warning', message: string, correlationId: string }
  | { kind: 'error', message: string, error: ApiError }

/**
 * Executa comandos com estado de envio e feedback legível de sucesso ou erro. `partial`, quando
 * informado, examina o corpo da resposta: verdadeiro rebaixa o aviso de sucesso a resultado parcial.
 */
export function useActions() {
  const { commandDone } = useSession()
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [busy, setBusy] = useState(false)

  const run = useCallback(async <T,>(label: string, action: () => Promise<ApiResult<T>>, describe?: (data: T) => string,
    partial?: (data: T) => boolean): Promise<ApiResult<T> | null> => {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await action()
      const suffix = describe ? ` ${describe(result.data)}` : ''
      if (partial?.(result.data)) setFeedback({ kind: 'warning', message: `${label}: concluído com falhas.${suffix}`, correlationId: result.correlationId })
      else setFeedback({ kind: 'success', message: `${label}: concluído.${suffix}`, correlationId: result.correlationId, replayed: result.replayed })
      commandDone()
      return result
    } catch (error) {
      const message = isAmbiguous(error) ? `${label}: não foi possível confirmar; a operação pode ter sido registrada.` : `${label}: não concluído.`
      setFeedback({ kind: 'error', message, error: asApiError(error) })
      return null
    } finally {
      setBusy(false)
    }
  }, [commandDone])

  return { feedback, busy, run, clear: () => setFeedback(null) }
}

/**
 * Chaves de idempotência por intenção e corpo, com intenções pendentes após falha ambígua
 * (regras em `intents.ts`). O componente é renderizado de novo quando a lista de pendências muda.
 */
export function useIdempotencyKeys() {
  const [, rerender] = useReducer((x: number) => x + 1, 0)
  const intents = useRef<IdempotentIntents | null>(null)
  if (!intents.current) intents.current = new IdempotentIntents(rerender)
  return intents.current
}

/**
 * Pedidos sem confirmação: o usuário consulta os registros e então repete o pedido original
 * (mesmo corpo e mesma chave) ou o descarta explicitamente.
 */
export function PendingIntents({ keys, busy, run, onCheck }: {
  keys: IdempotentIntents
  busy: boolean
  run: <T>(label: string, action: () => Promise<ApiResult<T>>) => Promise<ApiResult<T> | null>
  onCheck: () => void
}) {
  const pending = keys.pending()
  if (pending.length === 0) return null
  return <div className="pending-region">
    {pending.map(p => <div key={p.intent} className="notice warn" role="status" aria-label={`Pedido sem confirmação: ${p.label}`}>
      <div>
        <strong>{p.label}: não foi possível confirmar; a operação pode ter sido registrada.</strong>
        <p>O pedido original está preservado com os mesmos dados e a mesma chave de idempotência. Consulte os registros antes de decidir: repetir o pedido original não duplica o registro; dados diferentes só podem ser enviados depois de descartar este pedido.</p>
        <p className="meta">Chave: <code title={p.key}>{p.key.slice(0, 8)}</code>{p.correlationId && <> · Correlação: <code>{p.correlationId}</code></>}</p>
        <div className="notice-actions">
          <button type="button" className="secondary small" disabled={busy} onClick={onCheck}>Consultar registros</button>
          <button type="button" className="secondary small" disabled={busy} onClick={() => void run(p.label, () => keys.retry(p.intent)).then(r => { if (r) onCheck() })}>Repetir pedido original</button>
          <button type="button" className="secondary small" disabled={busy} onClick={() => {
            if (window.confirm('Descarte somente depois de confirmar nos registros que o pedido não foi gravado. Um novo envio usará outra chave e pode duplicar o registro se o original tiver sido gravado.')) keys.discard(p.intent)
          }}>Descartar pedido</button>
        </div>
      </div>
    </div>)}
  </div>
}

export function FeedbackBanner({ feedback, onClose }: { feedback: Feedback | null, onClose: () => void }) {
  return <div className="feedback-region" aria-live="polite">
    {feedback?.kind === 'success' && <div className="notice success" role="status">
      <div>
        <strong>{feedback.message}</strong>
        <p className="meta">
          {feedback.replayed === true && <span className="tag">Repetição idempotente: resposta original reaproveitada</span>}
          Correlação: <code>{feedback.correlationId}</code>
        </p>
      </div>
      <button type="button" className="close" aria-label="Fechar aviso" onClick={onClose}>×</button>
    </div>}
    {feedback?.kind === 'warning' && <div className="notice warn" role="alert">
      <div>
        <strong>{feedback.message}</strong>
        <p className="meta">Correlação: <code>{feedback.correlationId}</code></p>
      </div>
      <button type="button" className="close" aria-label="Fechar aviso" onClick={onClose}>×</button>
    </div>}
    {feedback?.kind === 'error' && <ErrorPanel error={feedback.error} context={feedback.message} onClose={onClose} />}
  </div>
}

export function ErrorPanel({ error, context, onRetry, onClose }: { error: ApiError, context?: string, onRetry?: () => void, onClose?: () => void }) {
  const { signOut } = useSession()
  const detail = error.detail && error.issues.length === 0 ? error.detail : ''
  return <div className="notice error" role="alert">
    <div>
      {context && <strong>{context} </strong>}
      <strong>{errorHeadline(error)}</strong>
      {detail && <p>{detail}</p>}
      {error.issues.length > 0 && <ul className="issues">{error.issues.map((issue, i) => <li key={i}>{describeIssue(issue)}</li>)}</ul>}
      <p className="meta">
        {error.kind === 'network' ? 'Sem resposta do servidor' : error.status === 0 ? <>Verificação no navegador · código <code>{error.code}</code></> : <>HTTP {error.status} · código <code>{error.code}</code></>}
        {error.correlationId && <> · Correlação: <code>{error.correlationId}</code></>}
      </p>
      <div className="notice-actions">
        {error.status === 401 && <button type="button" className="secondary small" onClick={signOut}>Trocar credencial</button>}
        {onRetry && <button type="button" className="secondary small" onClick={onRetry}>Tentar novamente</button>}
      </div>
    </div>
    {onClose && <button type="button" className="close" aria-label="Fechar aviso" onClick={onClose}>×</button>}
  </div>
}

// ---------- Layout e formulários ----------

/** `id`, quando informado, torna o cartão um destino de link que pode receber o foco. */
export function Card({ title, roles, children, aside, className, id }: { title: string, roles?: string, children: ReactNode, aside?: ReactNode, className?: string, id?: string }) {
  const headingId = useId()
  return <section id={id} tabIndex={id ? -1 : undefined} className={`card ${className ?? ''}`} aria-labelledby={headingId}>
    <div className="card-head">
      <div><h2 id={headingId}>{title}</h2>{roles && <p className="roles">Papéis: {roles}</p>}</div>
      {aside}
    </div>
    {children}
  </section>
}

export function Field({ name, label, type = 'text', required = true, defaultValue, hint, ...rest }: {
  name: string, label: string, type?: string, required?: boolean, defaultValue?: string, hint?: string,
  min?: string, step?: string, placeholder?: string, autoComplete?: string,
}) {
  const id = useId()
  return <div className="field">
    <label htmlFor={id}>{label}{!required && <span className="optional"> (opcional)</span>}</label>
    <input id={id} name={name} type={type} required={required} defaultValue={defaultValue} aria-describedby={hint ? `${id}-hint` : undefined} {...rest} />
    {hint && <small id={`${id}-hint`}>{hint}</small>}
  </div>
}

export function TextArea({ name, label, required = true, defaultValue }: { name: string, label: string, required?: boolean, defaultValue?: string }) {
  const id = useId()
  return <div className="field">
    <label htmlFor={id}>{label}{!required && <span className="optional"> (opcional)</span>}</label>
    <textarea id={id} name={name} required={required} defaultValue={defaultValue} rows={3} />
  </div>
}

export interface Option { value: string, label: string }
export function SelectField({ name, label, options, required = true, placeholder = 'Selecione', defaultValue, value, onChange, hint }: {
  name: string, label: string, options: Option[], required?: boolean, placeholder?: string, defaultValue?: string,
  /** Quando informado, o campo é controlado pelo estado do componente pai. */
  value?: string,
  onChange?: (value: string) => void, hint?: string,
}) {
  const id = useId()
  return <div className="field">
    <label htmlFor={id}>{label}{!required && <span className="optional"> (opcional)</span>}</label>
    {/* Remonta quando as opções assíncronas chegam, para que o valor padrão (ex.: cliente pré-selecionado) seja aplicado. */}
    <select key={value === undefined ? `${defaultValue ?? ''}|${options.length > 0}` : 'controlled'} id={id} name={name} required={required}
      {...(value === undefined ? { defaultValue: defaultValue ?? '' } : { value })} onChange={e => onChange?.(e.target.value)} aria-describedby={hint ? `${id}-hint` : undefined}>
      <option value="">{placeholder}</option>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
    {hint && <small id={`${id}-hint`}>{hint}</small>}
  </div>
}

export const CUSTOMER_PAGE_SIZE = 50

function customerLabel(c: Customer): string {
  return `${c.name} · ${c.email}${c.active === false ? ' (inativo)' : ''}`
}

/**
 * Seleção de cliente ativo do CRM além da primeira página (#34): navega pelas páginas da consulta
 * paginada, busca por e-mail exato e carrega pelo UUID o cliente já selecionado (ex.: vindo da URL),
 * que continua disponível ao mudar de página. Sem `value`, o próprio campo guarda a seleção.
 */
export function CustomerPicker({ name = 'customerId', label, value, defaultValue = '', onChange, required = true, placeholder = 'Selecione', hint }: {
  name?: string, label: string, value?: string, defaultValue?: string, onChange?: (value: string) => void,
  required?: boolean, placeholder?: string, hint?: string,
}) {
  const id = useId()
  const { api } = useSession()
  const [own, setOwn] = useState(defaultValue)
  const selected = value ?? own
  const [page, setPage] = useState<{ offset: number, email: string }>({ offset: 0, email: '' })
  const [known, setKnown] = useState<Customer | null>(null)
  const [lookupError, setLookupError] = useState<ApiError | null>(null)
  const emailRef = useRef<HTMLInputElement>(null)
  const selectRef = useRef<HTMLSelectElement>(null)
  const selectedRef = useRef(selected)
  selectedRef.current = selected

  // Cada resposta guarda a página que a pediu: a faixa e o bloqueio dependem do que chegou, não do último clique.
  const customers = useResource(async a => {
    const result = await a.listCustomers({ active: true, email: page.email || undefined, limit: CUSTOMER_PAGE_SIZE, offset: page.offset })
    return { ...result, data: { offset: page.offset, email: page.email, rows: result.data } }
  }, [page.offset, page.email])
  const loaded = customers.data
  const rows = loaded?.rows ?? []
  const inPage = rows.find(c => c.customerId === selected)

  // Cliente selecionado fora da página atual: consulta direta pelo UUID.
  useEffect(() => {
    setLookupError(null)
    if (!selected || inPage || known?.customerId === selected) return
    let current = true
    api.getCustomer(selected).then(r => { if (current) setKnown(r.data) }, e => { if (current) setLookupError(asApiError(e)) })
    return () => { current = false }
  }, [api, selected, inPage, known?.customerId])
  useEffect(() => { if (inPage) setKnown(inPage) }, [inPage])

  // `form.reset()` após sucesso não apaga o cliente escolhido: a seleção pertence ao estado do campo.
  useEffect(() => {
    const form = selectRef.current?.form
    if (!form) return
    const restore = () => setTimeout(() => { if (selectRef.current) selectRef.current.value = selectedRef.current })
    form.addEventListener('reset', restore)
    return () => form.removeEventListener('reset', restore)
  }, [])

  function choose(next: string) {
    if (value === undefined) setOwn(next)
    onChange?.(next)
  }
  function search() {
    setPage({ offset: 0, email: emailRef.current?.value.trim() ?? '' })
  }

  // Até chegar a página pedida, a navegação fica bloqueada: cliques seguidos pulariam páginas.
  const loading = customers.status === 'loading' || (customers.status === 'success' && (loaded?.offset !== page.offset || loaded?.email !== page.email))
  const extra = known && known.customerId === selected && !inPage ? [known] : []
  const options = [...extra, ...rows]
  const first = rows.length && loaded ? loaded.offset + 1 : 0
  return <div className="field customer-picker">
    <label htmlFor={id}>{label}{!required && <span className="optional"> (opcional)</span>}</label>
    <select ref={selectRef} id={id} name={name} required={required} value={selected} onChange={e => choose(e.target.value)} aria-describedby={`${id}-hint`}>
      <option value="">{customers.status === 'loading' && !customers.data ? 'Carregando…' : placeholder}</option>
      {selected && !options.some(c => c.customerId === selected) && <option value={selected}>{lookupError ? `Cliente ${selected.slice(0, 8)} não carregado` : `Carregando cliente ${selected.slice(0, 8)}…`}</option>}
      {options.map(c => <option key={c.customerId} value={c.customerId}>{customerLabel(c)}</option>)}
    </select>
    <div className="picker-tools" role="group" aria-label="Paginação e busca de clientes">
      <input ref={emailRef} type="email" aria-label="Buscar por e-mail exato" placeholder="E-mail exato" autoComplete="off"
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search() } }} />
      <button type="button" className="secondary small" onClick={search}>Buscar</button>
      <button type="button" className="secondary small" disabled={loading || page.offset === 0} onClick={() => setPage(p => ({ ...p, offset: Math.max(0, p.offset - CUSTOMER_PAGE_SIZE) }))}>Anteriores</button>
      <button type="button" className="secondary small" disabled={loading || rows.length < CUSTOMER_PAGE_SIZE} onClick={() => setPage(p => ({ ...p, offset: p.offset + CUSTOMER_PAGE_SIZE }))}>Próximos</button>
    </div>
    <small id={`${id}-hint`} role="status">
      {customers.status === 'error' ? <>Falha ao carregar clientes ({errorHeadline(customers.error)}) <button type="button" className="inline" onClick={() => void customers.reload()}>Tentar novamente</button></>
        : lookupError ? `Não foi possível carregar o cliente selecionado: ${errorHeadline(lookupError)}`
        // Durante o carregamento as opções ainda são da página anterior: a faixa só aparece com os dados novos.
        : loading ? 'Carregando clientes…'
        : rows.length && loaded ? `Clientes ativos ${first}–${loaded.offset + rows.length}${loaded.email ? ` com e-mail ${loaded.email}` : ''}.`
        : loaded ? (loaded.email ? 'Nenhum cliente ativo com esse e-mail.' : 'Nenhum cliente ativo nesta página.') : 'Carregando clientes…'}
      {hint && <> {hint}</>}
    </small>
  </div>
}

export function Checkbox({ name, label, defaultChecked = true }: { name: string, label: string, defaultChecked?: boolean }) {
  const id = useId()
  return <div className="check"><input id={id} type="checkbox" name={name} defaultChecked={defaultChecked} /><label htmlFor={id}>{label}</label></div>
}

/** Formulário que só limpa os campos quando a operação tem sucesso. */
export function ActionForm({ submit, busy, onSubmit, children, label, reset = form => form.reset() }: {
  submit: string, busy: boolean, label?: string, children: ReactNode,
  onSubmit: (data: FormData) => Promise<boolean>,
  /** Limpeza após sucesso; por padrão, `form.reset()`. Formulários com campos controlados limpam só os demais. */
  reset?: (form: HTMLFormElement) => void,
}) {
  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    if (await onSubmit(new FormData(form))) reset(form)
  }
  return <form onSubmit={e => void handle(e)} aria-label={label}>
    {children}
    <button type="submit" disabled={busy}>{busy ? 'Enviando…' : submit}</button>
  </form>
}

export interface Column<T> { key: string, label: string, render: (row: T) => ReactNode }
export function Table<T>({ rows, columns, rowKey, caption }: { rows: T[], columns: Column<T>[], rowKey: (row: T) => string, caption: string }) {
  return <div className="table-wrap" tabIndex={0} role="region" aria-label={`Tabela: ${caption}`}>
    <table>
      <caption className="sr-only">{caption}</caption>
      <thead><tr>{columns.map(c => <th key={c.key} scope="col">{c.label}</th>)}</tr></thead>
      <tbody>{rows.map(row => <tr key={rowKey(row)}>{columns.map(c => <td key={c.key}>{c.render(row)}</td>)}</tr>)}</tbody>
    </table>
  </div>
}

export function PageIntro({ children }: { children: ReactNode }) {
  return <p className="intro">{children}</p>
}
