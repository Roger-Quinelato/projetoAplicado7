import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

test('CRM: inativar pede confirmação nomeada e só inativa quando confirmado', async ({ page }) => {
  const { nome, email } = dadosUnicos('crm')
  await entrar(page, 'demo-admin')
  await irPara(page, 'CRM')

  await page.getByRole('button', { name: 'Novo cliente' }).click()
  const form = page.getByRole('form', { name: 'Novo cliente' })
  await form.getByLabel('Nome (fictício)').fill(nome)
  await form.getByLabel('E-mail sintético').fill(email)
  await form.getByRole('button', { name: 'Cadastrar cliente' }).click()
  await expect(page.getByRole('status').filter({ hasText: nome })).toContainText('cadastrado')

  const linha = page.getByRole('region', { name: 'Tabela: Clientes' }).getByRole('row').filter({ hasText: email })
  await linha.getByRole('button', { name: `Mais ações: ${nome}` }).click()
  await page.getByRole('menuitem', { name: 'Inativar…' }).click()
  const dialogo = page.getByRole('dialog', { name: `Inativar ${nome}?` })
  await expect(dialogo).toBeVisible()
  await dialogo.getByRole('button', { name: 'Manter ativo' }).click()
  await expect(dialogo).toHaveCount(0)
  await expect(linha).toContainText('Ativo')

  await linha.getByRole('button', { name: `Mais ações: ${nome}` }).click()
  await page.getByRole('menuitem', { name: 'Inativar…' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Inativar cliente' }).click()
  await expect(page.getByRole('status').filter({ hasText: `Cliente ${nome} inativado.` })).toBeVisible()
  // Com o filtro padrão (ativos), o cliente inativado sai da tabela.
  await expect(page.getByRole('region', { name: 'Tabela: Clientes' }).getByRole('row').filter({ hasText: email })).toHaveCount(0)
})

test('CRM: menu "Mais" fecha com Esc e devolve o foco ao botão', async ({ page }) => {
  const { nome, email } = dadosUnicos('menu')
  await entrar(page, 'demo-admin')
  await irPara(page, 'CRM')
  await page.getByRole('button', { name: 'Novo cliente' }).click()
  const form = page.getByRole('form', { name: 'Novo cliente' })
  await form.getByLabel('Nome (fictício)').fill(nome)
  await form.getByLabel('E-mail sintético').fill(email)
  await form.getByRole('button', { name: 'Cadastrar cliente' }).click()
  const botao = page.getByRole('button', { name: `Mais ações: ${nome}` })
  await botao.click()
  await expect(page.getByRole('menuitem', { name: 'Editar' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu')).toHaveCount(0)
  await expect(botao).toBeFocused()
})
