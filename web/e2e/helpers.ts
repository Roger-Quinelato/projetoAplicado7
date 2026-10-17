import { expect, type Page } from '@playwright/test'

/** Dados sintéticos únicos por execução: o banco de teste é novo, mas o roteiro pode rodar de novo no mesmo. */
export function dadosUnicos(prefixo = 'e2e') {
  const sufixo = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
  return { nome: `Cliente ${prefixo} ${sufixo}`, email: `${prefixo}-${sufixo}@example.com` }
}

/** Preenche a tela de acesso sem esperar o resultado. */
export async function informarCredencial(page: Page, token: string) {
  await page.goto('/')
  await page.getByLabel('Credencial de acesso').fill(token)
  await page.getByRole('button', { name: 'Acessar demonstração' }).click()
}

/** Entra com um token local `demo-*` e espera a navegação dos contextos. */
export async function entrar(page: Page, token: string) {
  await informarCredencial(page, token)
  await expect(page.getByRole('navigation', { name: 'CONTEXTOS' })).toBeVisible()
}

export function irPara(page: Page, rotulo: string) {
  return page.getByRole('navigation', { name: 'CONTEXTOS' }).getByRole('link', { name: rotulo, exact: true }).click()
}
