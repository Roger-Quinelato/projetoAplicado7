import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

test('F1: cliente elegível → reserva → rascunho de contrato para o mesmo cliente', async ({ page }) => {
  const { nome, email } = dadosUnicos('f1')
  await entrar(page, 'demo-admin')

  await test.step('cadastra o cliente no CRM', async () => {
    await irPara(page, 'CRM')
    const form = page.getByRole('form', { name: 'Novo cliente' })
    await form.getByLabel('Nome (fictício)').fill(nome)
    await form.getByLabel('E-mail sintético').fill(email)
    await form.getByLabel('Elegível para contratar').check()
    await form.getByLabel('Consentimento de serviço').check()
    await form.getByRole('button', { name: 'Cadastrar cliente' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Cadastro de cliente' })).toContainText(nome)
    await expect(page.getByRole('row').filter({ hasText: email })).toBeVisible()
  })

  await test.step('registra a reserva', async () => {
    await irPara(page, 'Reservas e contratos')
    const form = page.getByRole('form', { name: 'Nova reserva' })
    await form.getByLabel('Cliente (CRM)').selectOption({ label: `${nome} · ${email}` })
    await form.getByRole('button', { name: 'Registrar reserva' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'solicitada' })).toBeVisible()
  })

  await test.step('gera o rascunho a partir da reserva', async () => {
    const reservas = page.getByRole('region', { name: 'Tabela: Reservas' })
    const linha = reservas.getByRole('row').filter({ hasText: nome })
    await expect(linha).toContainText('Solicitada')
    await linha.getByRole('button', { name: 'Gerar rascunho' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'em rascunho para o mesmo cliente' })).toBeVisible()
    await expect(linha).toContainText('Com rascunho')
  })

  await test.step('o contrato aparece em rascunho para o mesmo cliente', async () => {
    const contratos = page.getByRole('region', { name: 'Tabela: Contratos' })
    await expect(contratos.getByRole('row').filter({ hasText: nome })).toContainText('Rascunho')
  })
})
