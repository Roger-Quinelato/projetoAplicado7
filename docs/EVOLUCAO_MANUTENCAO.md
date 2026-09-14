# Estratégia de escalabilidade manutenção e evolução

## Princípios

A evolução preserva a SOA pragmática, as fronteiras do monólito modular e a
arquitetura hexagonal. Cada contexto continua proprietário de suas regras e
dados. A equipe distribui ou extrai componentes somente quando métricas de
escala, disponibilidade, tecnologia ou ritmo de mudança justificarem um novo
ADR.

Volumes, crescimento, retenção, objetivos de recuperação e calendário de
produção são **Premissa a validar**. A estratégia descreve o caminho de evolução
sem inventar capacidade ou prazo.

## 1. Como adicionar novos módulos

Um novo módulo deve representar uma capacidade de negócio delimitada, manter seu
modelo e sua persistência e expor uma porta pública. Outros contextos usam essa
porta ou eventos documentados, sem importar modelos internos ou consultar suas
tabelas. O módulo entra no monólito enquanto essa implantação atender às metas.

Antes da inclusão, a equipe registra proprietário dos dados, requisitos,
contratos, falhas esperadas, observabilidade e testes. Uma nova decisão
estrutural recebe ADR próprio.

## 2. Como integrar novos sistemas

Cada sistema externo recebe um adaptador substituível que traduz o contrato
externo para o modelo mínimo do fluxo. O adaptador trata autenticação, timeout,
retentativa permitida, mapeamento de identificadores e erros sem transferir
regras de negócio para Integration.

Comandos e consultas que exigem resposta imediata usam REST/JSON. Fatos
confirmados usam eventos versionados. OpenAPI, AsyncAPI ou JSON Schema entram
antes ou junto da integração.

## 3. Como alterar uma funcionalidade sem afetar todo o sistema

A regra muda no contexto que a possui. Portas e adaptadores isolam os demais
módulos. Mudanças compatíveis adicionam campos opcionais e preservam
consumidores existentes. Mudanças incompatíveis criam `/api/v2` ou novo tipo
de evento e mantêm a versão anterior durante a transição.

Testes unitários, de contrato, de integração e ponta a ponta verificam a mudança.
O pipeline também impede importações indevidas entre contextos.

## 4. Como lidar com mais usuários

A API não mantém sessão de usuário em memória e pode receber réplicas atrás de
um balanceador. A equipe acompanha taxa de requisições, p95, erros e saturação
antes de aumentar instâncias. O provedor de identidade permanece externo à
regra de negócio por meio da porta de autenticação.

O protótipo não demonstra balanceamento ou escala horizontal. Quantidade de
usuários e meta de concorrência são **Premissa a validar**.

## 5. Como lidar com mais dados

Índices atendem UUIDs globais, correlação e estados da outbox e da inbox. A
equipe define retenção para auditoria, falhas e eventos publicados quando o
volume real estiver disponível. Arquivamento, particionamento ou separação
física do banco dependem de volume, custo, período de consulta e obrigação de
retenção documentados em novo ADR.

O projeto mantém dados compartilhados no modelo canônico mínimo. Essa regra
reduz cópias e evita que um contrato central cresça com campos internos dos
contextos.

## 6. Como reduzir o impacto de alterações

Contratos versionados, adaptadores, feature flags e testes de compatibilidade
limitam o alcance de cada mudança. A fonte oficial continua responsável por
resolver divergências; consumidores não aplicam última escrita vence.

Logs, métricas, auditoria e `correlationId` permitem observar a alteração e
reverter a ativação do novo caminho sem perder a trilha operacional. Retentativa
fica restrita a erros transitórios, e falhas permanentes seguem para tratamento
explícito.

## 7. Como realizar atualizações gradualmente

A equipe executa a atualização em etapas:

1. Publica contratos compatíveis e estruturas de persistência aditivas.
2. Implanta produtores capazes de manter o formato anterior.
3. Atualiza consumidores e acompanha erros, latência, fila e divergências.
4. Ativa o novo comportamento por feature flag ou troca controlada de
   adaptador.
5. Migra dados quando necessário e verifica os critérios de aceite.
6. Remove a versão anterior somente em uma entrega posterior, depois de
   confirmar que nenhum consumidor depende dela.

Migrações precisam ser reproduzíveis e manter compatibilidade durante a
transição. Uma falha interrompe o avanço da atualização e preserva a versão
estável.

## Extração futura de um contexto

Um contexto pode sair do monólito quando apresentar necessidade independente e
mensurável. A extração preserva a porta e os eventos existentes, transfere seus
dados para uma persistência própria e substitui a chamada interna por adaptador
HTTP ou mensageria. A equipe planeja compatibilidade, migração, observabilidade e
retorno antes de alterar a implantação.

Sem essas evidências, o projeto mantém a implantação atual. Kubernetes, service
mesh, múltiplos bancos físicos ou decomposição geral em microsserviços ficam
fora do escopo do protótipo.

## Critérios para revisar a estratégia

A equipe reavalia a evolução quando medições indicarem:

- p95 ou taxa de erros acima da meta acordada;
- crescimento persistente da idade da outbox ou de mensagens não processadas;
- necessidade de disponibilidade ou implantação independente por contexto;
- volume de dados incompatível com índices e retenção atuais;
- tecnologia ou obrigação regulatória que o adaptador vigente não comporte.

Os limites numéricos de produção serão definidos após a validação dos volumes e
SLAs reais da organização.
