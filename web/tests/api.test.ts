// Executado com `npm test` (`node --test`); o Node remove os tipos nativamente.
// Fica fora de `src` para não entrar no `tsc -b`, que não carrega tipos do Node.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { describeIssue } from '../src/api.ts'

// Formato devolvido pela API v1: sem `ctx`/`input` e com `msg` minimizada.
const v1 = (type: string, field: string) => ({ type, loc: ['body', field], msg: 'Entrada inválida' })

test('não exibe placeholders quando a API não envia ctx', () => {
  const cases: [string, string, string][] = [
    ['string_too_short', 'name', 'Nome: texto curto demais'],
    ['string_too_long', 'description', 'Descrição: texto longo demais'],
    ['greater_than', 'amount', 'Valor: valor abaixo do permitido'],
    ['greater_than_equal', 'slaHours', 'SLA (horas): valor abaixo do permitido'],
    ['less_than_equal', 'slaHours', 'SLA (horas): valor acima do permitido'],
  ]
  for (const [type, field, expected] of cases) {
    const text = describeIssue(v1(type, field))
    assert.equal(text, expected)
    assert.doesNotMatch(text, /\?|\b0\b|:\s*$/)
  }
})

test('identifica e-mail inválido pelo campo, não pela mensagem', () => {
  assert.equal(describeIssue(v1('value_error', 'email')), 'E-mail: e-mail inválido')
  assert.equal(describeIssue(v1('value_error', 'reference')), 'Referência: valor inválido')
})

test('mantém campo obrigatório e tipos sem ctx', () => {
  assert.equal(describeIssue({ type: 'missing', loc: ['body', 'customerId'], msg: 'Field required' }), 'Cliente: campo obrigatório')
  assert.equal(describeIssue(v1('uuid_parsing', 'contractId')), 'Contrato: identificador inválido')
  assert.equal(describeIssue(v1('desconhecido', 'state')), 'Estado: valor inválido')
})

test('usa os limites quando ctx está presente', () => {
  assert.equal(describeIssue({ type: 'string_too_short', loc: ['body', 'name'], ctx: { min_length: 2 } }), 'Nome: mínimo de 2 caracteres')
  assert.equal(describeIssue({ type: 'greater_than', loc: ['body', 'amount'], ctx: { gt: 0 } }), 'Valor: deve ser maior que 0')
})
