# DDD - Modelo de Dominio Localiza

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Linguagem Ubiqua

| Termo | Definicao no projeto |
|---|---|
| Cliente | Pessoa ou empresa que realiza locacao ou contrata mobilidade corporativa. |
| Gestor de frota | Representante corporativo que acompanha reservas, contratos e faturas. |
| Reserva | Intencao operacional de locacao antes da ativacao/retirada. |
| Contrato de locacao | Acordo ativo com periodo, grupo de veiculo, protecoes, valores e condicoes. |
| Grupo de veiculo | Categoria comercial usada na reserva e no contrato. |
| SLA | Prazo ou nivel de atendimento associado ao contrato e ao tipo de ocorrencia. |
| Chamado | Solicitacao de atendimento, assistencia, duvida, manutencao ou ocorrencia. |
| Processo operacional | Sequencia de tarefas para retirada, devolucao, vistoria, manutencao ou resolucao. |
| Correlacao | Identificador que permite rastrear a operacao entre sistemas. |

## Bounded Contexts

| Contexto | Entidades principais | Fonte oficial |
|---|---|---|
| CRM | Cliente, contato, consentimento, oportunidade | Dados cadastrais e elegibilidade comercial. |
| Contracts | Reserva, contrato, item de locacao, SLA | Condicoes da locacao e status contratual. |
| Finance | Cobranca, fatura, pagamento, adicional | Valores, vencimentos, pagamentos e pendencias. |
| Support | Chamado, historico, prioridade | Atendimento e resolucao da ocorrencia. |
| Workflow | Processo, tarefa, responsavel, prazo | Estado operacional da retirada, devolucao e atendimento. |
| Integration | Mapeamento legado, outbox, inbox, falha | Rastreabilidade e entrega confiavel. |

## Relacoes Entre Contextos

- CRM fornece dados de cliente para Contracts por `CustomerReader`.
- Contracts fornece elegibilidade para Support por `ContractEntitlementPort`.
- Contracts publica `ContractActivated.v1` para Finance e Workflow.
- Support publica `TicketOpened.v1` para Workflow.
- Integration nao decide regras de negocio; apenas traduz, correlaciona,
  entrega e registra falhas.

## Agregados e Regras

- **Cliente:** deve ter identificador global e consentimento antes de originar
  contrato no fluxo academico.
- **Contrato de locacao:** so pode ser ativado uma vez; reexecucao retorna a
  mesma resposta idempotente.
- **Cobranca:** e unica por contrato no fluxo de primeira cobranca.
- **Chamado:** pode abrir como pendente quando a elegibilidade nao estiver
  disponivel; reconciliacao posterior confirma ou rejeita.
- **Processo operacional:** e unico por tipo e referencia de negocio.

## Eventos de Dominio

- `CustomerUpdated.v1`: CRM alterou dado cadastral relevante.
- `ContractActivated.v1`: contrato de locacao foi ativado.
- `TicketOpened.v1`: chamado de atendimento foi registrado.

## Invariantes

- Nenhum contexto acessa tabela interna de outro contexto.
- Reentrega do mesmo evento nao duplica efeito de negocio.
- Fonte oficial vence conflitos; divergencia vira registro auditavel.
- Mudanca incompatível exige nova versao de contrato ou evento.
