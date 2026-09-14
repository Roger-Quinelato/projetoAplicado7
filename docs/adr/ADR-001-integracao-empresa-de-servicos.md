# ADR-001 - SOA pragmática com APIs, eventos e monólito modular

- Status: Aceito para o protótipo acadêmico
- Data: 2026-09-12
- Decisores: equipe do Projeto Aplicado
- Contexto: Cenário 4 - Empresa de serviços

## Contexto

A organização possui CRM, sistema de contratos, sistema financeiro, sistema de atendimento e sistema de gestão de processos. O enunciado relata problemas típicos de aplicações isoladas: duplicidade, lançamentos manuais, dependência de legados, baixa escalabilidade, manutenção difícil e processos fragmentados.

A primeira entrega deve demonstrar arquitetura e integração, não substituir todos os sistemas. A equipe é júnior e precisa entregar pelo menos três fluxos executáveis, documentação de APIs, tratamento de erros, análise de qualidade, estratégia de evolução e justificativa técnica e de negócio.

O enunciado confirma os cinco sistemas e os problemas gerais da organização, mas não informa produtos, tecnologias, responsáveis, volumes nem interfaces existentes. O AS-IS específico permanece como premissa identificada até validação. Esta decisão não transforma essas premissas em fatos.

## Requisitos relacionados

- RF-01 a RF-07 do plano de implementação.
- Interoperabilidade, confiabilidade, segurança, observabilidade, manutenibilidade, desempenho, escalabilidade e disponibilidade.
- Três integrações demonstráveis e documentação que permita continuidade por outra equipe.

## Direcionadores

- Integrar sistemas heterogêneos sem acessar diretamente seus bancos.
- Reduzir dependências ponto a ponto e permitir evolução gradual.
- Manter o protótipo simples de executar, observar, testar e apresentar.
- Suportar respostas imediatas e processos assíncronos.
- Tratar reentrega, indisponibilidade e inconsistência de forma explícita.
- Preservar fontes oficiais de dados e rastreabilidade ponta a ponta.
- Evitar microsserviços sem necessidade operacional comprovada.

## Opções consideradas

### 1. Integrações ponto a ponto exclusivamente por REST

Vantagens: baixa barreira inicial e depuração simples.

Limitações: cresce aproximadamente com o número de relações entre sistemas, aumenta o acoplamento temporal, propaga indisponibilidade e dificulta mudanças de formato.

### 2. Microsserviços independentes para todas as capacidades

Vantagens: implantação e escala independentes, isolamento de falhas e fronteiras explícitas.

Limitações: exige mais automação, observabilidade, segurança, dados distribuídos e conhecimento operacional do que o protótipo justifica.

### 3. Barramento/ESB central com toda a lógica de negócio

Vantagens: conectividade e governança centralizadas.

Limitações: cria gargalo organizacional e técnico, concentra regras de negócio e pode se tornar um ponto único de mudança e falha.

### 4. SOA pragmática em monólito modular, com APIs e eventos

Vantagens: separa capacidades e contratos, permite comunicação síncrona e assíncrona, mantém execução simples e prepara extrações futuras.

Limitações: a implantação ainda é conjunta; fronteiras dependem de disciplina; o broker e a consistência eventual aumentam a complexidade conceitual.

## Decisão

Adotar a opção 4: uma arquitetura orientada a serviços em formato de monólito modular para a primeira entrega, com uma camada de integração baseada em portas e adaptadores.

As regras são:

1. CRM, contratos, financeiro, atendimento e BPM são contextos separados e têm responsabilidades e fontes oficiais definidas.
2. Nenhum módulo lê ou escreve diretamente no esquema interno de outro módulo.
3. REST/JSON é usado quando o solicitante precisa de resposta imediata, como criação de rascunho ou consulta de SLA.
4. Eventos são usados para fatos já confirmados que podem ter vários consumidores, como `ContractActivated.v1` e `TicketOpened.v1`.
5. PostgreSQL é compartilhado somente como infraestrutura do protótipo, com separação lógica por módulo e acesso controlado pela própria aplicação.
6. RabbitMQ é o broker de referência para execução local.
7. Publicações confiáveis usam outbox transacional; consumidores mantêm inbox/idempotência.
8. Toda chamada/evento carrega `correlationId`; erros permanentes seguem para fila de mensagens não processadas e podem ser reprocessados com auditoria.
9. APIs são descritas em OpenAPI e eventos em AsyncAPI ou JSON Schema; mudanças incompatíveis geram nova versão.
10. Serviços externos/legados são acessados somente por adaptadores, permitindo simuladores na demonstração e conectores reais no futuro.
11. Comandos repetíveis exigem `Idempotency-Key`; o armazenamento combina chave e operação e devolve a resposta original.
12. O reprocessamento altera apenas o estado de entrega. Inbox e restrições de negócio continuam ativas, e a auditoria registra solicitante, correlação e número anterior de tentativas.
13. O banco compartilhado representa somente a implantação. Cada módulo controla suas tabelas e não importa modelos internos de outro contexto.

## Fluxos cobertos pela decisão

- Cliente do CRM cria rascunho no sistema de contratos via REST.
- Contrato ativado publica evento consumido por financeiro e BPM.
- Atendimento consulta contrato/SLA via REST e publica a abertura para o BPM.

## Consequências positivas

- O protótipo pode ser iniciado e demonstrado com baixo custo operacional.
- As fronteiras e contratos tornam integrações compreensíveis e testáveis.
- Eventos reduzem o acoplamento entre ativação, cobrança e onboarding.
- Adaptadores isolam diferenças de tecnologia, formato e identificadores.
- A mesma estrutura permite substituir simuladores por sistemas reais.
- Módulos com demanda ou ritmo próprio podem ser extraídos posteriormente.

## Consequências negativas e custos

- Uma falha no processo da aplicação pode afetar vários módulos na mesma implantação.
- Escala e implantação não são independentes no início.
- Mensageria exige idempotência, reconciliação, observabilidade e operação de filas.
- Consistência eventual precisa ser refletida em estados como `PENDING` e explicada aos usuários.
- A separação lógica do banco precisa ser fiscalizada em revisão de código.

## Riscos e controles

- Monólito virar bloco acoplado: testes de arquitetura e dependências apenas por interfaces públicas.
- Lógica concentrada na integração: regras ficam no módulo proprietário; a camada de integração traduz, roteia e coordena.
- Evento incompatível: validação de esquema e testes de contrato no pipeline.
- Duplicidade: chaves idempotentes, restrições únicas e registro de eventos consumidos.
- Dados pessoais em trânsito: minimização, TLS, RBAC, mascaramento de logs e auditoria.

## Critérios para reconsiderar

Reavaliar esta decisão se métricas evidenciarem pelo menos uma das condições:

- um módulo precisa escalar ou ficar disponível de forma significativamente diferente;
- equipes diferentes precisam implantar módulos com cadências independentes;
- uma falha ou atualização conjunta gera impacto inaceitável;
- requisitos regulatórios exigem isolamento físico de dados ou execução;
- volume e latência tornam o broker ou o banco compartilhado inadequados.

Nesses casos, extrair primeiro o módulo que apresenta a necessidade, preservando suas APIs, eventos e propriedade de dados. Não realizar uma decomposição total preventiva.

## Validação

A decisão será considerada adequada quando os três fluxos funcionarem ponta a ponta; reentregas não duplicarem efeitos; falhas puderem ser rastreadas por `correlationId`; contratos forem validados automaticamente; e outra equipe conseguir executar a solução a partir da documentação.

As evidências estão ligadas aos requisitos em `docs/MATRIZ_RASTREABILIDADE.md`. A suíte automatizada verifica os três fluxos, repetição, degradação, autorização, contratos e fronteiras entre módulos. A equipe deve reabrir esta decisão se a validação das premissas revelar integrações, restrições regulatórias ou volumes incompatíveis com os direcionadores registrados.
