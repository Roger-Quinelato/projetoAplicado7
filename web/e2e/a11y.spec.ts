import AxeBuilder from '@axe-core/playwright'
import { test } from '@playwright/test'
import { entrar } from './helpers'

// Informativo: anexa as violações ao relatório e não reprova. A auditoria de 01/10/2026 (output/auditoria/2026-10-01T2035Z)
// já apontou contraste e outros itens; promover a bloqueante é decisão para depois de tratá-los.
const rotas = ['#/', '#/crm', '#/reservas', '#/financeiro', '#/atendimento', '#/workflow']

test('varredura axe de cada contexto (informativa)', async ({ page }, info) => {
  await entrar(page, 'demo-admin')
  const resumo: Record<string, string[]> = {}
  for (const rota of rotas) {
    await page.goto(`/${rota}`)
    await page.getByRole('heading', { level: 1 }).waitFor()
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    resumo[rota] = violations.map(v => `${v.impact ?? 'n/d'} · ${v.id} · ${v.nodes.length} nó(s)`)
  }
  await info.attach('axe-resumo.json', { body: JSON.stringify(resumo, null, 2), contentType: 'application/json' })
  console.log('axe:', JSON.stringify(resumo, null, 2))
})
