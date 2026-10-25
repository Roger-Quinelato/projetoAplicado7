import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Visão geral', exact: true })).toBeVisible()
})

for (const name of ['Visão geral', 'CRM', 'Reservas e contratos', 'Financeiro', 'Atendimento', 'Workflow']) {
  test(`acessibilidade automática: ${name}`, async ({ page }) => {
    await page.getByRole('button', { name, exact: true }).click()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(result.violations).toEqual([])
  })
}

test('navegação por teclado alcança e ativa o CRM', async ({ page }) => {
  const button = page.getByRole('button', { name: 'CRM', exact: true })
  let reached = false
  for (let index = 0; index < 20; index++) {
    await page.keyboard.press('Tab')
    if (await button.evaluate(element => document.activeElement === element)) {
      reached = true
      break
    }
  }
  expect(reached).toBe(true)
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'CRM', exact: true })).toBeVisible()
})

test('acessibilidade automática da tela de acesso', async ({ page }) => {
  await page.getByRole('button', { name: 'Sair', exact: true }).click()
  await expect(page.getByLabel('Credencial de acesso')).toBeVisible()
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(result.violations).toEqual([])
})
