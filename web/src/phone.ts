/** Telefone nacional (DDD e número): a tela aceita sem código do país e a API recebe em E.164 com +55. */
export const PHONE_INPUT_PATTERN = '(\+?55 ?)?\(?\d{2}\)? ?9?\d{4}-?\d{4}'

/** Converte o que foi digitado para E.164; vazio vira `null` e texto fora do padrão vira `undefined`. */
export function toE164(input: string): string | null | undefined {
  const digits = input.replace(/\D/g, '')
  if (!digits) return null
  if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) return `+${digits}`
  if (digits.length === 10 || digits.length === 11) return `+55${digits}`
  return undefined
}

/** Mostra o telefone como (DDD) número; números fora do padrão brasileiro aparecem como vieram. */
export function formatPhone(phone: string | null): string {
  if (!phone) return '—'
  const m = /^\+55(\d{2})(\d{4,5})(\d{4})$/.exec(phone)
  return m ? `(${m[1]}) ${m[2]}-${m[3]}` : phone
}
