# ADR-007: demonstração oficial local e retirada do Supabase

- Status: Aceito
- Data: 2026-10-29
- Decisor: Roger Quinelato, responsável pelo projeto
- Relaciona-se com ADR-001, ADR-002 e ADR-004

## Contexto

O plano do projeto previa publicar a demonstração no Render Free, com PostgreSQL no Supabase Free (T20, issues #23 e #64). Para isso, a inicialização da API ativava RLS e revogava os privilégios dos papéis `anon` e `authenticated` do Supabase em todas as tabelas (`protect_public_demo_tables`), coberta por `tests/test_public_database_security.py`.

Até 29/10/2026 a publicação não foi verificada: faltavam contas, segredos, URL HTTPS e um teste de persistência após reinício. O `Guia.pdf` não exige publicação: a demonstração pode usar protótipo funcional, sistemas simulados e Swagger. Restam 11 dias para a entrega de 09/11.

## Decisão

1. A demonstração oficial do projeto é **local**, com a API servindo a interface compilada (`web/dist`) a partir de SQLite ou do PostgreSQL do Docker Compose.
2. O **Supabase sai do projeto**: a função `protect_public_demo_tables`, sua chamada na inicialização e o teste correspondente foram removidos. O teste sai junto com a funcionalidade que verificava; não houve enfraquecimento de cobertura.
3. A publicação pública passa a ser **evolução futura**, fora do escopo da entrega. O `render.yaml` permanece como artefato opcional e **não verificado**: se for usado, `DATABASE_URL` deve apontar para um PostgreSQL escolhido no momento da publicação.
4. O modo público (`PUBLIC_DEMO=true` com `DEMO_ACCESS_TOKEN`) continua no código, porque protege qualquer exposição da API pela rede, inclusive numa rede local.

## Consequências

- A T20 (ARCH7-20, issues #23 e #64) fica fora do escopo da entrega.
- Os requisitos de disponibilidade e de segurança do banco publicado deixam de ter uma verificação pendente na entrega: eles se tornam estratégia de evolução (`docs/EVOLUCAO_MANUTENCAO.md`).
- Uma publicação futura em qualquer PostgreSQL gerenciado precisa reavaliar a exposição direta das tabelas pelo provedor (por exemplo, APIs de dados automáticas) e registrar a proteção em novo ADR.
- A suíte não contém mais testes ligados ao Supabase. Os testes ignorados localmente continuam sendo apenas os que exigem PostgreSQL ou RabbitMQ reais.
- Documentos de pesquisa e registros históricos que citam o Supabase (`BENCHMARK_BANCOS_SEMESTRE.md`, `PESQUISA_BANCOS_FONTES.md`, `EVIDENCIAS_VALIDACAO.md`) são preservados como histórico.
