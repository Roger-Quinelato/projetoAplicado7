# Achados — F-MOD (Modularização, fronteiras e domínio)

Referência: `main` = `44b8325`, cópia `iso-mod`. Severidades: 0 crítica, 0 alta, 6 média, 10 baixa, 3 informativa. Parecer P0/P1/P2 em `MAPA_ACOPLAMENTO.md`, seção 6. Os IDs E-MOD-nn remetem a `evidencias.md`.

### MOD-01 — Workflow aceita qualquer transição de tarefa e a rota atribui o estado (Q-07 / AUD-30)
- Natureza / Severidade / Confiança: defeito demonstrado / média / alta
- Esperado (fonte: AGENTS.md, "Arquitetura obrigatória" e "Propriedade dos dados"; archcorp-fronteiras-e-dominio §3: "Estado e transições ficam numa máquina de estados única no domínio do dono; rota HTTP valida formato e delega"; critério T16 citado em AUD-30): transições inválidas recusadas com 409 INVALID_STATE e auditadas.
- Observado: `change_task` grava `item.state = body.state` sem olhar o estado anterior; o contrato aceita OPEN, IN_PROGRESS, DONE e CANCELLED. No cenário principal, a mesma tarefa de um processo aberto passou por CANCELLED → IN_PROGRESS → DONE → OPEN, com 200 em cada passo. A conclusão do processo (todas as tarefas DONE) também fica na rota. Nenhum teste envia PATCH de transição (E-MOD-12).
- Localização: `src/archcorp/workflow/routes.py:131-149` (atribuição na linha 140; conclusão nas linhas 143-147); contrato `TaskChange.state` em `:50`.
- Reprodução: `scripts/exp_mod_fluxos.py principal` (bloco "AUD-30: transições de tarefa"); saída em `logs/exp_principal.txt`.
- Impacto: processo pode ser reaberto ou reativado sem regra e sem trilha; a tarefa de um chamado pode ser concluída sem que o chamado mude (MOD-02).
- Evidências: E-MOD-08, E-MOD-11, E-MOD-12.
- Linha de base: AUD-30 (= Q-07). Confirmado e aberto. Retorno ao Support também aberto (MOD-02).
- Correção proposta e critério de aceite: (1) tabela de transições de tarefa e de processo no domínio do workflow, no modelo de `contracts/domain.py`, com `ensure_task_transition`; (2) métodos de intenção `ProcessTask.transition(to)` e `ProcessInstance.complete_if_all_done()`; (3) a rota só valida formato e chama o caso de uso; (4) entrada de auditoria por transição. Aceite: CANCELLED→IN_PROGRESS e DONE→OPEN retornam 409 INVALID_STATE; o teste falha antes da correção; `grep -n "process.state =" src/archcorp/workflow/routes.py` retorna zero.
- Skill ou fluxo sugerido para a correção: `tactical-ddd` (refactoring.md, moves 1, 2 e 4); `tdd` para o teste de transição; `archcorp-fronteiras-e-dominio` §3.

### MOD-02 — Encerramento do contrato não chega a Support: chamado segue OPEN e resolvível; preparação concluída com tarefas canceladas (AUD-28, parcial)
- Natureza / Severidade / Confiança: divergência de estado entre contextos (propagação ausente) / média / alta
- Esperado (fonte: AUD-28 e critérios T09 e T12 do registro de 01/10; archcorp-fronteiras-e-dominio §4, "consumidor de evento recalcula ou ignora o que o produtor publicou"; PLANO_ACAO P-22: a regra de encerramento deve ser decidida em ADR ou TDD): o encerramento deixa coerentes os contextos que dependem do contrato.
- Observado: depois de `ContractClosed.v1` e do despacho, Finance emite a fatura FINAL de 2500,0 (resolvido). O processo ONBOARDING fica COMPLETED com as tarefas em CANCELLED. O chamado aberto do mesmo contrato continua OPEN e o endpoint de resolução responde 200. Support não consome `ContractClosed.v1` (`main.py:57` lista só Workflow e Finance).
- Localização: `src/archcorp/workflow/service.py:96-105` (COMPLETED na linha 101; CANCELLED nas linhas 102-104); `src/archcorp/main.py:57`; ausência de consumidor em `src/archcorp/support/service.py`.
- Reprodução: `scripts/exp_mod_fluxos.py principal` (blocos "AUD-28" e "AUD-29"); `logs/exp_principal.txt`.
- Impacto: cliente com contrato encerrado tem chamado resolvível; processo concluído com tarefas canceladas se confunde com conclusão real.
- Evidências: E-MOD-08, E-MOD-21.
- Linha de base: AUD-28. Parcial: Finance resolvido (fatura FINAL); Support e Workflow abertos.
- Correção proposta e critério de aceite: decidir a regra (chamados abertos viram CANCELLED ou ficam bloqueados; preparação não executada recebe estado próprio, por exemplo CLOSED_BY_CONTRACT, em vez de COMPLETED). Support passa a consumir `ContractClosed.v1` por um consumidor idempotente com inbox. Aceite: após ContractClosed e despacho, `POST .../resolve` no chamado aberto do contrato retorna 409 e o processo ONBOARDING não aparece como COMPLETED com tarefas CANCELLED. Teste de encerramento cobre chamado aberto e processo.
- Skill ou fluxo sugerido para a correção: `grilling` (decisão antes do código); `create-adr` ou TDD registrada (regra de encerramento); `tdd`.

### MOD-03 — Chamado com cliente e contrato inexistentes é aceito quando Contracts está indisponível e abre processo de 24 h (AUD-45)
- Natureza / Severidade / Confiança: risco (decisão não registrada) / baixa / alta
- Esperado (fonte: ADR-006, status "Proposto; aguarda aceite", que trata o estado pendente como requisito do F3; AGENTS.md "Confiabilidade e erros", sobre falha observável): o estado pendente deve ser decidido e registrado, inclusive a aceitação de identificadores que nunca existiram.
- Observado: com `CONTRACT_ADAPTER_AVAILABLE=false`, `POST /api/v1/support/tickets` com contrato e cliente aleatórios retorna 201 PENDING_ENTITLEMENT (prioridade HIGH, slaStatus PENDING). O despacho cria TICKET_RESOLUTION em STARTED com prazo de 24 h. Com o adaptador religado, a reconciliação responde 200 REJECTED_ENTITLEMENT e o processo passa a CANCELLED. A mitigação funciona, mas a aceitação não tem decisão registrada.
- Localização: `src/archcorp/support/service.py:60-65` (entitlement None → PENDING_ENTITLEMENT) e `:92-103` (`_entitlement`); `src/archcorp/workflow/service.py:54-59` (prazo provisório de 24 h); `:71` (cancelamento na reconciliação).
- Reprodução: `scripts/exp_mod_fluxos.py pendente-1` e depois `pendente-2`; saídas em `logs/exp_pendente_1.txt` e `logs/exp_pendente_2.txt`.
- Impacto: operação de 24 h para contrato inexistente até a reconciliação; prazo gravado sem `Z` no SQLite (AUD-41, F-DAD).
- Evidências: E-MOD-09, E-MOD-21.
- Linha de base: AUD-45. Aberto (mitigado pela reconciliação).
- Correção proposta e critério de aceite: decidir e registrar se o chamado pendente pode existir sem contrato conhecido. Se sim, documentar a decisão e manter o teste `pendente-2` como regressão. Se não, validar o identificador e o cliente no CRM quando ele estiver disponível, e recusar com 422 quando o contrato não puder ser verificado. Aceite: a decisão está registrada e há teste de regressão para o caso.
- Skill ou fluxo sugerido para a correção: `grilling` (decisão com o responsável); `create-adr` para completar o ADR-006 após o aceite; `tdd`.

### MOD-04 — Testes de fronteira enxergam só parte das formas de import (AUD-22, parcial)
- Natureza / Severidade / Confiança: risco (guarda de fronteira ineficaz) / média / alta
- Esperado (fonte: ADR-001 r.13, "cada módulo controla suas tabelas e não importa modelos internos de outro contexto"; AGENTS.md, "É proibido acessar diretamente tabelas, classes internas ou repositórios de outro módulo"): a verificação deve falhar diante de qualquer forma de violação.
- Observado: a réplica da lógica dos quatro testes de fronteira achou 4 de 12 formas da árvore sintética (F0, F7, F9, F10). Ficaram cegas: `from archcorp.crm import models`, `import archcorp.crm.models as m`, `from archcorp.crm.service import X` (serviço interno), `import archcorp.integration.service`, `from archcorp.integration import models`, `import sqlalchemy` em domínio e `from archcorp.integration import models` no `main`. O import-linter detecta 11 das 12; só `importlib.import_module` literal escapa (o grafo AST detecta). Sobre o código real, os quatro testes passam e a suíte de arquitetura passa (12 testes).
- Localização: `tests/test_contracts_and_architecture.py:90-101` (só `ImportFrom` com `parts[2] == "models"`); `:105-115` (main, só `ImportFrom`); `:118-126` (fachada, só `ImportFrom` com `archcorp.integration.`); `:129-134` (domínio, só `ImportFrom`).
- Reprodução: `scripts/replica_testes_arquitetura.py scripts/sintetico/src/archcorp` (`logs/replica_sintetico.txt`); `scripts/importlinter_sintetico.cfg` (`logs/sintetico/importlinter_sintetico.txt`); no código real, `scripts/importlinter_mod.cfg` (`logs/importlinter_real.txt`).
- Impacto: violação por `import` simples ou `from pacote import submódulo` passa sem alarme. Hoje o código está limpo nessas formas (E-MOD-07), mas nada impede que a regressão entre.
- Evidências: E-MOD-03, E-MOD-04, E-MOD-05, E-MOD-06, E-MOD-07.
- Linha de base: AUD-22. Parcial: imports de `integration.models` foram retirados de contracts, support e main; o teste continua cego.
- Correção proposta e critério de aceite: promover `importlinter_mod.cfg` para o repositório como verificação de CI (decisão da F-QUA e da F-CFG; altera o repositório, por isso não foi feito aqui). Manter o teste AST para `importlib`. Aceite: os 12 casos sintéticos são detectados e a configuração passa no código real.
- Skill ou fluxo sugerido para a correção: `coupling-analysis` (contratos); `tdd` (casos sintéticos como testes); `archcorp-fronteiras-e-dominio` §2.

### MOD-05 — Hexagonal parcial: regras e consultas na camada HTTP; broker embutido no despachante (AUD-06, parcial)
- Natureza / Severidade / Confiança: dívida técnica / média / média (inspeção e busca textual)
- Esperado (fonte: AGENTS.md, "Aplicar arquitetura hexagonal: domínio e casos de uso não dependem de HTTP, banco, broker ou SDK externo"; ADR-005 aceita Session nas portas e declara que não é hexagonal completa; ADR-001 r.6 e r.10, adaptadores substituíveis).
- Observado: (a) regra de transição de workflow na rota (MOD-01); (b) reprocessamento na rota: `event.status = "PENDING"`, `event.attempts = 0` e auditoria sem solicitante (`integration/routes.py:58-61`; AUD-31); (c) consultas diretas em rotas (`contracts/routes.py:200,252`; `finance/routes.py:235`; `workflow/routes.py:95-113`; `integration/routes.py:43-96`); (d) `pika` importado e usado dentro do despachante, sem porta (`integration/service.py:109-145`). A parte positiva: serviços e domínios não importam `fastapi` nem `HTTPException` (grep, E-MOD-11; `dominios-puros` mantido pelo import-linter).
- Localização: `src/archcorp/integration/routes.py:54-63`; `src/archcorp/workflow/routes.py:116-149`; `src/archcorp/integration/service.py:109-145`.
- Reprodução: `grep` das seções 4a e 4b em `logs/grep_estatico.txt`; `logs/importlinter_real.txt` (contrato `dominios-puros`).
- Impacto: trocar o broker ou a regra de reprocessamento exige mexer em rota ou no despachante; testar regra exige HTTP.
- Evidências: E-MOD-11, E-MOD-03, E-MOD-17.
- Linha de base: AUD-06. Parcial: `main.py` caiu de 619 para 175 linhas; as rotas de Contracts, Support e Integration foram para os routers (ADR-005); casos de uso de contracts, finance e support não têm HTTPException.
- Correção proposta e critério de aceite: mover o reprocessamento para `integration.service` como caso de uso com solicitante (AUD-31); criar `BrokerPublisher` como porta, com adaptador pika e adaptador de teste (dois adaptadores tornam o seam real); mover consultas de leitura para serviços. Aceite: `grep -n "pika" src/archcorp/integration/service.py` retorna só o adaptador; reprocessamento grava o principal na auditoria.
- Skill ou fluxo sugerido para a correção: `tactical-ddd` (refactoring, move 5); `codebase-design` (DEEPENING, "remote but owned" com porta); `archcorp-fronteiras-e-dominio`. Trocar de broker exige ADR (ADR-001 r.6); só o adaptador, não.

### MOD-06 — Regras duplicadas com resultado divergente: elegibilidade (404 × 422) e normalização UTC
- Natureza / Severidade / Confiança: divergência entre código e contrato / média / alta
- Esperado (fonte: AGENTS.md, "Erros e falhas" e "Idioma"; mesma condição de negócio deve dar o mesmo código de erro; coerência código, OpenAPI e testes, conforme o briefing §6 para AUD-40): cliente inexistente tem um único tratamento.
- Observado: (a) cliente inexistente na reserva retorna 404 "Cliente não encontrado"; no rascunho direto retorna 422 "Cliente inexistente ou inelegível". O teste fixa só o 422 (`test_f1_cliente_reserva_contrato.py:137`). (b) Normalização UTC em 5 implementações: `finance.domain.as_utc` levanta `ValueError` para datetime sem fuso; `support.domain.as_utc`, `finance.service.iso_utc` e `workflow.service._parse_utc` tratam o naive como UTC. O SQLite devolve naive (AUD-41).
- Localização: `src/archcorp/contracts/service.py:195-199` (reserva: NotFoundError) e `:35-40` (`eligible_customer`: BusinessRuleError); `src/archcorp/finance/domain.py:28-32`; `src/archcorp/support/domain.py:75-79`; `src/archcorp/finance/service.py:36-41`; `src/archcorp/workflow/service.py:21-24`.
- Reprodução: `scripts/exp_mod_fluxos.py principal` (bloco "Cliente inexistente"); `scripts/exp_mod_utc_dinheiro.py` (`logs/exp_utc_dinheiro.txt`).
- Impacto: o cliente da API precisa de dois tratamentos para o mesmo problema; datas naive são lidas de formas diferentes conforme o módulo.
- Evidências: E-MOD-08, E-MOD-10, E-MOD-12.
- Linha de base: novo (relacionado a AUD-40, F-DAD).
- Correção proposta e critério de aceite: uma função de elegibilidade (`ensure_customer_can_contract`) usada pela reserva e pelo rascunho, com um único código de erro; uma função UTC na infraestrutura, com decisão explícita sobre naive (rejeitar ou tratar como UTC em todos os pontos). Aceite: a mesma requisição sem cliente dá o mesmo status nos dois endpoints; um teste cobre a normalização nos cinco pontos.
- Skill ou fluxo sugerido para a correção: `component-common-domain-detection` (consolidar tratamento de erro; manter a regra no CRM, em `CustomerData.can_contract`); `tdd`.

### MOD-07 — Duplicação latente de regras e constantes (arredondamento, limite de página, replay, erros, literais)
- Natureza / Severidade / Confiança: dívida técnica / baixa / média
- Esperado (fonte: `component-common-domain-detection` (Do's: "uma regra, um dono"); AGENTS.md, "Propriedade dos dados": fonte oficial única):
- Observado: (a) dinheiro com dois arredondamentos: `contracts/service.py:18-20` usa `quantize` com o padrão (ROUND_HALF_EVEN) e `finance/domain.py:39-40` usa ROUND_HALF_UP; `0,125` vira `0,12` e `0,13`. É latente, porque as rotas aceitam no máximo duas casas. (b) Limite de listagem 200 em sete literais (`contracts/routes.py:200,252`; `finance/routes.py:235`; `finance/service.py:210`; `workflow/routes.py:95,110`), além de `MAX_PAGE_SIZE` (crm, com offset) e `PENDING_BATCH_MAX` (support). (c) Replay de idempotência repetido em 23 chamadas de 3 módulos (contracts, finance e support), mais o caminho legado (`previous`, `save_legacy` e a chave sintética `auto:{eventId}` em `contracts/service.py:140`). (d) Erro: HTTPException nas rotas de workflow (`:103-139`) e de integration (`:57,82`), e DomainError nos serviços; código sobrescrito em `finance/service.py:133` (`code="VALIDATION_ERROR"`). (e) Literal `max_length=100` em `support/routes.py:207` e `:250`, em vez de `IDEMPOTENCY_KEY_MAX_LENGTH`. (f) Conjunto de estados fechados repetido: `workflow/routes.py:122,138`, `workflow/service.py:99` e `web/src/contexts/Workflow.tsx:13`.
- Localização: as indicadas acima.
- Reprodução: `logs/grep_estatico.txt` (seções 8a, 8b, 8d, 8f, 8h); `scripts/exp_mod_utc_dinheiro.py`.
- Impacto: correções divergem por módulo; mudar um limite ou uma regra exige editar sete ou mais pontos.
- Evidências: E-MOD-10, E-MOD-11.
- Linha de base: novo (relacionado a AUD-39, AUD-40 e AUD-48, F-DAD).
- Correção proposta e critério de aceite: (a) `Money` com ROUND_HALF_UP e uma única função; (b) constante de página e paginação com offset em todas as listas; (c) helper de replay por operação; (d) só DomainError nas rotas de negócio; (e) constante no lugar do literal; (f) `is_closed(state)` no backend e no front. Aceite: `grep -n "limit(200)" src/archcorp` retorna zero fora da constante; nenhuma rota de negócio importa HTTPException; um teste compartilhado cobre o arredondamento. Um pacote novo de valor compartilhado exige decisão registrada (ADR).
- Skill ou fluxo sugerido para a correção: `component-common-domain-detection` (fase 5: consolidar com fronteira explícita); `tactical-ddd` (move 3, value object); `coding-guidelines`.

### MOD-08 — Projeção de Contracts sobrescrita por evento antigo (AUD-04; P0 no mapa)
- Natureza / Severidade / Confiança: risco de corrupção de dado na fronteira / média / média (inspeção; reprodução de F-DAD)
- Esperado (fonte: AGENTS.md, "Propriedade dos dados" e "Em divergências ... não aplique 'última escrita vence' sem decisão explícita; preserve a fonte oficial"): a fonte oficial de nome e e-mail é o CRM.
- Observado: `apply_customer_update` executa `UPDATE` incondicional de `customer_name` e `customer_email` em todos os contratos do cliente. O evento `CustomerUpdated.v1` não leva versão nem `occurredAt` do agregado (o payload tem customerId, name e email). Um `CustomerUpdated.v1` antigo, reprocessado depois de um mais novo, grava o nome antigo na projeção.
- Localização: `src/archcorp/contracts/service.py:166-169`; consumidor em `src/archcorp/main.py:61`; publicação em `src/archcorp/crm/service.py:52`.
- Reprodução: não reexecutado nesta frente. Reproduzido na auditoria de 01/10 (`evidencias/agente2/exp/e09_ordem_contrato.py`, E2-15) e a reprodução da F-DAD (E-02) confirma a sequência. Esta frente confirmou o código por leitura.
- Impacto: projeção divergente da fonte oficial, sem registro de inconsistência; a cópia é usada em contratos e pode aparecer em respostas.
- Evidências: E-MOD-18, E-MOD-21, E-MOD-16 (publicação e consumo).
- Linha de base: AUD-04 (= Q-03). Aberto (por inspeção). A reprodução e a severidade final ficam com a F-DAD.
- Correção proposta e critério de aceite: incluir versão ou `occurredAt` do agregado no `CustomerUpdated.v1` (mudança aditiva, atualizando a AsyncAPI e o teste de envelope), e aplicar o evento só se for mais novo; registrar o descarte na auditoria. Aceite: teste "falha v1 → aplica v2 → reprocessa v1" mantém v2 e registra o descarte; o teste falha antes da correção.
- Skill ou fluxo sugerido para a correção: `archcorp-dados-e-consistencia`; `archcorp-contratos-e-migracoes` (mudança aditiva no evento); `tdd`.
- Nota sobre a severidade: o mapa classifica o achado como P0 pelo critério de risco de corrupção de dado em fronteira. A severidade fica média, como no registro de 01/10, porque o disparo exige entrega fora de ordem ou falha injetada. A F-DAD deve reconciliar.

### MOD-09 — Raiz e infraestrutura dependem de contextos; FastAPI chega aos serviços por `observability`; ciclo de pacotes
- Natureza / Severidade / Confiança: dívida técnica (direção de dependência) / baixa / alta (import-linter e grafo executados)
- Esperado (fonte: `modular-design-principles`, "Inward leaks of infrastructure types into core logic are a smell"; AGENTS.md, "domínio e casos de uso não dependem de HTTP"; `component-flattening-analysis`: a raiz não é depósito):
- Observado: (a) `api_docs.py:2` importa `CRM_UNAVAILABLE_DETAIL` de `contracts.service`: metadado de documentação depende de serviço com SQLAlchemy. (b) `errors.py:20` importa `archcorp.schemas`, que importa os schemas de todos os contextos (`schemas.py:31-34`). (c) `observability.py:7` importa `fastapi`, e serviços de negócio usam `observability` (`logger`): sete cadeias indiretas até `fastapi` no import-linter (contrato `servicos-sem-http-direto-ou-indireto`, quebrado). (d) `infrastructure/migrate.py:24-37` carrega os modelos de todos os contextos (dinâmico; invisível ao import-linter, visível ao grafo). Resultado: um componente de pacotes com oito pacotes (`contracts`, `crm`, `finance`, `infrastructure`, `integration`, `raiz`, `support`, `workflow`). Não há ciclo entre módulos.
- Localização: `src/archcorp/api_docs.py:2`; `src/archcorp/errors.py:20`; `src/archcorp/schemas.py:31-34`; `src/archcorp/observability.py:7`; `src/archcorp/infrastructure/migrate.py:24-37`.
- Reprodução: `scripts/grafo_imports.py` (`logs/grafo_imports_relatorio.md`, "Ciclos entre pacotes"); `scripts/importlinter_mod.cfg` (`logs/importlinter_real.txt`, contratos `raiz-compartilhada-sem-contextos` e `servicos-sem-http-direto-ou-indireto`).
- Impacto: mudar um schema ou uma constante de contrato recompila a raiz; a camada de erro carrega todos os contextos; teste que importa `errors` puxa todos eles.
- Evidências: E-MOD-02, E-MOD-03, E-MOD-17.
- Linha de base: novo (relacionado a AUD-22 e ao ADR-005).
- Correção proposta e critério de aceite: (a) mover `CRM_UNAVAILABLE_DETAIL` para `api_examples` ou para a porta de Contracts; (b) `errors.py` importa de `api_examples`, não de `schemas`; (c) `observability` sem importar `fastapi` (o middleware fica em `main` ou em `errors`); (d) registrar os modelos por descoberta de pacote, no composition root. Aceite: os contratos `raiz-compartilhada-sem-contextos` e `servicos-sem-http-direto-ou-indireto` passam. Não exige ADR, exceto para remover o facade `schemas` (ADR-005).
- Skill ou fluxo sugerido para a correção: `component-flattening-analysis`; `modular-design-principles`; `coupling-analysis`.

### MOD-10 — Superfícies públicas expõem tipos de persistência e de transporte sem tipo
- Natureza / Severidade / Confiança: dívida técnica (API pública vazando) / baixa / média (inspeção)
- Esperado (fonte: `modular-design-principles` princípio 1, "superfície pública pequena e estável", e princípio 5, contratos documentados entre módulos; ADR-005: a fachada `integration.public` expõe idempotência, auditoria, eventos e IDs legados, e o compromisso com `Session` é aceito):
- Observado: `integration/public.py` reexporta `enqueue`, que devolve `OutboxEvent` (`integration/service.py:153`), e `LegacyIdService.register` e `resolve`, que devolvem `LegacyIdMapping` (linhas 164 e 176). Contracts usa `event.event_id` do objeto ORM. `ContractEntitlementPort.entitlement` devolve `dict` (`contracts/public.py:15`). Os eventos são montados como `dict` nos serviços (`contracts/service.py:101,134,172`). `ContractsUnavailableError` é declarada e capturada (`support/service.py:35,99`), mas nenhum código a levanta (E-MOD-11, 4h); o docstring prevê simuladores futuros.
- Localização: `src/archcorp/integration/service.py:153,164,176`; `src/archcorp/integration/public.py:6-8`; `src/archcorp/contracts/public.py:6,15`; `src/archcorp/support/service.py:35,99`.
- Reprodução: `logs/tabelas_e_acessos.txt` (seção `public.py`); inspeção de `integration/service.py`.
- Impacto: consumidores da fachada dependem de colunas do modelo; trocar a persistência de integração quebra os consumidores.
- Evidências: E-MOD-16, E-MOD-11, E-MOD-12.
- Linha de base: novo (relacionado a AUD-22).
- Correção proposta e critério de aceite: `enqueue` devolve uma referência (`EventRef` com `event_id`); `LegacyIdService` devolve um DTO; `entitlement` devolve um tipo (`Entitlement` com `eligible` e `sla_hours`); `ContractsUnavailableError` sai até haver quem a levante, ou ganha um teste que a levanta (decisão do responsável). Aceite: `grep -n "OutboxEvent\|LegacyIdMapping" src/archcorp/*/public.py` retorna zero; o compromisso com Session do ADR-005 permanece.
- Skill ou fluxo sugerido para a correção: `codebase-design` (reduzir a interface do seam); `modular-design-principles` (princípio 1).

### MOD-11 — Estado global de módulo e configuração lida dentro de regras; raiz com seis motivos de mudança
- Natureza / Severidade / Confiança: dívida técnica / baixa / média
- Esperado (fonte: `modular-design-principles` princípio 3, dependências explícitas, e princípio 2, composabilidade; ADR-005: configuração explícita dos serviços nos routers, sem contêiner de injeção):
- Observado: quatro routers guardam serviços em estado de módulo por `configure()` (`contracts/routes.py:30-38`; `finance/routes.py:28-34`; `integration/routes.py:14-18`, com `global`; `support/routes.py:55-61`). Regras leem `settings` global: `finance/service.py:167` (data de referência futura), `support/service.py:94` (adaptador) e `integration/service.py:95-129` (tentativas e broker). `main.py` (175 linhas, 10 commits desde 01/09, o maior churn entre os arquivos de código) reúne composição, guardas do lifespan da demo, health, métricas, estado da demonstração, estáticos e wiring dos consumidores.
- Localização: as indicadas acima; `src/archcorp/main.py:54-62` (wiring) e `:66-76` (lifespan).
- Reprodução: `logs/grep_estatico.txt` (seções 4e e 4f); `logs/churn_git_desde_2026-09-01.txt`.
- Impacto: duas configurações no mesmo processo compartilham estado; mudar a configuração altera regra sem passar pelo caso de uso; `main` muda por seis motivos.
- Evidências: E-MOD-11, E-MOD-13, E-MOD-17.
- Linha de base: novo.
- Correção proposta e critério de aceite: o caso de uso recebe a política por parâmetro (por exemplo, `ElegibilityPolicy`); os routers recebem os serviços por dependência do FastAPI (`app.state`); health, métricas e demo vão para um módulo `operations`, sem mudar o composition root. Aceite: `grep -n "settings\." src/archcorp/*/service.py` retorna zero em regras; teste com duas configurações no mesmo processo.
- Skill ou fluxo sugerido para a correção: `codebase-design` (DEEPENING: seams e dependências); `create-adr` (trocar `configure()` exige ADR, pois ADR-005 escolheu o padrão atual).

### MOD-12 — Finance guarda estado próprio na tabela de idempotência de Integration (ADR-003 §4)
- Natureza / Severidade / Confiança: dívida técnica (isolamento de estado parcial) / baixa / média
- Esperado (fonte: `modular-design-principles` princípio 8, "cada módulo controla seu estado"; ADR-001 r.13; ADR-003 §4, dívida registrada: extrair `IdempotencyStore` e `audit` para `infrastructure`):
- Observado: `handle_contract_closed` grava um marcador por `eventId` com a operação `finance_final_billing` em `integration_idempotency` (`finance/service.py:44,83,105,116`). Finance não tem tabela própria para essa deduplicação; a coluna `source_event_id` com restrição única (`finance/models.py:23,27`) já cobre a fatura.
- Localização: `src/archcorp/finance/service.py:44,83,105,116`.
- Reprodução: `logs/grep_estatico.txt` (seção 8d); E-MOD-21.
- Impacto: limpar ou reter a idempotência de Integration pode apagar a barreira do faturamento final; Finance depende de tabela de outro contexto.
- Evidências: E-MOD-11, E-MOD-21, E-MOD-15.
- Linha de base: novo (dívida registrada no ADR-003 §4).
- Correção proposta e critério de aceite: remover o marcador (a restrição única de `source_event_id` e a de `uq_invoice_contract_kind` cobrem a faturação) ou criar tabela de eventos processados de Finance; extrair `IdempotencyStore` e `audit` para `infrastructure`. Aceite: `finance` não grava em `integration_idempotency` nem importa `integration.service`.
- Skill ou fluxo sugerido para a correção: `create-adr` (muda dono de tabela transversal); `archcorp-fronteiras-e-dominio` §1; `decomposition-planning-roadmap` (ordem da extração).

### MOD-13 — Modelo anêmico, invariantes fora do agregado e primitivos sem value object
- Natureza / Severidade / Confiança: dívida técnica / baixa / média (inspeção)
- Esperado (fonte: `tactical-ddd`, golden rules 1, 3, 5 e 6: comportamento junto ao dado; invariantes no agregado; referência por ID; value object antes de entidade):
- Observado: entidades ORM sem comportamento (E-MOD-18). Mutações feitas por serviços e rotas: Contract e Reservation no mesmo commit (`contracts/service.py:95-99`, `:126-132`, `:240-241`); Invoice em três pontos (`finance/service.py:147`, `:179-180`, `:199`); ProcessInstance e ProcessTask na rota (`workflow/routes.py:140-147`). A regra "processo concluído quando todas as tarefas estão DONE" é invariante do agregado Processo e está na rota. Primitivos: `amount` com `currency` separados em Contract, Reservation, Invoice e Payment (`contracts/models.py:19-20`, `:38-39`; `finance/models.py:17-18`, `:35-36`); `status: str` em todas as entidades (`contracts/models.py:23`). Positivos: referência entre agregados por ID (`customer_id`, `contract_id`) e transições em `domain.py` nos três módulos de domínio.
- Localização: as indicadas acima.
- Reprodução: `logs/grep_estatico.txt` (seções 4b e 8e); E-MOD-18.
- Impacto: invariantes dependem de quem chama o serviço; `Money` e `Period` se repetem (MOD-07).
- Evidências: E-MOD-18, E-MOD-10.
- Linha de base: novo (relacionado a AUD-06 e AUD-30).
- Correção proposta e critério de aceite: value objects `Money` e `Period`; `ProcessInstance.complete_if_all_done()`; `Invoice.mark_overdue(now)` e `Invoice.register_payment(amount)` usando as funções de `finance/domain.py`; decidir o agregado Contrato + Reserva (agregado único ou justificativa escrita). Aceite: nenhuma mutação de `.status` fora do módulo dono do agregado.
- Skill ou fluxo sugerido para a correção: `tactical-ddd` (refactoring, moves 1 a 3); `domain-modeling`; `create-adr` se a fronteira do agregado mudar (Contrato + Reserva).

### MOD-14 — Regras temporais dependem do relógio ou da entrada fora do ponto injetado
- Natureza / Severidade / Confiança: risco (reprodutibilidade) / baixa / média (inspeção)
- Esperado (fonte: ADR-003 §3, vencimento pela data UTC do evento, para que o reprocessamento não mude o resultado; AGENTS.md, "Datas e horas em ISO 8601 UTC"):
- Observado: o prazo de ONBOARDING é `datetime.now(timezone.utc) + 72h` no momento do processamento (`workflow/service.py:42`), enquanto o faturamento usa `occurredAt` (`finance/service.py:65` e `:109`). O validador de reserva compara com `date.today()` (`contracts/routes.py:100`). O encerramento usa `max(date.today(), contract.starts_on)` (`contracts/service.py:123`). Support recebe o relógio injetado (`support/service.py:41-50`).
- Localização: as indicadas acima.
- Reprodução: `logs/grep_estatico.txt` (seção 8c).
- Impacto: reprocessar o mesmo evento em outro dia muda o prazo; o fuso da máquina influencia a regra.
- Evidências: E-MOD-11, E-MOD-21.
- Linha de base: novo (relacionado a F-DAD, item 5: prazo de ONBOARDING contado do despacho).
- Correção proposta e critério de aceite: contar o ONBOARDING a partir de `occurredAt` do envelope; relógio injetado em Contracts e na validação. Aceite: reprocessar `ContractActivated.v1` em outro dia mantém o prazo.
- Skill ou fluxo sugerido para a correção: `archcorp-dados-e-consistencia`; `tdd` com relógio fixo.

### MOD-15 — Camada web: tipos escritos à mão, componente com várias responsabilidades e rótulos duplicados
- Natureza / Severidade / Confiança: dívida técnica (divergência potencial entre contrato e interface) / baixa / média (inspeção)
- Esperado (fonte: `docs/api/openapi.yaml` como contrato; `modular-design-principles` princípio 5):
- Observado: `web/src/api.ts` (358 linhas) define os tipos à mão. `Billing.amount: number | string` (`api.ts:64`) acomoda a divergência de AUD-20. `ui.tsx` (281 linhas) reúne sessão, formatação, rótulos de estado, recursos, formulários, tabela e layout. `SlaBadge` (`contexts/Support.tsx:19-23`) repete o padrão de rótulos de `Status` (`ui.tsx:48-62`). Positivo: `contexts/` tem um arquivo por contexto do backend. O maior componente de contexto tem 165 linhas.
- Localização: `web/src/api.ts:64`; `web/src/ui.tsx`; `web/src/contexts/Support.tsx:19-23`; `web/src/contexts/Workflow.tsx:13`.
- Reprodução: `logs/web_src_tamanhos.txt`; inspeção.
- Impacto: mudar o contrato exige mudar tipos à mão; mudanças de formatação se espalham.
- Evidências: E-MOD-22, E-MOD-11.
- Linha de base: novo (relacionado a AUD-20, F-DAD; AUD-26 e AUD-27, F-QUA).
- Correção proposta e critério de aceite: gerar os tipos a partir de `docs/api/openapi.yaml` com verificação em CI; dividir `ui.tsx` por responsabilidade (formatação, recurso, formulário). Aceite: `Billing.amount` tem um tipo único igual ao do OpenAPI.
- Skill ou fluxo sugerido para a correção: `coding-guidelines`; `component-flattening-analysis` (organização).

### MOD-16 — Layout de contexto não uniforme; exemplos de API espalhados; peça sem uso
- Natureza / Severidade / Confiança: dívida técnica / informativa / média
- Esperado (fonte: ADR-005, schemas por contexto e exemplos em `api_examples.py` e `api_docs.py`):
- Observado: `workflow` não tem `domain.py`, `schemas.py` nem `public.py`; `crm` não tem `domain.py`. Exemplos de API estão em `api_examples.py`, em `api_docs.py` e nas rotas (`workflow/routes.py:19-35`; `finance/routes.py:41-62`; `contracts/routes.py:51-70`; `crm/routes.py:26-39`). `ApiModel` (`schemas.py:6-7`) não é usada em `src` nem em `tests`.
- Localização: as indicadas acima.
- Reprodução: `logs/grep_estatico.txt` (seção 4h); `logs/tabelas_e_acessos.txt`.
- Impacto: procurar regra ou exemplo varia por contexto.
- Evidências: E-MOD-11, E-MOD-16, E-MOD-17.
- Linha de base: novo.
- Correção proposta e critério de aceite: layout mínimo por contexto (`models`, `domain` quando há regra, `service`, `routes`, `schemas`, `public` quando há consumidor); exemplos de cada contexto no próprio `schemas.py`; remover `ApiModel`. Aceite: `grep -rn "ApiModel" src` retorna zero.
- Skill ou fluxo sugerido para a correção: `component-flattening-analysis` (fase 4, plano); `coding-guidelines`.

### MOD-17 — Logs do aplicativo não atribuem o módulo de origem
- Natureza / Severidade / Confiança: dívida técnica (observabilidade) / baixa / alta (logs executados)
- Esperado (fonte: `modular-design-principles` princípio 9, "cada módulo pode ser diagnosticado sozinho ... atribuível à unidade que emitiu"; AGENTS.md, "Observabilidade": logs com módulo, operação, correlationId e resultado):
- Observado: todo registro do aplicativo sai com `"module": "archcorp"`, porque há um único logger (`observability.py:33`). O módulo de origem só aparece no campo `operation`. Trecho literal: `{"module": "archcorp", "operation": "record_simulated_payment", "correlationId": "cedf962d-...", ...}`.
- Localização: `src/archcorp/observability.py:33` (`getLogger("archcorp")`) e `:15-27` (formatter que usa `record.name`).
- Reprodução: `logs/exp_principal.txt` (E-MOD-20).
- Impacto: filtrar logs por contexto exige conhecer os nomes das operações.
- Evidências: E-MOD-20.
- Linha de base: novo (relacionado a F-QUA, item 5: campos dos logs estruturados).
- Correção proposta e critério de aceite: `logging.getLogger(f"archcorp.{modulo}")` em cada serviço, ou campo `module` explícito no `extra`. Aceite: registros de finance têm `module` = `finance`.
- Skill ou fluxo sugerido para a correção: `coding-guidelines`; fluxo de observabilidade do AGENTS.md.

### MOD-18 — Teste da deleção: módulos rasos por desenho e profundidade concentrada no lugar errado (informativa)
- Natureza / Severidade / Confiança: informativa / informativa / média
- Esperado (fonte: `codebase-design`, teste da deleção: se a complexidade some, era passagem; se reaparece em N chamadores, estava ganhando seu lugar):
- Observado (deletar → o que acontece):
  - `integration/public.py` (reexporta 4 nomes): raso. A complexidade reaparece nos seis contextos como conhecimento de `AuditLog` e `OutboxEvent` (32 chamadas de `audit` em seis módulos, além das chamadas de `enqueue`). Mantém-se: é o seam que esconde o modelo (ADR-005).
  - `schemas.py` (fachada): raso. Apagar quebra as importações antigas e o compromisso de compatibilidade do ADR-005. Mantém-se; a dependência de `errors.py` é que deve sair (MOD-09).
  - `ResilientCustomerReader` (`contracts/adapters.py`, 60 linhas): profundo (prazo, retentativa, jitter e tradução de erro). Apagar espalharia a política em um só lugar, `read_customer`. Mantém-se.
  - `IdempotencyStore` (`integration/service.py:202-241`): profundo (impressão digital, conflito, replay, caminho legado). Reaparece em 23 chamadas. Mantém-se.
  - Domínios `contracts/domain.py`, `finance/domain.py` e `support/domain.py`: profundos, sem I/O. Mantém-se.
  - `workflow` sem domínio: a regra de transição está na rota (MOD-01). Apagar `routes.py` apagaria a regra. Profundidade no lugar errado.
  - `LegacyIdService` (quatro métodos, uma consulta cada): raso; reaparece em três chamadas. Aceitável.
  - `api_docs.py` (324 linhas, sem comportamento de execução): metadados. Mantém-se pela localidade da documentação.
- Localização: as indicadas acima.
- Reprodução: inspeção; E-MOD-16 e E-MOD-17 listam as fachadas e o inventário.
- Impacto: nenhum imediato. Quando MOD-01 e MOD-06 forem corrigidos, `workflow` ganha domínio profundo.
- Evidências: E-MOD-16, E-MOD-17, E-MOD-18.
- Linha de base: novo.
- Correção proposta e critério de aceite: nenhuma obrigatória. Usar `codebase-design` (DEEPENING) e, se surgir nova interface, `DESIGN-IT-TWICE` antes de aceitá-la.
- Skill ou fluxo sugerido para a correção: `codebase-design`.

### MOD-19 — Complexidade concentrada em dois pontos; manutenibilidade menor em serviços de crm, contracts e support (triagem de sinal)
- Natureza / Severidade / Confiança: sinal de ferramenta, triado / informativa / média
- Esperado (fonte: radon como sinal, conforme o briefing §3; leitura do código para triagem):
- Observado: complexidade média A (2,02). Dois blocos C: `document_problem_responses` (`api_docs.py:201`, CC 16) e `ContractService.close` (`contracts/service.py:109`, CC 11). Triagem: o primeiro é metadado de documentação com muitos ramos de status (não é regra de negócio; uma tabela de respostas reduziria os ramos); o segundo tem quatro ramos de regra (estado, data, reserva e idempotência), é sinal e não defeito. Índice de manutenibilidade mais baixo: `crm/service.py` 24,8; `contracts/service.py` 28,5; `support/service.py` 35,7.
- Localização: as indicadas acima.
- Reprodução: `logs/radon_cc.txt`; `logs/radon_mi.txt`.
- Impacto: baixo; o custo aparece quando as regras de MOD-06 e MOD-13 forem mexidas.
- Evidências: E-MOD-14.
- Linha de base: novo.
- Correção proposta e critério de aceite: nenhuma obrigatória. Ao corrigir MOD-06 e MOD-13, separar a regra de encerramento do serviço de contrato.
- Skill ou fluxo sugerido para a correção: `coding-guidelines` (sinal).
