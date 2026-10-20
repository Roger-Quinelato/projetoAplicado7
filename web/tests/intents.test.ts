// Regras de intenção pendente após falha ambígua (#34), sem React.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ApiError, type ApiResult } from '../src/api.ts'
import { IdempotentIntents, PENDING_INTENT, isAmbiguous } from '../src/intents.ts'

const ok = <T,>(data: T): ApiResult<T> => ({ data, status: 201, correlationId: 'c-ok', replayed: false })
const network = () => new ApiError({ kind: 'network', status: 0, title: 'Falha de rede', detail: '', code: 'NETWORK_ERROR', correlationId: 'c-rede' })
const http = (status: number, code: string) => new ApiError({ kind: 'http', status, title: '', detail: '', code, correlationId: `c-${status}` })

/** Servidor simulado: grava pela chave e responde de novo a mesma chave sem duplicar. */
function servidor() {
  const gravados = new Map<string, unknown>()
  const estado = { perderRespostas: false }
  return {
    gravados,
    estado,
    async criar(key: string, body: unknown, perderResposta = false): Promise<ApiResult<unknown>> {
      const replay = gravados.has(key)
      if (!replay) gravados.set(key, body)
      if (perderResposta || estado.perderRespostas) throw network()
      return { ...ok(body), replayed: replay }
    },
  }
}

test('classifica falhas ambíguas e definitivas', () => {
  assert.equal(isAmbiguous(network()), true)
  assert.equal(isAmbiguous(http(500, 'INTERNAL_ERROR')), true)
  assert.equal(isAmbiguous(http(504, 'HTTP_504')), true)
  assert.equal(isAmbiguous(http(503, 'HTTP_503')), true, '503 sem problema da API pode vir de um proxy após a gravação')
  assert.equal(isAmbiguous(http(503, 'SERVICE_UNAVAILABLE')), false, 'a API garante que nada foi gravado')
  assert.equal(isAmbiguous(http(422, 'VALIDATION_ERROR')), false)
  assert.equal(isAmbiguous(new Error('x')), false)
})

test('resposta perdida após a gravação: repetir o pedido original gera um único registro', async () => {
  const api = servidor()
  const intents = new IdempotentIntents()
  const body = { customerId: 'c1', amount: 10 }
  api.estado.perderRespostas = true
  await assert.rejects(intents.send('reservation', body, key => api.criar(key, body), 'Registro de reserva'))
  api.estado.perderRespostas = false
  const [pendente] = intents.pending()
  assert.equal(pendente.intent, 'reservation')
  assert.equal(pendente.label, 'Registro de reserva')
  assert.equal(pendente.correlationId, 'c-rede')

  const result = await intents.retry('reservation')
  assert.equal(result.replayed, true)
  assert.equal(api.gravados.size, 1)
  assert.deepEqual([...api.gravados.keys()], [pendente.key])
  assert.deepEqual(intents.pending(), [])
})

test('com pedido pendente, dados diferentes são recusados sem chamar a API', async () => {
  const api = servidor()
  const intents = new IdempotentIntents()
  await assert.rejects(intents.send('ticket', { description: 'a' }, key => api.criar(key, 'a', true)))
  let chamadas = 0
  await assert.rejects(
    intents.send('ticket', { description: 'editada' }, async key => { chamadas++; return api.criar(key, 'editada') }),
    (error: unknown) => error instanceof ApiError && error.code === PENDING_INTENT && error.correlationId === 'c-rede',
  )
  assert.equal(chamadas, 0)
  assert.equal(api.gravados.size, 1)
  assert.equal(intents.pending().length, 1, 'o pedido original continua preservado')
})

test('o mesmo corpo reaproveita a chave pendente; outras intenções seguem livres', async () => {
  const api = servidor()
  const intents = new IdempotentIntents()
  const body = { amount: 5 }
  await assert.rejects(intents.send('payment:A', body, key => api.criar(key, body, true)))
  await intents.send('payment:A', { amount: 5 }, key => api.criar(key, body))
  await intents.send('payment:B', { amount: 7 }, key => api.criar(key, 7))
  assert.equal(api.gravados.size, 2)
  assert.deepEqual(intents.pending(), [])
})

test('descartar libera nova chave para dados diferentes', async () => {
  const api = servidor()
  const intents = new IdempotentIntents()
  await assert.rejects(intents.send('draft', { a: 1 }, key => api.criar(key, 1, true)))
  const anterior = intents.pending()[0].key
  intents.discard('draft')
  let usada = ''
  await intents.send('draft', { a: 2 }, async key => { usada = key; return api.criar(key, 2) })
  assert.notEqual(usada, anterior)
})

test('falha definitiva não deixa pendência e libera a chave', async () => {
  const intents = new IdempotentIntents()
  const chaves: string[] = []
  for (const error of [http(422, 'VALIDATION_ERROR'), http(503, 'SERVICE_UNAVAILABLE')]) {
    await assert.rejects(intents.send('reservation', { a: 1 }, async key => { chaves.push(key); throw error }))
    assert.deepEqual(intents.pending(), [])
  }
  assert.notEqual(chaves[0], chaves[1])
})

test('a ordem das chaves do corpo não muda a intenção', async () => {
  const api = servidor()
  const intents = new IdempotentIntents()
  await assert.rejects(intents.send('x', { a: 1, b: 2 }, key => api.criar(key, 1, true)))
  await intents.send('x', { b: 2, a: 1 }, key => api.criar(key, 1))
  assert.equal(api.gravados.size, 1)
})

test('notifica mudanças na lista de pendências', async () => {
  let avisos = 0
  const intents = new IdempotentIntents(() => { avisos++ })
  await assert.rejects(intents.send('x', 1, async () => { throw network() }))
  assert.equal(avisos, 1)
  await intents.send('x', 1, async () => ok(1))
  assert.equal(avisos, 2)
})
