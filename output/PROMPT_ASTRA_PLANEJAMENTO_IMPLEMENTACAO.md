# Prompt para Astra — planejamento da implementação ArchCorp

Atue como arquiteto de software e planejador técnico do projeto ArchCorp / Projeto Aplicado 7. Faça um planejamento executável para concluir o produto e preparar a apresentação acadêmica. Nesta tarefa, analise e produza o plano; não implemente funcionalidades, publique, altere issues ou descarte alterações locais.

## Contexto de negócio e escopo

O projeto aplica o Cenário 4 (empresa de serviços) a uma operação de locação de veículos e mobilidade corporativa inspirada na Localiza. Queremos reduzir recadastro, lançamentos manuais e fragmentação entre comercial, contratos, financeiro, atendimento e operações. Os usuários principais são equipes internas.

O produto é um protótipo web de integração entre cinco contextos: CRM; reservas e contratos; financeiro e faturamento; atendimento e assistência; gestão de processos (Workflow). Integration cuida de eventos, correlação e recuperação. A oferta sintética usada nos exemplos é `RENTAL-FLEX`, com grupo de veículo, proteção, período, valor/moeda, ciclo e SLA.

O termo financeiro significa faturamento e pagamentos da locação. Não há requisito confirmado de financiamento bancário, compra financiada ou análise de crédito. Tampouco há obrigação de construir um portal do cliente ou substituir integralmente os cinco sistemas.

## Antes de planejar: confirme a base

O levantamento de 19/10/2026 encontrou duas versões com diferenças relevantes:

- Checkout local em `C:\ProjetoAplicado7`, branch `execucao-tarefas-pendentes`, HEAD `3fdb53302bfbc9277e40b7a4698c8a6c3c0943dd`, com mudanças locais anteriores em documentos/evidências.
- GitHub `Roger-Quinelato/projetoAplicado7`, `main` consultada em `cf155ee12809cfed30b1cff5980e566bd7d34d6e`.

Reconfirme esses identificadores. Não presuma que a branch local representa a `main` atual nem que todo avanço da `main` preserva todas as correções locais. Compare as funcionalidades e proponha uma estratégia de consolidação, com regressões a preservar. Não faça checkout destrutivo, reset, merge ou substituição de arquivos nesta tarefa.

## Fontes a consultar

1. `AGENT.md` e instruções aplicáveis.
2. `Guia.pdf`, fonte primária acadêmica disponível. O PDF específico Localiza citado no guia de agentes não foi localizado; sinalize a ausência, sem inventar conteúdo.
3. `PLANO_IMPLEMENTACAO_CENARIO_4.md` e ADRs vigentes em cada versão.
4. `docs/PRD_LOCALIZA.md`, `docs/VISAO_NEGOCIO.md`, `docs/REQUISITOS.md`.
5. `docs/ESTADO_IMPLEMENTACAO.md`, `docs/EXECUCAO_TAREFAS.md`, `docs/CRONOGRAMA_EXECUCAO.md`, `docs/MATRIZ_RASTREABILIDADE.md`.
6. `docs/BASELINE_COMPORTAMENTAL.md` e `output/auditoria/teste-real-2026-10-17/RELATORIO.md`, disponíveis no checkout local e referentes ao commit local auditado.
7. `output/LEVANTAMENTO_FUNCIONAL_E_PENDENCIAS.md`, como mapa inicial, a confirmar contra as fontes.
8. Código em `src/archcorp/`, frontend em `web/src/`, testes, migrações, OpenAPI, AsyncAPI, CI e roteiros de demonstração.
9. Issues abertas e PRs pertinentes: https://github.com/Roger-Quinelato/projetoAplicado7/issues . Priorize #34 e #56, e confira T12–T22 (#15 a #25). Jira é o registro principal conforme a governança local; se não tiver acesso, registre essa limitação. Não infira ausência de código porque uma issue continua aberta.

## Ponto de partida já levantado — confirme, não reimplemente automaticamente

- CRM: clientes com consulta/filtro/paginação, edição e inativação; contatos; oportunidades ganhas/perdidas; identidade UUID e validação.
- Contratos: reserva, cancelamento, rascunho sem recadastro, ativação e encerramento idempotentes. A `main` documenta leitura resiliente do CRM no ADR-006.
- Financeiro local: primeira fatura e pagamentos parciais/totais simulados. Na `main` existem estados de fatura, saldo, inadimplência, cancelamento e faturamento final no encerramento (`ContractClosed.v1`), com migração e regras próprias. O prazo de dez dias e o cálculo por ciclo iniciado são premissas de negócio; não equivalem a cobrança recorrente automática.
- Atendimento: contrato/elegibilidade, prioridade/SLA, atribuição, resolução e reconciliação. A `main` acrescenta histórico e situação de SLA, reconciliação em lote e idempotência ampliada.
- Workflow: processos de preparação e resolução por eventos, tarefas, responsáveis e prazos. Compare especialmente proteção dos estados finais e cálculo dos prazos: há diferenças entre as versões.
- Integração: outbox/inbox, auditoria, correlação, idempotência e reprocessamento. O despachante executa consumidores internos; RabbitMQ recebe cópia opcional. O despacho é explícito, sem presumir worker automático.
- Frontend: cinco áreas e visão geral. A `main` tem navegação por hash, cliente API tipado, telas mais completas, trilha por correlação e recuperação de falhas. Separe existência de endpoint de ação realmente disponível na interface.
- Segurança: tokens locais por papel e segredo compartilhado no modo público; sem contas individuais/OIDC comprovados.
- Operação: Docker, PostgreSQL, RabbitMQ, Alembic, dados sintéticos, logs, métricas básicas e health checks. Publicação HTTPS em Render/Supabase permanece sem comprovação no levantamento.

A auditoria de 17/10 do checkout local registra 84 testes Python, 11 testes de navegador com API simulada e 37 verificações com navegador/API/PostgreSQL/RabbitMQ locais. O documento remoto relata outra suíte, com 211 aprovados e 10 ignorados. Não some nem atribua resultados de uma versão à outra. Se não executar uma verificação agora, trate-a como evidência histórica.

## Riscos e pendências a avaliar

1. Issue #34: erro transacional de outbox, resposta perdida após gravação e clientes fora da primeira página dos seletores. O tratamento transacional já evoluiu nos códigos examinados; identifique itens resolvidos, parcialmente resolvidos e ainda reproduzíveis. Na `main` lida, os seletores ainda consultavam a primeira página e o feedback genérico ainda dizia “não concluído” em falha ambígua.
2. Auditoria local: sucesso indevido quando o despacho retorna falhas; login financeiro bloqueado por carregamento global; contraste em estados preenchidos; prontidão do RabbitMQ antes de AMQP; indicador verde após falha de rede. Revalide na base final, pois a interface remota já mudou e o mecanismo de login é diferente.
3. UI versus API: complete a matriz de ações, papéis, estados e mensagens. Verifique cancelamentos, edição, reconciliação, histórico, saldo e reprocessamento sem prometer cobertura apenas por existir uma rota.
4. Issue #56: proposta de Mercado Pago Checkout Pro em sandbox. Planeje como evolução separada, sujeita à decisão de inclusão nesta entrega. Prever porta/adaptador em Finance, checkout a partir de fatura existente, valor/moeda autoritativos do servidor, confirmação por consulta ao provedor, webhook validado e idempotente, referência externa, estados, falhas e testes. Retorno do navegador sozinho não quita fatura. Preservar provedor simulado e testes offline; sem dados de cartão no protótipo. Produção permanece fora dessa proposta inicial. Consulte documentação oficial atual para detalhes técnicos.
5. T20: publicação real, HTTPS, health, escrita/leitura, persistência após reinício, migrações e proteção de segredos no provedor.
6. T19/T21/T22: documentos, relatório e slides consistentes com a versão final; vínculos oficiais, nomes/contribuições, premissas validadas com professor, ensaio e submissão. T14 também exige revisão da viabilidade.

## Entregue o planejamento neste formato

1. **Definição do produto:** problema, público, proposta de valor, oferta de locação, módulos e o que está fora do escopo. Distinga oferta comercial, funcionalidades e entregáveis acadêmicos.
2. **Diagnóstico por versão:** base local, `main`, diferenças e estratégia recomendada de consolidação. Cite arquivos, funções, testes, ADRs e issues que sustentam cada conclusão.
3. **Matriz de funcionalidades:** módulo; capacidade/regra; usuário/papel; requisito; situação da API; situação da UI; testes/evidência; status (implementado, parcial, ausente ou não verificado); lacuna e dependência. Não use “concluído” com base apenas em documentação ou em issue fechada.
4. **Backlog priorizado:** primeiro consolidar/estabilizar os três fluxos obrigatórios; depois completar o que falta para a entrega; separar Mercado Pago e demais evoluções opcionais. Para cada tarefa, indique objetivo de negócio, escopo mínimo, arquivos/módulos, dependências, issue existente, critérios de aceite observáveis, regressões, validação e estimativa em faixa com premissas. Não invente responsáveis ou prazo da disciplina.
5. **Sequência de execução:** etapas ou sprints com dependências, entregável demonstrável, critério de saída e o que pode avançar em paralelo. Não crie duplicatas de T01–T22 sem explicar a relação com os aceites existentes.
6. **Plano de apresentação:** F1 cliente → reserva/contrato; F2 ativação → fatura + preparação; F3 chamado → SLA + resolução; roteiro de falha/reprocessamento. Mostre telas, entradas sintéticas, resultados, verificações de não duplicação e alternativa via API se uma tela não cobrir a operação.
7. **Checklist acadêmico e operacional:** AS-IS, TO-BE, padrões/ADRs, três integrações, interoperabilidade, pelo menos cinco atributos de qualidade, evolução, viabilidade, APIs/eventos, testes, relatório de 15–20 páginas, slides, deploy quando exigido pelo plano e evidências da versão final.
8. **Decisões pendentes:** apenas decisões que alterem escopo ou bloqueiem execução, com recomendação e premissa explícita. Sugira a primeira tarefa concreta que deve ser executada após aprovação do plano.

Preserve monólito modular, portas/interfaces públicas, propriedade dos dados, dados sintéticos e as garantias de idempotência, precisão monetária, SLA, auditoria e recuperação. Não acrescente financiamento, frota completa, produção de pagamentos, emissão fiscal, assinatura real, OIDC, tracing distribuído, microsserviços ou Kubernetes como obrigação sem requisito/decisão explícitos. Entregue um plano proporcional ao protótipo, orientado à conclusão e apresentação, com linguagem clara em português.
