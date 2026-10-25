import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Visão geral', exact: true })).toBeVisible()
})

test('navega pelos cinco contextos e apresenta coleções vazias', async ({ page }) => {
  for (const name of ['CRM', 'Reservas e contratos', 'Financeiro', 'Atendimento', 'Workflow']) {
    await page.getByRole('button', { name, exact: true }).click()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(page.getByText('Sem registros ainda.').first()).toBeVisible()
  }
})

test('preserva dados quando a API rejeita o cadastro', async ({ page }) => {
  await page.route('**/api/v1/crm/customers', route => route.request().method() === 'POST'
    ? route.fulfill({ status: 409, json: { detail: 'E-mail sintético já cadastrado' } })
    : route.fulfill({ json: [] }))
  await page.getByRole('button', { name: 'CRM', exact: true }).click()
  await page.getByLabel('Nome', { exact: true }).first().fill('Cliente Sintético')
  await page.getByLabel('E-mail sintético').fill('cliente@example.com')
  await page.getByRole('button', { name: 'Cadastrar cliente' }).click()
  await expect(page.getByRole('status')).toContainText('E-mail sintético já cadastrado')
  await expect(page.getByLabel('Nome', { exact: true }).first()).toHaveValue('Cliente Sintético')
  await expect(page.getByLabel('E-mail sintético')).toHaveValue('cliente@example.com')
})

test('bloqueia novo envio enquanto aguarda e limpa somente após sucesso', async ({ page }) => {
  let release: () => void = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  let submissions = 0
  await page.route('**/api/v1/crm/customers', async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: [] })
    submissions++
    await pending
    await route.fulfill({ status: 201, json: { customerId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' } })
  })
  await page.getByRole('button', { name: 'CRM', exact: true }).click()
  await page.getByLabel('Nome', { exact: true }).first().fill('Cliente Sintético')
  await page.getByLabel('E-mail sintético').fill('cliente@example.com')
  const submit = page.getByRole('button', { name: 'Cadastrar cliente' })
  await submit.click()
  try {
    await expect(submit).toBeDisabled()
    await expect(page.getByLabel('E-mail sintético')).toHaveValue('cliente@example.com')
  } finally {
    release()
  }
  await expect(page.getByRole('status')).toContainText('concluído')
  await expect(submit).toBeEnabled()
  await expect(page.getByLabel('E-mail sintético')).toHaveValue('')
  expect(submissions).toBe(1)
})
