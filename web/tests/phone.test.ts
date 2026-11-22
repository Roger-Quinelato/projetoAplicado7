import assert from 'node:assert/strict'
import test from 'node:test'
import { formatPhone, toE164 } from '../src/phone.ts'

test('DDD e número viram E.164 com +55, com ou sem máscara', () => {
  assert.equal(toE164('31999990000'), '+5531999990000')
  assert.equal(toE164('(31) 99999-0000'), '+5531999990000')
  assert.equal(toE164('(31) 3333-4444'), '+553133334444')
})
test('código do país digitado não é duplicado, vazio vira null e o resto é inválido', () => {
  assert.equal(toE164('+5531999990000'), '+5531999990000')
  assert.equal(toE164(''), null)
  assert.equal(toE164('12345'), undefined)
})
test('o telefone é mostrado sem o código do país', () => {
  assert.equal(formatPhone('+5531999990000'), '(31) 99999-0000')
  assert.equal(formatPhone('+553133334444'), '(31) 3333-4444')
  assert.equal(formatPhone(null), '—')
})
