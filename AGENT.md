# AGENT.md

Estado em 27/09/2026: este arquivo contém diretrizes obrigatórias de evolução. Para comportamento já implementado e limites verificados, consulte `docs/ESTADO_IMPLEMENTACAO.md`; para demandas e prazos, `docs/CRONOGRAMA_EXECUCAO.md`. OIDC, tracing distribuído, fila de erro no broker e escalabilidade horizontal são metas, não funcionalidades comprovadas do protótipo.

## Regras permanentes para agentes

As regras **SEMPRE** são requisitos de execução em toda tarefa. As regras **NUNCA** são proibições. Uma meta arquitetural não comprova que a funcionalidade existe: confirme o código, os testes e `docs/ESTADO_IMPLEMENTACAO.md` antes de descrever o estado do sistema.

### SEMPRE

- Leia este guia, o `README.md` e as instruções da pasta que será alterada; consulte também a fonte de verdade e os contratos pertinentes antes de implementar.
- Trate o enunciado acadêmico como fonte primária dos requisitos. Identifique premissas e pontos pendentes de validação como tais.
- Diferencie, em toda documentação e comunicação, comportamento implementado, decisão aprovada, arquitetura desejada e hipótese ainda não validada.
- Preserve o caráter de protótipo acadêmico: use dados sintéticos e adaptadores/simuladores; descreva cada dependência real como requisito futuro até que sua conexão seja comprovada.
- Respeite os limites dos módulos e o proprietário dos dados. Faça mudanças estruturais somente com decisão arquitetural registrada em ADR.
- Ao alterar comportamento, API, evento, arquitetura ou operação, atualize na mesma mudança os contratos, documentação, diagramas e rastreabilidade afetados.
- Verifique a mudança com testes proporcionais ao risco, incluindo falhas, reentrega e idempotência quando aplicável; informe com precisão o que foi e não foi executado.
- Antes de declarar uma publicação pronta, confirme URL HTTPS, health checks, operações de escrita/leitura e persistência após reinício, além da configuração segura de segredos.

### NUNCA

- Afirme ou sugira que o protótipo acessa, sincroniza ou integra sistemas reais da Localiza; não há essa conexão comprovada.
- Apresente OIDC/OAuth, tracing distribuído, fila de erro no broker, escala horizontal, deploy público ou integração externa como implementados sem evidência verificável.
- Inclua dados pessoais reais, credenciais, tokens, senhas, dados bancários ou conteúdo sensível de chamados em código, logs, exemplos, issues ou documentação.
- Grave segredos no Git. Para a demonstração pública, configure `DEMO_ACCESS_TOKEN` e demais credenciais somente no ambiente seguro do provedor.
- Acesse tabelas, classes internas, repositórios ou regras de negócio de outro módulo; use o banco compartilhado como canal de integração entre módulos.
- Oculte falhas, capture exceções sem tratamento observável, remova ou enfraqueça testes para obter aprovação, ou marque uma entrega como concluída sem atender aos critérios deste guia.
- Substitua sistemas corporativos, introduza microsserviços/Kubernetes ou amplie os fluxos do protótipo sem requisito explícito, necessidade demonstrada e decisão arquitetural.
- Converta uma hipótese sobre a organização, os sistemas existentes, os responsáveis ou as datas em fato documentado.

## Missão do repositório

Este repositório contém o Projeto Aplicado de Arquitetura de Sistemas Corporativos para o Cenário 4 - Localiza - locação de veículos e mobilidade corporativa. O objetivo é demonstrar, de forma executável e documentada, a integração entre CRM, reservas e contratos, financeiro e faturamento, atendimento e assistência 24h e gestão de processos operacionais.

## Fontes de verdade

Antes de alterar o projeto, leia nesta ordem:

1. `Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf` - requisitos acadêmicos.
2. `PLANO_IMPLEMENTACAO_CENARIO_4.md` - escopo, requisitos, fluxos e critérios de aceite.
3. `docs/adr/ADR-001-integracao-empresa-de-servicos.md` - decisão arquitetural vigente.
4. Demais ADRs, OpenAPI/AsyncAPI e documentação do módulo afetado.

Em caso de conflito, o enunciado tem precedência. Não transforme premissas do plano em fatos: marque-as e mantenha uma lista de pontos a validar.

## Idioma e documentação

- Escreva documentação, decisões e mensagens de negócio em português do Brasil.
- Use inglês apenas para nomes técnicos convencionais, identificadores de código, endpoints e campos de API.
- Atualize documentação e diagramas na mesma mudança que altera arquitetura ou contrato.
- Crie um novo ADR para decisões estruturais; não reescreva silenciosamente uma decisão aceita.

## Arquitetura obrigatória

- Manter uma SOA pragmática entregue inicialmente como monólito modular.
- Organizar os contextos: `crm`, `contracts`, `finance`, `support`, `workflow` e `integration`.
- Aplicar arquitetura hexagonal: domínio e casos de uso não dependem de HTTP, banco, broker ou SDK externo.
- Usar interfaces públicas entre módulos. É proibido acessar diretamente tabelas, classes internas ou repositórios de outro módulo.
- Colocar regras de negócio no módulo proprietário. A integração traduz, roteia, correlaciona e orquestra; ela não deve se tornar dona das regras dos cinco sistemas.
- Acessar sistemas externos somente por adaptadores substituíveis por simuladores nos testes.
- Preservar as fronteiras mesmo que o protótipo use um único processo e um único servidor PostgreSQL.

## Propriedade dos dados

| Contexto | Fonte oficial |
|---|---|
| CRM | Cliente, contatos, consentimentos e oportunidade |
| Contracts | Reserva, contrato de locação, grupo de veículo, vigência, proteções e SLA |
| Finance | Pré-autorização, cobrança, fatura, pagamento, caução, multa e inadimplência |
| Support | Chamado, assistência, prioridade, histórico e resolução |
| Workflow | Instância, tarefa, responsável, prazo e estado operacional do processo |
| Integration | Mapeamento de IDs legados, correlação, outbox/inbox e falhas |

Cada entidade compartilhada usa UUID global e pode manter identificadores legados associados ao sistema de origem. Em divergências, não aplique estratégia de "última escrita vence" sem uma decisão explícita; preserve a fonte oficial e registre a inconsistência.

## Reservas e contratos de integração

- REST/JSON para comandos e consultas que exigem resposta imediata.
- Eventos para fatos confirmados e efeitos desacoplados.
- APIs sob `/api/v1`; documentar em OpenAPI.
- Documentar eventos em AsyncAPI ou JSON Schema.
- Envelope obrigatório de evento: `eventId`, `eventType`, `eventVersion`, `occurredAt`, `correlationId`, `causationId`, `producer` e `payload`.
- Datas e horas em ISO 8601 UTC; valores monetários em decimal com moeda explícita; conteúdo em UTF-8.
- Mudanças incompatíveis exigem nova versão. Mudanças compatíveis devem ser aditivas.
- Propagar `correlationId` em HTTP, logs, eventos e registros de erro.

## Confiabilidade e erros

- Use outbox transacional para publicar eventos relacionados a mudanças persistidas.
- Consumidores devem ser idempotentes e registrar `eventId` processado.
- Comandos mutáveis expostos por HTTP devem aceitar `Idempotency-Key` quando puderem ser repetidos.
- Defina timeout em chamadas externas; aplique retentativa apenas a erros transitórios e com atraso exponencial e jitter.
- Encaminhe falhas permanentes para fila de erro, preservando payload seguro, motivo, tentativas e correlação.
- Reprocessamento deve ser explícito, auditável e incapaz de duplicar efeitos de negócio.
- Nunca capture uma exceção sem registrar contexto ou convertê-la em resultado tratado.

## Segurança e privacidade

- Autenticação OIDC/OAuth 2.0 e autorização baseada em papéis nas rotas protegidas.
- Não armazene segredos, tokens ou senhas no repositório. Forneça apenas arquivos de exemplo sem valores reais.
- Valide todas as entradas na fronteira da aplicação.
- Não registre tokens, senhas, dados bancários, documentos completos nem conteúdo sensível de chamados.
- Minimize os dados presentes em APIs e eventos e mantenha trilha de auditoria para operações críticas.
- Use TLS fora do ambiente local de demonstração.

## Observabilidade

- Logs estruturados com horário, nível, módulo, operação, `correlationId` e resultado.
- Métricas mínimas: taxa e latência por operação, erros, retentativas, tamanho/idade da fila e mensagens não processadas.
- Traces devem atravessar API, adaptadores e consumidores.
- Disponibilize health checks separados para processo vivo e dependências prontas.

## Testes obrigatórios

Para cada mudança de comportamento, inclua testes proporcionais ao risco:

- unitários para regras de domínio e tradução;
- integração para banco, broker, outbox/inbox e adaptadores;
- contrato para OpenAPI e eventos;
- ponta a ponta para os três fluxos do plano;
- cenários de reentrega, timeout, indisponibilidade e falha permanente.

Uma correção de bug deve incluir teste que falha antes da correção. Não remova ou enfraqueça testes apenas para obter resultado verde.

## Fluxos mínimos que não podem regredir

1. CRM cria rascunho de contrato de locação sem recadastro.
2. Ativação do contrato cria cobrança e inicia preparação de retirada por evento, sem duplicidade.
3. Atendimento e assistência 24h consulta contrato/SLA, abre chamado e inicia processo de resolução.

## Forma de trabalho

1. Identifique o requisito e a fonte oficial afetados.
2. Confirme se a mudança respeita o ADR vigente; se não, proponha novo ADR antes de implementar.
3. Faça a menor mudança coerente e mantenha as fronteiras de módulo.
4. Atualize reservas e contratos antes ou junto da implementação.
5. Execute testes e verificações de contrato relevantes.
6. Atualize diagramas, exemplos e rastreabilidade do requisito.
7. Registre limitações, premissas e riscos ainda abertos.

## Critérios de conclusão de uma mudança

Uma tarefa só está concluída quando:

- comportamento e critérios de aceite estão atendidos;
- testes relevantes passam;
- logs não expõem dados sensíveis;
- reservas e contratos e documentação estão atualizados;
- migrações são reproduzíveis e têm estratégia de compatibilidade;
- falhas e reprocessamentos têm comportamento definido;
- não foi criado acesso indevido entre módulos;
- a execução local continua documentada e reproduzível.

## Restrições de escopo

- Não substituir os cinco sistemas por implementações completas sem solicitação explícita.
- Não introduzir Kubernetes, service mesh, múltiplos bancos físicos ou decomposição em microsserviços sem requisito mensurável e novo ADR.
- Não usar banco compartilhado como atalho entre módulos.
- Não criar novos fluxos antes de estabilizar os três fluxos obrigatórios.
- Não inventar fatos sobre a organização; documentar hipóteses como premissas a validar.

