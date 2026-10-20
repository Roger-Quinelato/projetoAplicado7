import { ApiError, uuid, type ApiResult } from './api.ts'

/**
 * Comandos com `Idempotency-Key` e falha ambígua (#34).
 *
 * Uma falha de rede ou um 5xx depois do envio não diz se o servidor gravou o comando. Nesses casos a
 * intenção fica pendente: corpo, chave e correlação são preservados para repetir o pedido original com a
 * mesma chave (o servidor devolve a resposta gravada, sem duplicar). Enquanto a intenção estiver pendente,
 * um envio com corpo diferente é recusado no navegador, para que uma edição não vire uma nova criação sem
 * que o usuário descarte explicitamente o pedido anterior.
 *
 * Respostas definitivas liberam a chave: sucesso, 4xx e 503 `SERVICE_UNAVAILABLE` (a API garante que
 * nada foi gravado, ADR-006).
 */

/** JSON com chaves ordenadas: o mesmo corpo sempre gera a mesma impressão digital. */
export function fingerprint(value: unknown): string {
  return JSON.stringify(value ?? null, (_key, v: unknown) => v && typeof v === 'object' && !Array.isArray(v)
    ? Object.fromEntries(Object.entries(v as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)))
    : v)
}

/** Verdadeiro quando não é possível saber se o servidor executou o comando. */
export function isAmbiguous(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  if (error.kind === 'network') return true
  if (error.status === 503 && error.code === 'SERVICE_UNAVAILABLE') return false
  return error.status >= 500
}

export const PENDING_INTENT = 'PENDING_INTENT'

export interface PendingIntent {
  intent: string
  label: string
  key: string
  /** Correlação da última tentativa sem confirmação. */
  correlationId: string
}

interface Entry {
  fingerprint: string
  key: string
  body: unknown
  label: string
  call: (key: string) => Promise<ApiResult<unknown>>
  pending: boolean
  correlationId: string
}

export class IdempotentIntents {
  private readonly entries = new Map<string, Entry>()
  private readonly onChange: () => void

  constructor(onChange: () => void = () => {}) {
    this.onChange = onChange
  }

  pending(): PendingIntent[] {
    return [...this.entries.entries()].filter(([, e]) => e.pending)
      .map(([intent, e]) => ({ intent, label: e.label, key: e.key, correlationId: e.correlationId }))
  }

  /**
   * Envia o comando. A chave anterior só é reaproveitada para o mesmo corpo (duplo clique, nova tentativa);
   * com intenção pendente, um corpo diferente é recusado com `PENDING_INTENT`.
   */
  async send<T>(intent: string, body: unknown, call: (key: string) => Promise<ApiResult<T>>, label = intent): Promise<ApiResult<T>> {
    const print = fingerprint(body)
    let entry = this.entries.get(intent)
    if (entry?.pending && entry.fingerprint !== print) {
      throw new ApiError({
        kind: 'http', status: 0, code: PENDING_INTENT, correlationId: entry.correlationId,
        title: 'Há um pedido anterior sem confirmação.',
        detail: 'Consulte os registros e repita o pedido original, que usa a mesma chave e não duplica, ou descarte-o antes de enviar dados diferentes.',
      })
    }
    if (!entry || entry.fingerprint !== print) {
      entry = { fingerprint: print, key: uuid(), body, label, call, pending: false, correlationId: '' }
      this.entries.set(intent, entry)
    }
    const current = entry
    current.call = call as Entry['call']
    current.label = label
    try {
      const result = await call(current.key)
      this.release(intent, current)
      return result
    } catch (error) {
      if (isAmbiguous(error)) {
        current.pending = true
        current.correlationId = (error as ApiError).correlationId
        this.onChange()
      } else {
        this.release(intent, current)
      }
      throw error
    }
  }

  /** Repete o pedido pendente com o mesmo corpo e a mesma chave. */
  retry(intent: string): Promise<ApiResult<unknown>> {
    const entry = this.entries.get(intent)
    if (!entry) return Promise.reject(new ApiError({
      kind: 'http', status: 0, code: PENDING_INTENT, correlationId: '', title: 'Nenhum pedido pendente.', detail: '',
    }))
    return this.send(intent, entry.body, entry.call, entry.label)
  }

  /** Descarta a intenção; um envio seguinte usará outra chave. */
  discard(intent: string): void {
    if (this.entries.delete(intent)) this.onChange()
  }

  private release(intent: string, entry: Entry): void {
    if (this.entries.get(intent) !== entry) return
    this.entries.delete(intent)
    if (entry.pending) this.onChange()
  }
}
