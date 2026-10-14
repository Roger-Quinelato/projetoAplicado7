import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, asApiError, describeIssue, errorHeadline, uuid, type Api, type ApiResult } from './api'

// ---------- Sessão compartilhada ----------

export interface Session {
  api: Api
  /** Volta à tela de credencial (usado em respostas 401). */
  signOut: () => void
  navigate: (route: string) => void
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
  PAID: ['Paga', 'good'], OVERDUE: ['Vencida', 'bad'],
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
  const { api } = useSession()
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

  useEffect(() => { void reload() }, [reload, ...deps])
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
  | { kind: 'error', message: string, error: ApiError }

/** Executa comandos com estado de envio e feedback legível de sucesso ou erro. */
export function useActions() {
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [busy, setBusy] = useState(false)

  const run = useCallback(async <T,>(label: string, action: () => Promise<ApiResult<T>>, describe?: (data: T) => string): Promise<ApiResult<T> | null> => {
    setBusy(true)
    setFeedback(null)
    try {
      const result = await action()
      const suffix = describe ? ` ${describe(result.data)}` : ''
      setFeedback({ kind: 'success', message: `${label}: concluído.${suffix}`, correlationId: result.correlationId, replayed: result.replayed })
      return result
    } catch (error) {
      setFeedback({ kind: 'error', message: `${label}: não concluído.`, error: asApiError(error) })
      return null
    } finally {
      setBusy(false)
    }
  }, [])

  return { feedback, busy, run, clear: () => setFeedback(null) }
}

/** JSON com chaves ordenadas: o mesmo corpo sempre gera a mesma impressão digital. */
export function fingerprint(value: unknown): string {
  return JSON.stringify(value ?? null, (_key, v: unknown) => v && typeof v === 'object' && !Array.isArray(v)
    ? Object.fromEntries(Object.entries(v as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)))
    : v)
}

/**
 * Chaves de idempotência por intenção e corpo. A chave anterior só é reaproveitada quando a nova
 * tentativa da mesma intenção envia exatamente o mesmo corpo (duplo clique, nova tentativa após
 * falha ambígua de rede); se o usuário corrigir um campo, gera-se uma chave nova. A chave é
 * descartada após sucesso e após `409 IDEMPOTENCY_CONFLICT`.
 */
export function useIdempotencyKeys() {
  const keys = useRef(new Map<string, { fingerprint: string, key: string }>())
  return {
    keyFor(intent: string, body: unknown): string {
      const print = fingerprint(body)
      let entry = keys.current.get(intent)
      if (!entry || entry.fingerprint !== print) { entry = { fingerprint: print, key: uuid() }; keys.current.set(intent, entry) }
      return entry.key
    },
    async send<T>(intent: string, body: unknown, call: (key: string) => Promise<ApiResult<T>>): Promise<ApiResult<T>> {
      const key = this.keyFor(intent, body)
      try {
        const result = await call(key)
        keys.current.delete(intent)
        return result
      } catch (error) {
        if (error instanceof ApiError && error.code === 'IDEMPOTENCY_CONFLICT') keys.current.delete(intent)
        throw error
      }
    },
  }
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
        {error.kind === 'network' ? 'Sem resposta do servidor' : <>HTTP {error.status} · código <code>{error.code}</code></>}
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

export function Card({ title, roles, children, aside, className }: { title: string, roles?: string, children: ReactNode, aside?: ReactNode, className?: string }) {
  const id = useId()
  return <section className={`card ${className ?? ''}`} aria-labelledby={id}>
    <div className="card-head">
      <div><h2 id={id}>{title}</h2>{roles && <p className="roles">Papéis: {roles}</p>}</div>
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
