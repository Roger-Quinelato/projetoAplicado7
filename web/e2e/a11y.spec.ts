import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { entrar } from './helpers'

// Bloqueante desde 20/10/2026 (#62): as violações apontadas na auditoria de 01/10/2026 foram tratadas, o contraste
// do conteúdo fora dos cartões passou a ser medido (#61) e a varredura fica sem violações WCAG 2 A/AA nas telas iniciais.
// O contraste com registros preenchidos é coberto por papeis-e-feedback.spec.ts.
const rotas = ['#/', '#/crm', '#/reservas', '#/financeiro', '#/atendimento', '#/workflow']

test('varredura axe de cada contexto sem violações WCAG 2 A/AA', async ({ page }, info) => {
  await entrar(page, 'demo-admin')
  const resumo: Record<string, string[]> = {}
  for (const rota of rotas) {
    await page.goto(`/${rota}`)
    await page.getByRole('heading', { level: 1 }).waitFor()
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    resumo[rota] = violations.map(v => `${v.impact ?? 'n/d'} · ${v.id} · ${v.nodes.length} nó(s)`)
  }
  await info.attach('axe-resumo.json', { body: JSON.stringify(resumo, null, 2), contentType: 'application/json' })
  expect(resumo).toEqual(Object.fromEntries(rotas.map(rota => [rota, []])))
})
