# PRD - Modernizacao de Integracoes Localiza

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Contexto

O produto academico aplica o Cenario 4 do `Guia.pdf` a uma operacao inspirada na
Localiza. A organizacao possui sistemas separados para CRM, reservas e contratos
de locacao, financeiro e faturamento, atendimento e assistencia 24h e gestao de
processos operacionais. O problema central e a fragmentacao entre cadastro,
contrato, cobranca, preparacao do veiculo e atendimento ao cliente.

## Problema

Sem integracao padronizada, a mesma empresa ou cliente pode aparecer com
identificadores diferentes em canais, contrato, faturamento e atendimento. A
ativacao de uma locacao pode depender de lancamentos manuais para gerar cobranca
e iniciar preparacao de retirada. Durante um chamado, o atendimento pode nao ter
confirmacao confiavel de contrato, grupo de veiculo, protecoes e SLA.

## Publico-Alvo

- Equipe comercial e canais digitais.
- Operacao de reservas, retirada, devolucao e vistoria.
- Financeiro e faturamento.
- Atendimento e assistencia 24h.
- Gestores de frota e clientes corporativos.
- Gestao executiva que precisa de rastreabilidade e indicadores.

## Objetivos do Produto

1. Reduzir recadastro e duplicidade de cliente.
2. Criar reserva/contrato de locacao a partir do cadastro oficial do CRM.
3. Ativar locacao e disparar cobranca e preparacao de retirada sem acoplamento
   ponto a ponto.
4. Abrir chamado com contrato de locacao, grupo de veiculo e SLA aplicaveis.
5. Permitir rastreamento e reprocessamento de falhas por `correlationId`.

## Escopo P0

- Identidade global de cliente.
- Tres fluxos integrados F1, F2 e F3.
- Contratos OpenAPI e AsyncAPI.
- Outbox, inbox, idempotencia, auditoria e consulta de operacao.
- Documentacao AS-IS, TO-BE, ADR, requisitos, integracoes, qualidade, evolucao,
  roteiro, matriz de rastreabilidade, relatorio e apresentacao.

## Fora do Escopo

- Substituir sistemas reais da Localiza.
- Integrar pagamento, antifraude, telemetria, aplicativo, Webcorp ou sistemas de
  agencia reais.
- Migrar historico.
- Demonstrar alta disponibilidade de producao.

## Metricas de Sucesso

| Meta | Indicador academico |
|---|---|
| Integracao minima comprovada | Tres fluxos executados ponta a ponta. |
| Confiabilidade | Reentrega nao duplica cobranca, processo ou chamado. |
| Observabilidade | Operacao localizada por `correlationId`. |
| Manutenibilidade | Teste arquitetural impede dependencia indevida entre contextos. |
| Entrega do guia | Matriz de rastreabilidade cobre os itens exigidos. |

## Dependencias

As premissas de tecnologia, volumes, SLAs reais, dados pessoais, regras de
cobranca, regras de protecao, regras de sinistro e integrações corporativas
precisam ser validadas com professor ou representante da organizacao antes de
qualquer conclusao produtiva.
