# Avaliação dos atributos de qualidade

## Método de avaliação

A avaliação relaciona cada atributo exigido pelo guia a uma necessidade do
Cenário 4, ao risco que ameaça essa necessidade, à estratégia adotada e ao
resultado esperado. A coluna de evidência registra o que o protótipo demonstra
hoje. A coluna de limitações evita extrapolar resultados locais para um ambiente
de produção ainda desconhecido.

| Atributo | Necessidade | Risco | Estratégia adotada | Resultado esperado | Evidência atual | Limitações |
|---|---|---|---|---|---|---|
| Interoperabilidade | Integrar modelos, identificadores e tecnologias diferentes. | Vincular o cliente errado ou consumir um contrato incompatível. | UUID global, mapeamento legado, modelo canônico mínimo, adaptadores, OpenAPI e AsyncAPI. | Sistemas trocam apenas os dados necessários e evoluem por contratos versionados. | F1 preserva o mesmo `customerId`; os contratos descrevem APIs e eventos. | Produtos e formatos legados reais são **Premissa a validar**. |
| Confiabilidade | Preservar fatos e impedir efeitos duplicados. | Perder uma ativação ou criar cobrança e processo mais de uma vez. | Outbox transacional, inbox, `Idempotency-Key`, restrições únicas, retentativa controlada e fila de falha. | Reentregas produzem um único efeito de negócio e falhas permanecem recuperáveis. | Testes de F1 e F2 repetem operações sem duplicidade; o teste de falha permite reprocessamento. | O protótipo demonstra entrega local; disponibilidade real do broker não foi medida. |
| Segurança | Restringir operações e reduzir exposição de dados. | Usuário sem papel adequado executar uma ação ou dados sensíveis aparecerem em logs e eventos. | Bearer OIDC simulado, RBAC, validação de entrada, minimização de payload e TLS fora do ambiente local. | Somente papéis autorizados executam operações e os registros evitam dados proibidos. | Testes verificam resposta 403 e 422; `TicketOpened.v1` omite a descrição do chamado. | OIDC corporativo, gestão de chaves, TLS e testes de segurança externos não fazem parte da demonstração. |
| Observabilidade | Localizar uma operação que atravessa módulos. | Falha sem causa, etapa ou responsável identificável. | `correlationId`, logs estruturados, métricas, auditoria, eventos e health checks separados. | Uma consulta reúne a trilha da operação e a equipe identifica filas e falhas. | Middleware, `/metrics`, `/health/*` e `GET /api/v1/operations/{correlation_id}` estão implementados. | A correlação representa o trace no monólito; não há coletor distribuído externo. |
| Manutenibilidade | Alterar um contexto sem acessar detalhes internos de outro. | O monólito acumular dependências cruzadas e mudanças em cascata. | Arquitetura hexagonal, portas públicas, propriedade de dados e teste estático de fronteiras. | Mudanças permanecem localizadas e adaptadores podem ser substituídos. | O teste arquitetural rejeita importação cruzada de modelos entre contextos. | O teste não substitui revisão de regras, consultas SQL ou dependências indiretas futuras. |
| Disponibilidade | Preservar solicitações durante falha parcial. | A indisponibilidade de Contracts bloquear ou perder um chamado. | Timeout na porta externa, estado `PENDING_ENTITLEMENT` e reconciliação posterior. | O atendimento registra a solicitação e conclui a validação quando a dependência retorna. | O teste de F3 abre o chamado pendente e o reconcilia após restaurar Contracts. | Alta disponibilidade, failover e metas de recuperação de produção são **Premissa a validar**. |
| Desempenho | Responder consultas locais dentro da meta da demonstração. | Banco, serialização ou consultas aumentarem a latência. | API sem estado, índices, payload mínimo e medição automatizada. | Consultas locais apresentam p95 inferior a 500 ms no ambiente registrado. | `scripts/performance_smoke.py` mede 200 consultas; o resultado vigente fica em `docs/EVIDENCIAS_VALIDACAO.md`. | A medição exclui dependências simuladas lentas e não dimensiona produção. |
| Escalabilidade | Permitir aumento de usuários e eventos sem redesenhar os domínios. | API saturar ou a idade da fila crescer em picos. | API sem estado, consumidores idempotentes e escala por fila orientada por métricas. | Réplicas podem aumentar apenas no componente pressionado. | O desenho preserva esse caminho e expõe métricas operacionais básicas. | Não há volume organizacional, teste de carga representativo ou escala horizontal demonstrada. |
| Testabilidade | Reproduzir fluxos e falhas antes da apresentação. | Erros de integração aparecerem apenas na demonstração ou em produção. | Adaptadores substituíveis e testes de fluxo, contrato, autorização, falha e arquitetura. | A equipe detecta regressões nos três fluxos e nos controles principais. | A suíte cobre F1, F2, F3, reentrega, indisponibilidade, autorização, contratos e fronteiras. | Os testes usam SQLite e adaptadores internos; PostgreSQL, RabbitMQ e legados reais exigem validação adicional. |

## Metas operacionais do protótipo

- **Latência local:** p95 inferior a 500 ms para consultas locais, com 200
  amostras e exclusão de atrasos deliberados dos simuladores.
- **Idempotência:** zero cobrança, processo ou chamado duplicado com a mesma
  chave ou o mesmo `eventId`.
- **Rastreabilidade:** todas as rotas mutáveis devolvem
  `X-Correlation-ID`; operações críticas registram auditoria.
- **Recuperação:** uma falha permanente preserva evento, motivo, tentativas e
  correlação até reprocessamento explícito.
- **Privacidade:** logs estruturados não contêm token, senha, dado bancário,
  documento pessoal completo ou descrição de chamado.

## Interpretação e pendências

Os resultados atuais demonstram adequação ao protótipo acadêmico, não capacidade
de produção. Volumes, hardware de referência, disponibilidade requerida,
objetivos de recuperação, retenção e concorrência são **Premissa a validar**.
Quando esses dados existirem, a equipe deve transformar cada necessidade em um
cenário mensurável e reavaliar as estratégias e o ADR vigente.
