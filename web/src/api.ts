/**
 * Cliente tipado da API `/api/v1` (contrato em `docs/api/openapi.yaml`).
 *
 * - Envia `Authorization: Bearer <token>` informado pelo usuário em tempo de execução.
 * - Gera um `X-Correlation-ID` (UUID) por requisição e devolve o valor efetivo.
 * - Envia `Idempotency-Key` apenas nos comandos que o contrato declara aceitar.
 * - Converte respostas `application/problem+json` (RFC 9457) em `ApiError`.
 */

// ---------- Tipos do contrato ----------

export type Uuid = string
export type BillingCycle = 'ONCE' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY'

export interface Customer {
  customerId: Uuid
  name: string
  email: string
  eligible: boolean
  consentService: boolean
  active?: boolean
  legacyId?: string | null
}
export interface CustomerCreate { name: string, email: string, eligible?: boolean, consentService?: boolean, legacyId?: string | null }
export interface CustomerUpdate { name?: string, email?: string, eligible?: boolean, consentService?: boolean }

export interface Contact { contactId: Uuid, customerId: Uuid, name: string, email: string, phone: string | null }
export interface ContactInput { customerId: Uuid, name: string, email: string, phone?: string | null }

export type OpportunityStatus = 'OPEN' | 'WON' | 'LOST'
export interface Opportunity { opportunityId: Uuid, customerId: Uuid, title: string, status: OpportunityStatus, notes: string | null }
export interface OpportunityInput { customerId: Uuid, title: string, notes?: string | null }

export type ReservationStatus = 'REQUESTED' | 'DRAFTED' | 'ACTIVE' | 'CLOSED' | 'CANCELLED'
export interface Reservation {
  reservationId: Uuid
  customerId: Uuid
  vehicleGroup: string
  protectionCode: string
  serviceCode: string
  startsOn: string
  endsOn: string
  amount: number
  currency: string
  billingCycle: BillingCycle
  slaHours: number
  status: ReservationStatus
  contractId: Uuid | null
}
export interface ReservationInput {
  customerId: Uuid
  vehicleGroup: string
  protectionCode: string
  serviceCode: string
  startsOn: string
  endsOn: string
  amount: number
  currency?: string
  billingCycle?: BillingCycle
  slaHours?: number
}

export type ContractStatus = 'DRAFT' | 'ACTIVE' | 'CLOSED' | 'CANCELLED'
export interface Billing { amount: number | string, currency: string, cycle: BillingCycle }
export interface Contract {
  contractId: Uuid
  customerId: Uuid
  serviceCode: string
  startsOn: string
  endsOn?: string | null
  billing: Billing
  slaHours: number
  status: ContractStatus
  eventId?: Uuid
}
export interface ContractDraftCreate { customerId: Uuid, serviceCode: string, startsOn: string, billing: Billing, slaHours?: number }
export interface ReservationDraft { reservationId: Uuid, contract: Contract }
export interface ContractCloseInput { endsOn?: string | null, reason?: string | null }
export interface Entitlement { eligible: boolean, slaHours: number | null }

export type InvoiceStatus = 'OPEN' | 'PARTIALLY_PAID' | 'PAID' | 'OVERDUE' | 'CANCELLED'
export interface Invoice {
  invoiceId: Uuid
  contractId: Uuid
  customerId: Uuid
  /** INITIAL: primeira cobrança (ativação); FINAL: faturamento final (encerramento). */
  kind: 'INITIAL' | 'FINAL'
  amount: number
  currency: string
  dueDate: string
  paidAmount: number
  balance: number
  /** OVERDUE também é calculado na leitura; `delinquent` indica inadimplência já registrada. */
  status: InvoiceStatus
  delinquent: boolean
  overdueSince: string | null
  sourceEventId: Uuid | null
}
export interface Payment { paymentId: Uuid, invoiceId: Uuid, amount: number, currency: string, reference: string }
export interface PaymentInput { amount: number, currency: string, reference: string }
export interface PaymentResult { paymentId: Uuid, invoice: Invoice }
export interface OverdueCheckResult { asOf: string, evaluatedAt: string, markedOverdue: Uuid[], alreadyOverdue: number }

export type TicketStatus = 'OPEN' | 'PENDING_ENTITLEMENT' | 'REJECTED_ENTITLEMENT' | 'RESOLVED'
/** Estado de SLA calculado pela API no instante da resposta (T15). */
export type SlaStatus = 'PENDING' | 'WITHIN' | 'BREACHED' | 'MET' | 'NOT_APPLICABLE'
export interface Ticket {
  ticketId: Uuid
  customerId: Uuid
  contractId: Uuid
  serviceCode: string
  category: string
  status: TicketStatus
  priority: 'NORMAL' | 'HIGH'
  slaHours: number | null
  dueAt: string | null
  description?: string
  owner?: string | null
  openedAt?: string | null
  resolvedAt?: string | null
  slaStatus?: SlaStatus | null
}
export type TicketHistoryAction = 'OPENED' | 'ASSIGNED' | 'REASSIGNED' | 'ENTITLEMENT_CONFIRMED' | 'ENTITLEMENT_REJECTED' | 'RESOLVED'
export interface TicketHistoryEntry {
  occurredAt: string
  action: TicketHistoryAction
  fromStatus: TicketStatus | null
  toStatus: TicketStatus
  owner: string | null
  previousOwner: string | null
  actorRole: string | null
  slaStatus: SlaStatus | null
  correlationId: string
}
export interface PendingReconciliation { confirmed: number, rejected: number, remaining: number, contractsAvailable: boolean, tickets: Ticket[] }
export interface TicketCreate { customerId: Uuid, contractId: Uuid, serviceCode: string, category: string, description: string }

export interface Process { processId: Uuid, processType: string, referenceId: Uuid, customerId: Uuid, state: string, owner: string, dueAt: string | null }
export type TaskState = 'OPEN' | 'IN_PROGRESS' | 'DONE' | 'CANCELLED'
export interface Task { taskId: Uuid, processId: Uuid, title: string, state: TaskState, owner: string, dueAt: string | null }
export interface TaskInput { processId: Uuid, title: string, owner?: string }
export interface TaskChange { state: TaskState, owner?: string | null }

export interface DemoState { customers: number, contracts: number, invoices: number, tickets: number, processes: number, legacyMappings: number }
export interface DispatchResult { processed: number, failed: number }
export interface Failure { eventId: Uuid, eventType: string, attempts: number, reason: string | null, correlationId: Uuid }
export interface OperationTrace {
  correlationId: Uuid
  audit: { occurredAt: string, module: string, operation: string, result: string, entityId: string | null }[]
  events: { eventId: Uuid, eventType: string, status: string, attempts: number }[]
}

// ---------- Erros (RFC 9457) ----------

export interface ValidationIssue { loc?: (string | number)[], msg?: string, type?: string, ctx?: Record<string, unknown> }

export type ErrorKind = 'http' | 'network'

export class ApiError extends Error {
  readonly kind: ErrorKind
  readonly status: number
  readonly title: string
  readonly detail: string
  readonly code: string
  readonly correlationId: string
  readonly issues: ValidationIssue[]

  constructor(init: { kind: ErrorKind, status: number, title: string, detail: string, code: string, correlationId: string, issues?: ValidationIssue[] }) {
    super(init.detail || init.title)
    this.name = 'ApiError'
    this.kind = init.kind
    this.status = init.status
    this.title = init.title
    this.detail = init.detail
    this.code = init.code
    this.correlationId = init.correlationId
    this.issues = init.issues ?? []
  }
}

/** UUID v4. Usa `crypto.randomUUID` quando disponível (contexto seguro) e `getRandomValues` como alternativa. */
export function uuid(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

const FIELD_LABELS: Record<string, string> = {
  name: 'Nome', email: 'E-mail', phone: 'Telefone', title: 'Título', notes: 'Notas', customerId: 'Cliente',
  contractId: 'Contrato', vehicleGroup: 'Grupo de veículo', protectionCode: 'Proteção', serviceCode: 'Serviço',
  startsOn: 'Início', endsOn: 'Fim', amount: 'Valor', currency: 'Moeda', billingCycle: 'Ciclo de cobrança',
  cycle: 'Ciclo de cobrança', slaHours: 'SLA (horas)', reference: 'Referência', category: 'Categoria',
  description: 'Descrição', owner: 'Responsável', state: 'Estado', processId: 'Processo', status: 'Estado',
  legacyId: 'ID legado', reason: 'Motivo', asOf: 'Data de referência', 'Idempotency-Key': 'Chave de idempotência',
}

/**
 * Converte um item de erro de validação em texto legível em português.
 *
 * A API v1 devolve apenas `type`, `loc` e `msg` minimizada ("Field required" ou
 * "Entrada inválida"), sem `ctx` nem `input`, para não ecoar dados enviados.
 * Os limites (`ctx`) só entram no texto quando presentes; sem eles a mensagem
 * descreve a regra sem inventar valores.
 */
export function describeIssue(issue: ValidationIssue): string {
  const loc = (issue.loc ?? []).filter(part => part !== 'body' && part !== 'query' && part !== 'path' && part !== 'header')
  const fieldKey = loc.length ? String(loc[loc.length - 1]) : ''
  const field = FIELD_LABELS[fieldKey] ?? fieldKey
  const ctx = issue.ctx ?? {}
  const limit = (key: string, withLimit: (value: string) => string, without: string): string =>
    ctx[key] === undefined || ctx[key] === null ? without : withLimit(String(ctx[key]))
  let message: string
  switch (issue.type) {
    case 'missing': message = 'campo obrigatório'; break
    case 'string_too_short': message = limit('min_length', v => `mínimo de ${v} caracteres`, 'texto curto demais'); break
    case 'string_too_long': message = limit('max_length', v => `máximo de ${v} caracteres`, 'texto longo demais'); break
    case 'string_pattern_mismatch': message = 'formato inválido'; break
    case 'uuid_parsing': case 'uuid_type': message = 'identificador inválido'; break
    case 'date_parsing': case 'date_from_datetime_parsing': case 'date_type': message = 'data inválida'; break
    case 'greater_than': message = limit('gt', v => `deve ser maior que ${v}`, 'valor abaixo do permitido'); break
    case 'greater_than_equal': message = limit('ge', v => `deve ser no mínimo ${v}`, 'valor abaixo do permitido'); break
    case 'less_than': message = limit('lt', v => `deve ser menor que ${v}`, 'valor acima do permitido'); break
    case 'less_than_equal': message = limit('le', v => `deve ser no máximo ${v}`, 'valor acima do permitido'); break
    case 'decimal_parsing': case 'float_parsing': case 'int_parsing': message = 'número inválido'; break
    case 'enum': case 'literal_error': message = 'valor fora das opções permitidas'; break
    // A mensagem do validador não é devolvida; o campo identifica o caso de e-mail.
    case 'value_error': message = fieldKey === 'email' ? 'e-mail inválido' : 'valor inválido'; break
    default: message = 'valor inválido'
  }
  return field ? `${field}: ${message}` : message
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

async function toApiError(response: Response, fallbackCorrelation: string): Promise<ApiError> {
  const correlationId = response.headers.get('X-Correlation-ID') ?? fallbackCorrelation
  let body: Record<string, unknown> = {}
  try { body = await response.json() as Record<string, unknown> } catch { /* corpo não JSON: usa os valores padrão abaixo */ }
  const issues = (Array.isArray(body.errors) ? body.errors : Array.isArray(body.detail) ? body.detail : []) as ValidationIssue[]
  return new ApiError({
    kind: 'http',
    status: response.status,
    title: asText(body.title) || `Erro HTTP ${response.status}`,
    detail: asText(body.detail),
    code: asText(body.code) || `HTTP_${response.status}`,
    correlationId: asText(body.correlationId) || correlationId,
    issues,
  })
}

// ---------- Cliente ----------

export interface ApiResult<T> {
  data: T
  status: number
  correlationId: string
  /** Valor do cabeçalho `Idempotency-Replayed`, quando a operação o devolve. */
  replayed: boolean | null
}

type Query = Record<string, string | number | boolean | undefined | null>
interface RequestOptions { body?: unknown, query?: Query, idempotencyKey?: string }

function withQuery(path: string, query?: Query): string {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const text = params.toString()
  return text ? `${path}?${text}` : path
}

export function createApi(token: string, fetcher: typeof fetch = (...args) => fetch(...args)) {
  async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
    const correlationId = uuid()
    const headers: Record<string, string> = { Accept: 'application/json, application/problem+json', 'X-Correlation-ID': correlationId }
    if (token) headers.Authorization = `Bearer ${token}`
    if (options.body !== undefined) headers['Content-Type'] = 'application/json'
    if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey
    let response: Response
    try {
      response = await fetcher(withQuery(path, options.query), {
        method, headers, body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      })
    } catch {
      throw new ApiError({
        kind: 'network', status: 0, title: 'Falha de rede', code: 'NETWORK_ERROR', correlationId,
        detail: 'Não foi possível contatar a API. Verifique a conexão e se o servidor está em execução.',
      })
    }
    if (!response.ok) throw await toApiError(response, correlationId)
    const replayHeader = response.headers.get('Idempotency-Replayed')
    const data = response.status === 204 ? (undefined as T) : await response.json() as T
    return {
      data, status: response.status,
      correlationId: response.headers.get('X-Correlation-ID') ?? correlationId,
      replayed: replayHeader === null ? null : replayHeader === 'true',
    }
  }
  const get = <T>(path: string, query?: Query) => request<T>('GET', path, { query })

  return {
    // CRM
    listCustomers: (q?: { email?: string, active?: boolean, limit?: number, offset?: number }) => get<Customer[]>('/api/v1/crm/customers', q),
    createCustomer: (body: CustomerCreate) => request<Customer>('POST', '/api/v1/crm/customers', { body }),
    updateCustomer: (id: Uuid, body: CustomerUpdate) => request<Customer>('PATCH', `/api/v1/crm/customers/${id}`, { body }),
    deactivateCustomer: (id: Uuid) => request<Customer>('POST', `/api/v1/crm/customers/${id}/deactivate`),
    listContacts: (customerId?: Uuid) => get<Contact[]>('/api/v1/crm/contacts', { customerId }),
    createContact: (body: ContactInput) => request<Contact>('POST', '/api/v1/crm/contacts', { body }),
    deleteContact: (id: Uuid) => request<void>('DELETE', `/api/v1/crm/contacts/${id}`),
    listOpportunities: (q?: { customerId?: Uuid, status?: OpportunityStatus }) => get<Opportunity[]>('/api/v1/crm/opportunities', q),
    createOpportunity: (body: OpportunityInput) => request<Opportunity>('POST', '/api/v1/crm/opportunities', { body }),
    updateOpportunity: (id: Uuid, body: { status?: OpportunityStatus, title?: string, notes?: string }) =>
      request<Opportunity>('PATCH', `/api/v1/crm/opportunities/${id}`, { body }),

    // Reservas e contratos
    listReservations: (customerId?: Uuid) => get<Reservation[]>('/api/v1/contracts/reservations', { customerId }),
    createReservation: (body: ReservationInput, idempotencyKey: string) =>
      request<Reservation>('POST', '/api/v1/contracts/reservations', { body, idempotencyKey }),
    draftFromReservation: (id: Uuid, idempotencyKey: string) =>
      request<ReservationDraft>('POST', `/api/v1/contracts/reservations/${id}/draft`, { idempotencyKey }),
    cancelReservation: (id: Uuid) => request<Reservation>('POST', `/api/v1/contracts/reservations/${id}/cancel`),
    listContracts: (customerId?: Uuid) => get<Contract[]>('/api/v1/contracts', { customerId }),
    createDraft: (body: ContractDraftCreate, idempotencyKey: string) =>
      request<Contract>('POST', '/api/v1/contracts/drafts', { body, idempotencyKey }),
    activateContract: (id: Uuid, idempotencyKey: string) =>
      request<Contract>('POST', `/api/v1/contracts/${id}/activate`, { idempotencyKey }),
    closeContract: (id: Uuid, body: ContractCloseInput, idempotencyKey: string) =>
      request<Contract>('POST', `/api/v1/contracts/${id}/close`, { body, idempotencyKey }),
    entitlement: (id: Uuid, customerId: Uuid, serviceCode: string) =>
      get<Entitlement>(`/api/v1/contracts/${id}/entitlement`, { customerId, serviceCode }),

    // Financeiro
    listInvoices: (contractId?: Uuid) => get<Invoice[]>('/api/v1/finance/invoices', { contractId }),
    listPayments: (invoiceId?: Uuid) => get<Payment[]>('/api/v1/finance/payments', { invoiceId }),
    recordPayment: (invoiceId: Uuid, body: PaymentInput, idempotencyKey: string) =>
      request<PaymentResult>('POST', `/api/v1/finance/invoices/${invoiceId}/payments`, { body, idempotencyKey }),
    checkOverdue: (asOf?: string) =>
      request<OverdueCheckResult>('POST', '/api/v1/finance/invoices/overdue-check', { body: asOf ? { asOf } : {} }),

    // Atendimento
    listTickets: () => get<Ticket[]>('/api/v1/support/tickets'),
    openTicket: (body: TicketCreate, idempotencyKey: string) =>
      request<Ticket>('POST', '/api/v1/support/tickets', { body, idempotencyKey }),
    assignTicket: (id: Uuid, owner: string) => request<Ticket>('POST', `/api/v1/support/tickets/${id}/assign`, { body: { owner } }),
    resolveTicket: (id: Uuid) => request<Ticket>('POST', `/api/v1/support/tickets/${id}/resolve`),
    reconcileTicket: (id: Uuid) => request<Ticket>('POST', `/api/v1/support/tickets/${id}/reconcile`),
    reconcilePendingTickets: () => request<PendingReconciliation>('POST', '/api/v1/support/tickets/reconcile-pending'),
    ticketHistory: (id: Uuid) => get<TicketHistoryEntry[]>(`/api/v1/support/tickets/${id}/history`),

    // Workflow
    listProcesses: () => get<Process[]>('/api/v1/workflow/processes'),
    listTasks: (processId?: Uuid) => get<Task[]>('/api/v1/workflow/tasks', { processId }),
    createTask: (body: TaskInput) => request<Task>('POST', '/api/v1/workflow/tasks', { body }),
    changeTask: (id: Uuid, body: TaskChange) => request<Task>('PATCH', `/api/v1/workflow/tasks/${id}`, { body }),

    // Integração e operação
    demoState: () => get<DemoState>('/api/v1/demo/state'),
    dispatchOutbox: () => request<DispatchResult>('POST', '/api/v1/integration/outbox/dispatch'),
    listFailures: () => get<Failure[]>('/api/v1/integration/failures'),
    reprocessFailure: (eventId: Uuid) => request<{ eventId: Uuid, status: string }>('POST', `/api/v1/integration/failures/${eventId}/reprocess`),
    operationTrace: (correlationId: Uuid) => get<OperationTrace>(`/api/v1/operations/${correlationId}`),
  }
}

export type Api = ReturnType<typeof createApi>

/** Mensagem principal, em português, para um erro da API. */
export function errorHeadline(error: ApiError): string {
  if (error.kind === 'network') return 'Não foi possível contatar a API.'
  switch (error.status) {
    case 400: return 'Requisição inválida.'
    case 401: return 'Credencial ausente ou inválida. Entre novamente com a credencial de demonstração.'
    case 403: return 'Seu papel não tem permissão para esta operação.'
    case 404: return 'Recurso não encontrado.'
    case 409: return 'A operação conflita com o estado atual do registro.'
    case 422: return 'Os dados enviados não foram aceitos.'
    default: return error.status >= 500 ? 'Erro interno no servidor. Tente novamente em instantes.' : error.title
  }
}

/** Normaliza qualquer exceção lançada durante uma operação. */
export function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  const message = error instanceof Error ? error.message : String(error)
  return new ApiError({ kind: 'http', status: 0, title: 'Erro inesperado', detail: message, code: 'CLIENT_ERROR', correlationId: '' })
}
