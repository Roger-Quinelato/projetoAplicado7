import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, informarCredencial, irPara } from './helpers'

test('papel sem permissão recebe a negativa ao cadastrar cliente', async ({ page }) => {
  const { nome, email } = dadosUnicos('acesso')
  await entrar(page, 'demo-support')
  await expect(page.getByText('Perfil local: support').first()).toBeVisible()

  await irPara(page, 'CRM')
  const form = page.getByRole('form', { name: 'Novo cliente' })
  await form.getByLabel('Nome', { exact: true }).fill(nome)
  await form.getByLabel('E-mail', { exact: true }).fill(email)
  await form.getByRole('button', { name: 'Cadastrar cliente' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Cadastro de cliente' }))
    .toContainText('Seu perfil não pode fazer esta ação.')
})

test('credencial inválida é recusada na tela de acesso', async ({ page }) => {
  await informarCredencial(page, 'credencial-invalida')
  await expect(page.getByRole('alert')).toContainText('Credencial não aceita')
  await expect(page.getByRole('navigation', { name: 'MENU' })).toHaveCount(0)
})

test('Sair encerra a sessão e limpa a credencial', async ({ page }) => {
  await entrar(page, 'demo-admin')
  await page.getByRole('button', { name: 'Sair' }).click()
  await expect(page.getByLabel('Credencial de acesso')).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('archcorp-demo-token'))).toBeNull()
})
