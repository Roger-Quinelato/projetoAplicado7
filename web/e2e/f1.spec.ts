import { expect, test } from '@playwright/test'
import { dadosUnicos, entrar, irPara } from './helpers'

test('F1: cliente elegível → reserva → edição → ativação gera contrato para o mesmo cliente', async ({ page }) => {
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

  await test.step('edita a reserva solicitada (upgrade de grupo e novo valor)', async () => {
    const reservas = page.getByRole('region', { name: 'Tabela: Reservas' })
    const linha = reservas.getByRole('row').filter({ hasText: nome })
    await expect(linha).toContainText('Solicitada')
    await linha.getByRole('button', { name: 'Editar…' }).click()
    const form = page.getByRole('form', { name: 'Editar reserva' })
    await expect(form.getByLabel('Valor (R$)')).toHaveValue('1200.00')
    await form.getByLabel('Grupo de veículo').selectOption('SUV')
    await form.getByLabel('Valor (R$)').fill('1500.00')
    await form.getByRole('button', { name: 'Salvar alterações' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Dados atualizados' })).toBeVisible()
    await expect(linha).toContainText('SUV')
    await expect(linha).toContainText('Solicitada')
  })

  await test.step('ativa a reserva e o contrato nasce para o mesmo cliente', async () => {
    const reservas = page.getByRole('region', { name: 'Tabela: Reservas' })
    const linha = reservas.getByRole('row').filter({ hasText: nome })
    await linha.getByRole('button', { name: 'Ativar' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Ativação da reserva' })).toBeVisible()
    await expect(linha).toContainText('Ativa')
    const contratos = page.getByRole('region', { name: 'Tabela: Contratos' })
    await expect(contratos.getByRole('row').filter({ hasText: nome })).toContainText('Ativo')
  })

  await test.step('despacha o evento da ativação para não deixar pendência para os outros roteiros', async () => {
    const barra = page.getByRole('region', { name: 'Eventos de integração' })
    await barra.getByRole('button', { name: 'Despachar eventos' }).click()
    await expect(barra).toContainText('1 evento entregue, nenhuma falha.')
  })
})
