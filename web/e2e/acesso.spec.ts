import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, informarCredencial, irPara } from './helpers'

test('papel sem permissão recebe a negativa ao cadastrar cliente', async ({ page }) => {
  const { nome, email } = dadosUnicos('acesso')
  await entrar(page, 'demo-support')
  await expect(page.getByText('Perfil local: support').first()).toBeVisible()

  await irPara(page, 'CRM')
  await page.getByRole('button', { name: 'Novo cliente' }).click()
  const form = page.getByRole('form', { name: 'Novo cliente' })
  await form.getByLabel('Nome (fictício)').fill(nome)
  await form.getByLabel('E-mail sintético').fill(email)
  await form.getByRole('button', { name: 'Cadastrar cliente' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Não foi possível cadastrar o cliente.' }))
    .toContainText('Seu papel não tem permissão para esta operação.')
})

test('credencial inválida é recusada na tela de acesso', async ({ page }) => {
  await informarCredencial(page, 'credencial-invalida')
  await expect(page.getByRole('alert')).toContainText('Credencial ausente ou inválida')
  await expect(page.getByRole('navigation', { name: 'CONTEXTOS' })).toHaveCount(0)
})

test('Sair encerra a sessão e limpa a credencial', async ({ page }) => {
  await entrar(page, 'demo-admin')
  await page.getByRole('button', { name: 'Sair' }).click()
  await expect(page.getByLabel('Credencial de acesso')).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('archcorp-demo-token'))).toBeNull()
})
