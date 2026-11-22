// Executado com `npm test` (`node --test`); o Node remove os tipos nativamente.
// Fica fora de `src` para não entrar no `tsc -b`, que não carrega tipos do Node.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ApiError, describeIssue, errorMessage, needsSupportCode } from '../src/api.ts'

const apiError = (status: number, detail = '', kind: 'http' | 'network' = 'http', code = 'X', issues: { type: string }[] = []) =>
  new ApiError({ kind, status, title: '', detail, code, correlationId: 'c-1', issues })

test('mensagens de erro não expõem código HTTP nem texto interno', () => {
  const cases: [ApiError, string][] = [
    [apiError(422, 'Data de encerramento anterior ao início do contrato'), 'A data de encerramento não pode ser antes do início do contrato. Escolha outra data.'],
    [apiError(409, 'Chamado não pode ser atribuído neste estado'), 'Este chamado já foi resolvido ou encerrado e não aceita responsável. A lista foi atualizada.'],
    [apiError(409, 'Pagamento excede saldo da fatura'), 'O valor é maior que o saldo da fatura. Informe um valor igual ou menor que o saldo.'],
    [apiError(409, 'algo novo no servidor'), 'Este item mudou e a ação não vale mais. Atualize a lista e tente de novo.'],
    [apiError(403), 'Seu perfil não pode fazer esta ação.'],
    [apiError(401), 'Sua sessão terminou. Entre novamente.'],
    [apiError(500), 'Não foi possível concluir agora. Tente de novo em instantes.'],
    [apiError(0, '', 'network'), 'Não foi possível falar com o sistema. Confira sua conexão e tente de novo.'],
    [apiError(422, 'Entrada inválida', 'http', 'VALIDATION_ERROR', [{ type: 'missing' }]), 'Corrija os campos abaixo e tente de novo.'],
  ]
  for (const [error, expected] of cases) {
    const message = errorMessage(error)
    assert.equal(message, expected)
    assert.doesNotMatch(message, /HTTP|\d{3}|CONFLICT|endpoint/)
  }
})

test('o código para o suporte só vale para falhas que a pessoa não corrige', () => {
  assert.equal(needsSupportCode(apiError(500)), true)
  assert.equal(needsSupportCode(apiError(0, '', 'network')), true)
  assert.equal(needsSupportCode(apiError(409)), false)
  assert.equal(needsSupportCode(apiError(0, '', 'http', 'PENDING_INTENT')), false)
})

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
