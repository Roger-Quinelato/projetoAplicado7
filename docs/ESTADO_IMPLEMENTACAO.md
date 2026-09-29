# Estado verificado da implementação

Data: 27/09/2026, atualizado em 29/09/2026 com a sprint Q3 (T06–T09). Este registro separa o que o código local executa, o que a documentação projeta e o que ainda depende de validação externa. A execução no Render/Supabase não foi verificada nesta data.

| Área | Existe no repositório | Limite verificado |
|---|---|---|
| CRM | Clientes (criação, consulta com filtros e paginação, alteração e inativação), contatos (CRUD) e oportunidades com transições `OPEN` para `WON`/`LOST`; validação, auditoria e matriz de papéis testadas | Dados sintéticos; sem CRM externo; remoção física de cliente não é oferecida |
| Reservas/contratos | Reserva idempotente com cancelamento, rascunho a partir da reserva na mesma transação, ativação idempotente com revalidação do cliente, encerramento idempotente com `ContractClosed.v1` e máquina de estados única | Sem disponibilidade real de frota, assinatura ou preço externo; Finance não consome `ContractClosed.v1` (faturamento final em T12) |
| Financeiro | Primeira fatura por evento, pagamento simulado, saldo e vencimento | Sem PSP, conciliação bancária, nota fiscal ou cobrança real |
| Atendimento | Abertura, SLA, atribuição, resolução e reconciliação de elegibilidade | Sem central de atendimento externa |
| Workflow | Processo e tarefa por evento, proprietário, prazo e transições | Sem motor BPM externo |
| Integração | Outbox/inbox, correlação, auditoria, despacho, falhas e reprocessamento | Consumidores internos são invocados pelo despachante; RabbitMQ recebe cópia opcional, não entrega aos consumidores |
| Segurança | Papéis por token local; no modo público, segredo aleatório em variável de ambiente; inicialização PostgreSQL ativa RLS e revoga acesso Data API `anon`/`authenticated` às tabelas do protótipo | Sem OIDC/OAuth ou contas individuais; credencial pública compartilhada; RLS ainda não verificada em Supabase real |
| Observabilidade | Logs, métricas básicas, trilha por correlação e health checks | Sem tracing distribuído ou painel externo |
| Interface | React/TypeScript com telas e ações dos cinco contextos; build e inspeção local de cadastro aprovados | Falta teste na URL HTTPS pública |
| Dados e migrações | UUID global por entidade; mapeamento `integration_legacy_ids` com consulta por API; esquema versionado com Alembic e migrações aditivas (ADR-002); carga sintética idempotente em `scripts/seed_sintetico.py` | Upgrade automático verificado em SQLite nos testes; PostgreSQL do Supabase/Render não verificado |
| Contrato de erro | Corpo único `application/problem+json` (RFC 9457) com `code` e `correlationId`; unicidade violada retorna `409` | `detail` de `422` mantém a lista da versão 1 por compatibilidade |
| Hospedagem | Dockerfile único, `render.yaml`, URL relativa e banco configurável; imagem Docker compilada no GitHub Actions | Contas Render/Supabase, inicialização PostgreSQL e teste HTTPS ainda pendentes |

O catálogo T01–T22 e os prazos internos estão em `CRONOGRAMA_EXECUCAO.md`. Os estados e links externos são atualizados manualmente, sem promessa de sincronização automática. A entrega final requer nomes dos integrantes, contribuições individuais e validação docente das premissas/datas.

Em 27/09/2026, as 22 tarefas também foram criadas como [GitHub Issues](https://github.com/Roger-Quinelato/projetoAplicado7/issues), cada uma com link para seu registro `ARCH7` no Jira. Sete marcos Q1–Q7 e etiquetas de semana, tipo, prioridade e status permitem navegar pelo cronograma. O [PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/pull/2) contém a implementação. O GitHub Project permanece pendente de escopo de acesso.
