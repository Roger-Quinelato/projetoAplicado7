# ArchCorp: produto, funcionalidades e próximos passos

Levantamento em 19/10/2026 para preparar o planejamento de implementação no Astra.

## 1. O que estamos construindo

Um protótipo acadêmico de integração para uma operação de locação de veículos e mobilidade corporativa inspirada na Localiza. A ArchCorp representa a equipe que propõe a modernização. O valor do produto é evitar recadastro, lançamentos repetidos e perda de informação entre comercial, contratos, financeiro, atendimento e operações.

O público principal é interno: comercial, reservas/contratos, financeiro, suporte e operações. O cliente da locação se beneficia indiretamente. Um portal de autoatendimento do cliente não está estabelecido como entrega obrigatória.

O enunciado `Guia.pdf` define o Cenário 4 como empresa de serviços e cinco sistemas. A aplicação à Localiza é a contextualização do repositório; não foi localizado o PDF específico Localiza mencionado em `AGENT.md`. Produtos, processos e SLAs internos reais da empresa permanecem hipóteses.

**Financeiro não significa financiamento:** há faturamento da locação e registro de pagamentos; não foi identificado requisito de empréstimo, análise de crédito, juros de financiamento ou compra financiada de veículos.

## 2. Produto, oferta e entregáveis são coisas diferentes

| Item | O que significa no projeto |
|---|---|
| Produto de software | ArchCorp, demonstrador web de operações integradas, com cinco contextos de negócio e uma camada de integração. |
| Oferta de locação do exemplo | `RENTAL-FLEX`, código de serviço usado nos contratos e chamados. Não é evidência de produto comercial real da Localiza. |
| Configuração da locação | Grupo de veículo, proteção, período, valor/moeda, ciclo de cobrança e SLA. Não existe evidência de catálogo completo com preços, estoque e disponibilidade reais. |
| Entregáveis acadêmicos | Protótipo, código/testes, requisitos, AS-IS/TO-BE, diagramas, ADRs, APIs/eventos, qualidade, evolução, viabilidade, demonstração e relatório técnico de 15–20 páginas. |

Pré-autorização, caução, multas, condutores, vistoria, manutenção, sinistro e devolução aparecem como responsabilidades possíveis do domínio em documentos. Essa menção não comprova implementação nem torna todos esses fluxos obrigatórios nesta entrega.

## 3. Atenção: duas versões precisam ser reconciliadas

- Checkout local: branch `execucao-tarefas-pendentes`, HEAD `3fdb53302bfbc9277e40b7a4698c8a6c3c0943dd`, com alterações anteriores em documentação e evidências. Não foram modificadas por este levantamento.
- `main` consultada diretamente no GitHub: `cf155ee12809cfed30b1cff5980e566bd7d34d6e`. Há diferenças relevantes no código e no estado documentado.
- A auditoria local de 17/10 avaliou o primeiro commit, não a `main` atual. Ela registra 84 testes Python, 11 testes de navegador com API simulada e 37 verificações com navegador/API/PostgreSQL/RabbitMQ locais.
- O estado documentado na `main` relata 211 testes aprovados e 10 ignorados em uma execução anterior. Essa execução não foi repetida neste levantamento e não equivale à auditoria do checkout local.

Portanto, não somar contagens, não transferir resultados entre versões e não declarar um problema resolvido em ambas sem testar a versão escolhida. A primeira tarefa do Astra deve ser fixar uma base e comparar as diferenças, preservando as garantias de cada versão.

## 4. Funcionalidades existentes e lacunas

| Módulo / capacidade | Checkout local | `main` remota consultada | O que planejar |
|---|---|---|---|
| CRM: cadastro de clientes | API cria, consulta, filtra, pagina, edita e inativa; validação e UUID global. Interface oferece cadastro e listagem básicos. | Interface também oferece filtros, paginação, edição e inativação. | Unificar a versão; corrigir seleção de clientes além da primeira página. |
| CRM: contatos e oportunidades | CRUD de contatos e oportunidades `OPEN` → `WON`/`LOST` na API; UI expõe parte das ações. | Interface mais completa, incluindo ações de contatos e oportunidades ganhas/perdidas. | Mapear cobertura de cada ação na UI e permissões. Não confundir cliente cadastrado com usuário de login. |
| Reserva e contrato | Reserva/cancelamento, rascunho sem recadastro, ativação e encerramento idempotentes na API; UI expõe reserva, rascunho, ativação e encerramento. | UI também expõe cancelamento e rascunho direto. Leitura resiliente do CRM documentada no ADR-006. | Validar estados, repetição, indisponibilidade e resposta perdida; sem estoque real de frota. |
| Financeiro básico | Primeira fatura após evento; pagamento parcial/total simulado, saldo e vencimento. | Ciclo explícito `OPEN`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`, `CANCELLED`; saldo, inadimplência e cancelamento condicionado. | Reaproveitar implementação existente e validar regras/premissas. |
| Financeiro final | Encerramento emite evento, mas Finance não o consome; sem acerto final. | `finance/domain.py` e documentação mostram faturamento final por `ContractClosed.v1`, descontando o já faturado, com ciclos iniciados. | Não recriar esta feature. Conferir migração, aceite e regras de cálculo na base escolhida. Não confundir cálculo final com agendador de cobrança recorrente. |
| Pagamento por provedor | Pagamento simulado. | Pagamento simulado; issue #56 propõe Mercado Pago sandbox. | Evolução proposta e ainda não implementada no código examinado. |
| Atendimento | Abertura, contrato/SLA, prioridade, responsável, resolução e reconciliação de elegibilidade. | Acrescenta histórico próprio, situação do SLA, relógio de teste e reconciliação individual/em lote. | Preservar cálculo do prazo desde a abertura; comprovar integração com Workflow e limites de autorização. |
| Workflow | Processos/tarefas por eventos; responsáveis, prazos e transições; proteção de estados finais documentada/testada. | Processos e tarefas existem; prazo de atendimento acompanha Support. Código de alteração de tarefa tem política menos restritiva que a local; prazo de preparação ainda parte do despacho. | Comparar regras; proteger estados finais, agregação e prazo; separar correção de nova funcionalidade. |
| Integração e recuperação | Outbox/inbox, idempotência, rollback, falhas, reprocessamento e correlação; várias consultas são demonstráveis via API. | UI inclui falhas/reprocessamento e consulta da trilha; despachante usa savepoint e tratamento de falha de commit. | Issue #34 é parcialmente histórica: revalidar cada item, sem assumir que a falha SQL continua aberta tecnicamente. |
| Acesso e segurança | Tokens locais por papel; modo público com segredo compartilhado. Auditoria encontrou bloqueio indevido de papel financeiro na UI local. | Login aceita credencial autenticada mesmo com 403 na consulta administrativa inicial, corrigindo esse mecanismo de bloqueio no código. Recursos continuam sujeitos a 403 por papel. | Testar todos os papéis na versão final. Sem contas individuais/OIDC comprovados. |
| Observabilidade | Auditoria, logs, métricas básicas, correlação e health checks. | Mesmas capacidades, com evolução de proteção/formato de métricas. | Sem tracing distribuído ou painel externo comprovados. |
| Banco e execução | SQLite de desenvolvimento; PostgreSQL e RabbitMQ testados localmente em ambiente isolado; Alembic e seed sintético. | Migrações adicionais, inclusive ciclo financeiro. | Validar conjunto consolidado em PostgreSQL. RabbitMQ recebe cópia: consumidores continuam internos. |
| Publicação | Dockerfile e `render.yaml` preparados; publicação não comprovada. | Documentação continua registrando validação externa pendente. | T20: URL HTTPS, health, escrita/leitura, reinício, persistência e segredos no provedor. |

## 5. O que apresentar funcionando

1. **F1 — cadastro para contratação:** cadastrar cliente e contato, opcionalmente uma oportunidade; criar reserva e gerar contrato reaproveitando o mesmo cliente, sem recadastro. Repetir comando e demonstrar que não duplica.
2. **F2 — ativação para faturamento e operação:** ativar contrato, despachar os eventos e mostrar a primeira fatura e o processo de preparação de retirada. Registrar pagamento simulado parcial e total. Reentregar evento e conferir uma única cobrança/processo. Faturamento final é demonstrável depois de consolidar e validar a implementação da `main`.
3. **F3 — atendimento com contrato e SLA:** abrir chamado vinculado a contrato válido; mostrar prioridade, prazo, responsável e processo de resolução. Resolver e acompanhar Workflow. Demonstrar estado pendente e reconciliação quando a consulta de elegibilidade falha.
4. **Prova de qualidade:** localizar operação pela correlação e provocar falha controlada/reprocessamento, preservando idempotência e sem dados pessoais reais.

Explicar que o despacho é explícito. Não prometer geração imediata em segundo plano nem processamento por consumidores externos RabbitMQ.

Além da aplicação, a apresentação deve cobrir problema/valor de negócio, AS-IS/TO-BE, decisões arquiteturais, três integrações, exemplo de interoperabilidade, pelo menos cinco atributos de qualidade, evolução e limitações. O relatório DOCX e os slides PPTX existem localmente, mas precisam refletir a versão final consolidada, além de nomes e contribuições dos integrantes.

## 6. Issues abertas consultadas

Foram encontradas 13 issues abertas nesta consulta. São registros de trabalho, não uma lista confiável de funcionalidades ausentes.

| Issue | Interpretação para o planejamento |
|---|---|
| [#56 — Mercado Pago sandbox](https://github.com/Roger-Quinelato/projetoAplicado7/issues/56) | Evolução: checkout de fatura existente, confirmação no servidor, webhook validado, idempotência e provedor simulado preservado. Exige decisão de escopo/provedor; produção fica fora. |
| [#34 — outbox, reenvio e seletores](https://github.com/Roger-Quinelato/projetoAplicado7/issues/34) | Savepoint/recuperação já aparecem no código atual examinado; reconfirmar regressão. Mensagem de falha ambígua e seletores limitados à primeira página ainda aparecem na leitura estática da `main`. Reproduzir antes de corrigir. |
| [#15 — T12](https://github.com/Roger-Quinelato/projetoAplicado7/issues/15) | Financeiro implementado com escopos diferentes nas duas versões; verificar aceite, evidências e revisão pendente. |
| [#16 — T13](https://github.com/Roger-Quinelato/projetoAplicado7/issues/16) | F2 já tem implementação e evidências; tarefa exige conciliar aceite com a versão final. |
| [#17 — T14](https://github.com/Roger-Quinelato/projetoAplicado7/issues/17) | Revisão de viabilidade: custo do protótipo, dependências, limites e evolução comercial. Não afirmar custo organizacional zero ou economia sem medição. |
| [#18 — T15](https://github.com/Roger-Quinelato/projetoAplicado7/issues/18), [#19 — T16](https://github.com/Roger-Quinelato/projetoAplicado7/issues/19) | Atendimento e Workflow já existem; validar aceite e diferenças de regras entre versões. |
| [#20 — T17](https://github.com/Roger-Quinelato/projetoAplicado7/issues/20), [#21 — T18](https://github.com/Roger-Quinelato/projetoAplicado7/issues/21) | Há segurança e testes locais; faltam consolidar evidências e corrigir/retestar problemas encontrados. |
| [#22 — T19](https://github.com/Roger-Quinelato/projetoAplicado7/issues/22) | Documentos e materiais existem; precisam corresponder ao código que será apresentado. |
| [#23 — T20](https://github.com/Roger-Quinelato/projetoAplicado7/issues/23) | Publicação e comprovação no Render/Supabase permanecem pendentes. |
| [#24 — T21](https://github.com/Roger-Quinelato/projetoAplicado7/issues/24) | Conferir registros, arquivos e vínculos oficiais; situação externa completa não auditada. |
| [#25 — T22](https://github.com/Roger-Quinelato/projetoAplicado7/issues/25) | Validar premissas com professor, integrantes/contribuições, ensaio e submissão. |

O repositório define Jira como registro principal; status de GitHub e documentos não sincronizam automaticamente. Nenhuma issue ou registro externo foi alterado.

## 7. Ordem recomendada para o próximo planejamento

1. **Base única:** comparar branch local e `main`; escolher base e preservar funcionalidades e correções de ambas. O levantamento não autoriza descartar alterações locais.
2. **Estabilização obrigatória:** reproduzir os itens da #34; tratar resposta perdida após gravação e seleção após 200 clientes. Revalidar os cinco achados da auditoria local: despacho com falha anunciado como sucesso, login por papel, contraste com dados preenchidos, prontidão AMQP e indicação de conexão offline. Alguns já mudaram na `main` e não devem gerar correções duplicadas.
3. **Aceite funcional:** conferir ação por ação de cada módulo, incluindo UI/API/permissão, e executar F1/F2/F3 na mesma versão com PostgreSQL. Proteger regras de dinheiro, SLA, estados finais e não duplicação.
4. **Pagamento sandbox como evolução separada:** decidir se entra nesta entrega; caso entre, planejar #56 sem bloquear o aceite básico do protótipo simulado.
5. **Publicação e entrega:** T20, alinhamento dos materiais/T19, vínculos/T21 e validação/ensaio/submissão/T22.

Não existe evidência para incluir como obrigação atual financiamento, portal do cliente, cadastro individual de usuários, catálogo completo de frota, pagamento de produção, emissão fiscal, assinatura real, OIDC, microsserviços ou Kubernetes.

## Fontes e limites desta análise

- Locais: `Guia.pdf` (texto integral), `AGENT.md`, `README.md`, plano, PRD, visão de negócio, requisitos, ADR-001, estado, cronograma, execução das tarefas, roteiro, baseline e relatório de auditoria de 17/10; rotas dos módulos e interface.
- GitHub: lista das issues abertas, conteúdo de #34/#56, estado documentado e arquivos selecionados de UI, Finance, Integration e Workflow na `main` identificada acima.
- Não foram executados testes, aplicação ou deploy neste levantamento. Resultados de execução são atribuídos aos relatórios anteriores. A inspeção remota foi seletiva; não constitui auditoria completa da `main`.
- A referência comparativa de commits via GitHub retornou 404; nenhuma relação de ancestralidade foi concluída. As diferenças descritas vêm dos conteúdos efetivamente lidos.

Prompt pronto para uso: `output/PROMPT_ASTRA_PLANEJAMENTO_IMPLEMENTACAO.md`.
