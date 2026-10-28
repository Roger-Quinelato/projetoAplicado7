# Evidências — F-MOD (Modularização, fronteiras e domínio)

Referência: `main` = `44b8325`, cópia `iso-mod` (SHA-256 verificado, E-MOD-01). Data e hora: execução em 2026-10-19 (UTC); quando o log traz horário, ele está no campo "Fonte/local". Ambiente: Windows 11, Python 3.12.10 do `venv-auditoria` (somente leitura; nada foi instalado), SQLite em `iso-mod\tmp\`, TestClient, dados sintéticos e tokens `demo-*` do próprio repositório. Logs brutos em `logs/`; scripts em `scripts/`.

### E-MOD-01 — Integridade da cópia isolada (manifesto 44b8325)
- Tipo: comando
- Fonte/local: `logs/verificacao_iso.txt`; `evidencias/manifest_44b8325.sha256`; 2026-10-19T11:13:51Z
- Comando e ambiente: PowerShell, `Get-FileHash -Algorithm SHA256` sobre as 56 entradas `src/*` do manifesto, comparadas com `iso-mod`
- Resultado observado: "entradas src no manifest_44b8325.sha256: 56 / iguais na iso-mod: 56 / divergentes/ausentes: 0"
- Limitações: confere apenas `src/`; `tests/`, `web/` e `docs/` não foram conferidos por este comando

### E-MOD-02 — Grafo de imports AST com cobertura ampliada
- Tipo: comando (script próprio, somente stdlib)
- Fonte/local: `scripts/grafo_imports.py`; `logs/grafo_imports_relatorio.md`; `logs/grafo_imports_arestas.tsv`; `logs/grafo_imports_stdout.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `python grafo_imports.py <iso-mod>\src <PKG>\mod\logs`, Python do `venv-auditoria`
- Resultado observado: "Arquivos analisados: 55; arestas totais: 312; internas: 138." Formas: `from` 290, `import` 10, `import as` 5, `from pacote-submódulo` 1, `import_module` por constante 6. Regras: R1 (negócio → interno de outro contexto) 0; R2 (negócio → integration fora de `public`) 0; R3 (integration → negócio) 0; R4 (núcleo da raiz → contexto) 5; R5 (infraestrutura → contexto) 6; R6 (main → models) 0; R7 (domain → infraestrutura, models, rotas, serviço ou framework) 0; R8 (service → FastAPI direto) 0. Ciclos entre módulos: nenhum. Ciclo entre pacotes: um componente com 8 pacotes (`contracts`, `crm`, `finance`, `infrastructure`, `integration`, `raiz`, `support`, `workflow`). Dependência transitiva: `contracts.service → integration.public → integration.service → observability → fastapi`.
- Limitações: análise estática; `import_module` só é resolvido quando o nome vem de constante literal no mesmo arquivo; 55 arquivos `.py` (o manifesto conta 56 entradas, incluindo `script.py.mako`).

### E-MOD-03 — import-linter sobre o código real (configuração só em `scripts/`)
- Tipo: comando
- Fonte/local: `scripts/importlinter_mod.cfg` (11 contratos); `logs/importlinter_real.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `lint-imports --config <PKG>\mod\scripts\importlinter_mod.cfg --no-cache --show-timings`, com `PYTHONPATH=<iso-mod>\src`, cwd `iso-mod`; import-linter 2.1 (venv-auditoria)
- Resultado observado: "Analyzed 73 files, 263 dependencies." e "Contracts: 9 kept, 2 broken." Quebrados: `servicos-sem-http-direto-ou-indireto` (sete cadeias indiretas até `fastapi` por `archcorp.observability`, por exemplo `archcorp.contracts.service -> archcorp.integration.public -> archcorp.integration.service -> archcorp.observability -> fastapi`) e `raiz-compartilhada-sem-contextos` (`api_docs -> contracts.service (l.2)`; `errors -> schemas (l.20) -> contracts.schemas (l.32)`). Mantidos: os cinco contextos sem internos de outros contextos, `dominios-puros`, `integration-nao-depende-de-negocio`, `composicao-sem-models` e `infraestrutura-sem-contextos` (este último é falso negativo, pois `migrate` usa `import_module` dinâmico).
- Limitações: nos contratos de negócio usei `allow_indirect_imports = True` (vale a importação direta, como o teste atual). Nos contratos de raiz, serviço e domínio usei `False`, para expor cadeias indiretas. A configuração não foi adicionada ao repositório.

### E-MOD-04 — Testes de arquitetura reais e réplica sobre o código
- Tipo: comando
- Fonte/local: `tests/test_contracts_and_architecture.py`; `logs/pytest_arquitetura.txt`; `logs/replica_codigo_real.txt`; `scripts/replica_testes_arquitetura.py`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `python -m pytest tests/test_contracts_and_architecture.py -q -p no:cacheprovider -rs` (cwd `iso-mod`, `PYTHONPATH=iso-mod\src`); réplica com `python replica_testes_arquitetura.py <iso-mod>\src\archcorp`
- Resultado observado: "12 passed, 1 warning in 8.37s" (aviso: `httpx` com `starlette.testclient`). Réplica: os quatro testes de fronteira "PASSA (0 violação(ões))".
- Limitações: a réplica copia a lógica dos testes e troca só a raiz; a suíte completa (213/10 no SQLite) é da F-QUA e não foi executada aqui.

### E-MOD-05 — Sensibilidade dos testes de fronteira (árvore sintética, 12 formas)
- Tipo: comando
- Fonte/local: `scripts/sintetico/src/archcorp/` (arquivos `contracts/service.py`, `contracts/routes.py`, `contracts/domain.py`, `main.py`); `logs/replica_sintetico.txt`
- Comando e ambiente: réplica sobre `scripts/sintetico/src/archcorp`
- Resultado observado: a réplica aponta quatro violações, uma por teste: `contracts/service.py:1` (`archcorp.crm.models`), `contracts/routes.py:3` (`archcorp.integration.service`), `contracts/domain.py:2` (`sqlalchemy`) e `main.py:1` (`archcorp.contracts.models`). Formas cegas: F1 `from archcorp.crm import models` (linha 2), F2 `import archcorp.crm.models as m_alias` (linha 3), F3 `from archcorp.crm.service import CustomerService` (linha 4), F4 `importlib.import_module` literal (linhas 5 e 6), F5 `from archcorp.integration import models as im` (routes linha 1), F6 `import archcorp.integration.service` (routes linha 2), F8 `import sqlalchemy` (domain linha 1), F11 `from archcorp.integration import models` (main linha 2). Total: 4 de 12 detectadas.
- Limitações: árvore sintética de 12 casos, feita para medir a sensibilidade da lógica dos testes; não mede a suíte inteira.

### E-MOD-06 — import-linter e grafo na árvore sintética
- Tipo: comando
- Fonte/local: `scripts/importlinter_sintetico.cfg`; `logs/sintetico/importlinter_sintetico.txt`; `logs/sintetico/grafo_imports_arestas.tsv`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `lint-imports --config <PKG>\mod\scripts\importlinter_sintetico.cfg --no-cache` com cwd `scripts/sintetico` e `PYTHONPATH=scripts\sintetico\src`
- Resultado observado: "Contracts: 0 kept, 3 broken". Detectados: F0, F1, F2, F3, F5, F6, F7, F8, F9, F10 (depois de criar `contracts/models.py`) e F11. Não detectado: F4 (`importlib` literal). O grafo AST registra F4 como `import_module(literal)` (`contracts.service:6`).
- Limitações: na primeira rodada F10 não apareceu porque eu não tinha criado `contracts/models.py`; o grimp resolve import de submódulo inexistente para o pacote pai. A rodada foi refeita com o arquivo criado. O resultado vale como 11 de 12.

### E-MOD-07 — `imports_ast.py` de 01/10 reexecutado sobre 44b8325
- Tipo: comando
- Fonte/local: `output/auditoria/2026-10-01T2035Z/evidencias/agente2/imports_ast.py` (somente leitura); `logs/imports_ast_44b8325.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `python imports_ast.py` com cwd `iso-mod` e `PYTHONPATH=iso-mod\src`
- Resultado observado: as únicas linhas `<== CROSS-CONTEXT` apontam para módulos `*.public` (`contracts.service:9 -> crm.public`; `contracts.service:12 -> integration.public`; `crm.service:10 -> integration.public`; `finance.service:32 -> integration.public`; `support.service:14 -> contracts.public`; `support.service:22 -> integration.public`; `workflow.service:7 -> integration.public`). Não há mais `integration.models` em negócio nem `main` lendo `OutboxEvent` (no 01/10 eram E2-01 e E2-02).
- Limitações: o script mede imports, não reach-through por SQL textual (ver E-MOD-15).

### E-MOD-08 — Cenário principal: AUD-28, AUD-29, AUD-30 e a regra 404 × 422
- Tipo: comando (fluxo executado com TestClient e SQLite)
- Fonte/local: `scripts/exp_mod_fluxos.py principal`; `logs/exp_principal.txt`; 2026-10-19T08:07Z–08:08Z (linhas JSON de log intercaladas)
- Comando e ambiente: `python exp_mod_fluxos.py principal <iso-mod>\tmp\mod-principal.db` com `PYTHONPATH=iso-mod\src`, cwd `iso-mod`, `FINANCE_ALLOW_FUTURE_AS_OF=true` apenas nesta cópia; tokens `demo-admin`, `demo-operations`, `demo-support`, `demo-finance`, `demo-contracts`; relógio do sistema.
- Resultado observado (linhas `RESULTADO` literais):
  - "Finance cria fatura INITIAL ... observado: {'dueDate': '2026-10-29', 'amount': 2500.0, 'status': 'OPEN'}" (vencimento = data UTC do evento + 10 dias).
  - "Workflow aceita CANCELLED->IN_PROGRESS->DONE->OPEN ... observado: [('CANCELLED', 200), ('IN_PROGRESS', 200), ('DONE', 200), ('OPEN', 200)]".
  - "AUD-30 parte 2 ... observado: {'processo': 'COMPLETED', 'chamado': 'OPEN'}".
  - "AUD-29: pagamento aparece na trilha ... observado: True"; "AUD-29: verificação de vencimento marca inadimplência ... 'marcada': True"; "AUD-29: repetição não marca de novo ... 'marcadas': [], 'jaRegistradas': 1".
  - "AUD-28: Finance emite fatura FINAL ... observado: [('FINAL', 2500.0), ('INITIAL', 2500.0)]".
  - "AUD-28: preparação de retirada concluída com tarefas canceladas ... {'processo': 'COMPLETED', 'tarefas': [('Conferir documentos ', 'CANCELLED'), ('Executar onboarding', 'CANCELLED')]}".
  - "AUD-28: chamado do contrato encerrado continua OPEN ... observado: OPEN"; "AUD-28: chamado do contrato encerrado ainda é resolvível ... observado: 200".
  - "Cliente inexistente em RESERVA ... observado: (404, 'Cliente não encontrado')"; "Cliente inexistente em RASCUNHO direto ... observado: (422, 'Cliente inexistente ou inelegível')".
- Limitações: SQLite (não PostgreSQL); a inadimplência usou `asOf` futuro com a flag de simulação local, só nesta cópia; o pagamento é simulado, como no produto. O "dueDate" observado (2026-10-29) é o esperado pela data UTC do evento; a expectativa escrita no script aceitava 2026-10-30 ou 2026-10-29.

### E-MOD-09 — Chamado pendente com contrato inexistente (AUD-45)
- Tipo: comando (dois processos com o mesmo banco)
- Fonte/local: `scripts/exp_mod_fluxos.py pendente-1` e `pendente-2`; `logs/exp_pendente_1.txt`; `logs/exp_pendente_2.txt`; 2026-10-19T11:08Z
- Comando e ambiente: pendente-1 com `CONTRACT_ADAPTER_AVAILABLE=false`; pendente-2 com a variável removida; mesmo `mod-pendente.db`
- Resultado observado: pendente-1: "(201, 'PENDING_ENTITLEMENT', 'PENDING', 'HIGH')"; "processo ... observado: {'estado': 'STARTED', 'prazo': '2026-10-20T11:08:47.618569', 'abertura': '2026-10-19T11:08:47.618569Z'}". pendente-2: "reconciliação ... observado: (200, 'REJECTED_ENTITLEMENT')"; "processo pendente é cancelado ... observado: CANCELLED".
- Limitações: prazo gravado sem `Z` no SQLite (AUD-41, F-DAD); a contagem `processed` do despacho conta eventos, não consumidores (1 evento com dois consumidores).

### E-MOD-10 — Regras duplicadas: dinheiro e UTC
- Tipo: comando (leitura direta das funções, sem banco)
- Fonte/local: `scripts/exp_mod_utc_dinheiro.py`; `logs/exp_utc_dinheiro.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `python exp_mod_utc_dinheiro.py` com `PYTHONPATH=iso-mod\src`
- Resultado observado: "entrada 0.125: contracts.money=0.12 | finance.money=0.13"; "finance.domain.as_utc(naive) -> ValueError: Horário sem fuso horário; use UTC"; "support.domain.as_utc(naive) -> 2026-10-20T12:00:00+00:00"; "finance.service.iso_utc(naive) -> 2026-10-20T12:00:00Z"; "workflow.service._parse_utc(...) -> 2026-10-20T12:00:00+00:00".
- Limitações: a divergência de dinheiro é latente, porque as rotas aceitam no máximo duas casas (`decimal_places=2`, por exemplo `contracts/routes.py:90`; `finance/routes.py:76`).

### E-MOD-11 — Varredura estática: camadas, acoplamento, duplicação e configuração
- Tipo: comando (busca textual com `Select-String`) e inspeção
- Fonte/local: `logs/grep_estatico.txt` (seções 4a a 4h e 8a a 8h); 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: padrões sobre `iso-mod\src\archcorp`
- Resultado observado (trechos): 4a "src\archcorp\integration\service.py:113: import pika"; 4b "src\archcorp\workflow\routes.py:140: item.state = body.state"; "src\archcorp\integration\routes.py:61: event.attempts = 0"; 4c "src\archcorp\contracts\service.py:224: contract, replay = self.contracts._draft(...)"; 4e "src\archcorp\integration\routes.py:17: global _dispatcher"; 4f "src\archcorp\finance\service.py:167: if reference > today and (not settings.finance_allow_future_as_of ...)"; 8a: limite 200 em sete sítios literais (contracts/routes.py:200 e 252; finance/routes.py:235; finance/service.py:210; workflow/routes.py:95 e 110), além de `MAX_PAGE_SIZE` (crm) e `PENDING_BATCH_MAX` (support); 8d: 23 chamadas de `IdempotencyStore` em 3 módulos (contracts, finance e support) e `save_legacy(... f"auto:{event.event_id}")` (contracts/service.py:140); 8f: "src\archcorp\finance\service.py:133: raise BusinessRuleError(... code="VALIDATION_ERROR")" e HTTPException nas rotas de workflow (103 a 139) e integration (57, 82); 8h: `max_length=100` em support/routes.py:207 e :250; 4h: `ContractsUnavailableError` declarada em contracts/public.py:6 e capturada em support/service.py:35 (nenhum levantamento em `src` ou `tests`).
- Limitações: busca textual; os trechos citados nos achados foram conferidos à mão.

### E-MOD-12 — Cobertura de testes sobre as regras auditadas
- Tipo: comando (busca textual em `tests/`) e inspeção
- Fonte/local: `logs/grep_testes_regras.txt`; `tests/test_extended_modules.py:66`; `tests/test_f1_cliente_reserva_contrato.py:137`; `tests/test_finance.py:282-289`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `Select-String` sobre `tests/*.py` com os padrões de transição, elegibilidade, pagamento e pendência
- Resultado observado: a única menção a `/workflow/tasks` é `GET` (test_extended_modules.py:66); nenhum teste envia PATCH com transição inválida. `ContractsUnavailableError` e `ApiModel` não aparecem em `tests/`. O 422 de cliente inexistente no rascunho é fixado (test_f1...:137: "Cliente inexistente ou inelegível"); o 404 da reserva não aparece em teste. AUD-29 está coberto: `operations.count("record_simulated_payment") == 3` e `"mark_invoice_overdue" in operations and "evaluate_overdue" in operations` (test_finance.py:288-289).
- Limitações: busca textual, não cobertura de linha (cobertura é tarefa da F-QUA).

### E-MOD-13 — Volatilidade pelo histórico git desde 2026-09-01
- Tipo: comando (git somente leitura)
- Fonte/local: `logs/churn_git_desde_2026-09-01.txt`; `git -C <WT> log --since=2026-09-01 --name-only`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `git log --since=2026-09-01 --name-only` com contagem por pacote e por commit
- Resultado observado: "total de commits no periodo: 35". Commits por pacote: tests 12; raiz (`src/archcorp/*.py`) 10; contratos OpenAPI/AsyncAPI 9; contracts 8; support 7; workflow 7; crm 7; infrastructure 6; finance 6; web/src 5; integration 5. Arquivos mais alterados: `src/archcorp/main.py` 10 linhas de histórico; `docs/api/openapi.yaml` 9; `src/archcorp/contracts/service.py` 8.
- Limitações: janela de sete semanas; número de commits não mede esforço; o limiar de 7 commits é uma decisão declarada no mapa.

### E-MOD-14 — Complexidade e manutenibilidade (radon)
- Tipo: comando (radon 6.0.1 do `venv-auditoria`)
- Fonte/local: `logs/radon_cc.txt`; `logs/radon_mi.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `python -m radon cc -s -a src\archcorp` e `python -m radon mi -s src\archcorp` com cwd `iso-mod`
- Resultado observado: "Average complexity: A (2.0248618784530388)"; "F 201:0 document_problem_responses - C (16)" (`api_docs.py`); "M 109:4 ContractService.close - C (11)" (`contracts/service.py`). Índice de manutenibilidade mais baixo: `crm/service.py` 24,82; `contracts/service.py` 28,49; `support/service.py` 35,70.
- Limitações: sinal de ferramenta; cada bloco foi triado no achado MOD-19.

### E-MOD-15 — Dono, leitura e escrita de dados por contexto
- Tipo: comando (busca textual) e inspeção de código
- Fonte/local: `logs/tabelas_e_acessos.txt`; `src/archcorp/*/models.py`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: `Select-String` sobre `__tablename__`, SQL textual (`text(`, `exec_driver_sql`) e importações de `*.models`
- Resultado observado: 17 tabelas, cada uma com prefixo do dono (`crm_*`, `contracts_*`, `finance_*`, `support_*`, `workflow_*`, `integration_*`). Importação de `models` só dentro do próprio contexto (contracts/routes.py:17; contracts/service.py:8; crm/*; finance/*; support/service.py:26; workflow/*) e, na integração, no próprio contexto (integration/routes.py:11; integration/service.py:11) e na migração (`migrate.py:25-30`). SQL textual só em `infrastructure/db.py:35,47,51,53` (BEGIN, RLS e REVOKE) e em `main.py:127` (`SELECT 1` do health).
- Leitura e escrita cruzadas (inspeção, consistente com E-MOD-07): Contracts lê CRM por `CustomerReader`; Support lê Contracts por `ContractEntitlementPort`; escrita no outbox e na auditoria de outros contextos por `enqueue` e `audit` (fachada). Finance grava marcador em `integration_idempotency` (finance/service.py:83-116). Projeção: `contracts_contracts.customer_name/email` é cópia de CRM mantida por evento (contracts/service.py:166-169).
- Limitações: inspeção; não há consulta a banco real (PostgreSQL indisponível).

### E-MOD-16 — Superfícies públicas (`public.py` e fachada)
- Tipo: comando (busca textual) e inspeção
- Fonte/local: `logs/tabelas_e_acessos.txt` (seção de `public.py`); `src/archcorp/crm/public.py`, `contracts/public.py`, `integration/public.py`, `integration/service.py:153,164,176`
- Comando e ambiente: `Select-String '^class |^def |^__all__|^from |^import |^    def'` sobre `*/public.py`
- Resultado observado: `crm/public.py`: `CustomerData` (dataclass), `CustomerReaderUnavailableError`, `CustomerReader.get(session: Session, ...)`. `contracts/public.py`: `ContractsUnavailableError`, `ContractEntitlementPort.entitlement(session: Session, ...) -> dict`. `integration/public.py:8`: `__all__ = ["IdempotencyStore", "LegacyIdService", "audit", "enqueue"]`. `enqueue` devolve `OutboxEvent` (`integration/service.py:153`); `LegacyIdService.register` e `resolve` devolvem `LegacyIdMapping` (linhas 164 e 176). `finance`, `support` e `workflow` não têm `public.py`.
- Limitações: inspeção; o compromisso com `Session` está no ADR-005 e não é contado como defeito.

### E-MOD-17 — Raiz de `src/archcorp`: inventário, dependências e classificação
- Tipo: inspeção de código, com contagem de linhas (`wc -l`)
- Fonte/local: `src/archcorp/*.py` (main 175; schemas 36; api_examples 85; api_docs 324; errors 226; exceptions 49; observability 70; security 45; config 25); `logs/grafo_imports_relatorio.md`
- Comando e ambiente: `wc -l` na cópia; leitura dos arquivos
- Resultado observado: classificação segundo `component-flattening-analysis` (*misplaced implementation*, *valid composition root*, *shared infrastructure*, *boundary to clarify*): `main.py` = raiz de composição válida, com rotas próprias de health, métricas, demo e estáticos (mantidas pelo ADR-005), mas também wiring de consumidores e guardas de inicialização; `exceptions.py`, `config.py`, `observability.py` e `security.py` = infraestrutura e núcleo compartilhado legítimos; `errors.py` = adaptador HTTP, mas depende de `schemas` (A17); `api_docs.py` e `api_examples.py` = metadados; `api_docs.py` depende de `contracts.service` (A15), que é lugar errado; `schemas.py` = fachada de compatibilidade (ADR-005), que agrega todos os contextos (A16).
- Limitações: classificação qualitativa; a decisão sobre o facade `schemas` pertence ao ADR-005.

### E-MOD-18 — Entidades, mutações fora do modelo e teste da deleção (tactical-ddd, fases 1 e 2)
- Tipo: inspeção de código
- Fonte/local: `contracts/service.py:95-99,126-132,226,240-241`; `finance/service.py:147,179-180,199`; `workflow/routes.py:140,145,147`; `support/service.py` (`_transition`, atualização condicionada ao estado); `contracts/models.py:19-23,38-42`; `finance/models.py:17-20,35-36`; `crm/public.py:17`
- Comando e ambiente: leitura do código; sinais da `tactical-ddd` (`detection.md`), avaliação qualitativa (escore não aplicado a ORM)
- Resultado observado (fase 1, sinais): mutação de entidade a partir de serviço ou rota em `Contract`, `Reservation`, `Invoice`, `ProcessInstance` e `ProcessTask`. Sinal positivo: `TicketService._transition` faz `UPDATE ... WHERE status = expected` e confere `rowcount` (`support/service.py`); `CustomerData.can_contract` fica na própria classe (`crm/public.py:17`); domínios puros com regra de transição (`contracts/domain.py`, `finance/domain.py`, `support/domain.py`).
  Fase 2 (blocos): `Money` (amount e currency em `Contract`, `Reservation`, `Invoice` e `Payment`) e `Period` (startsOn e endsOn) são candidatos a value object; agregado de Processo com tarefas (invariante "concluído quando todas DONE"); agregado Contrato + Reserva com invariante de estado escrito no mesmo commit (candidato a decisão explícita, ver MOD-13); referência entre agregados por ID (cumprida: `customer_id`, `contract_id`).
- Teste da deleção (`codebase-design`): resultados detalhados em MOD-18.
- Limitações: avaliação qualitativa; ORM não recebe escore numérico; não houve refatoração (modo validar).

### E-MOD-19 — Subdomínios como entrada documental
- Tipo: inspeção documental (documento usado só como classificação de entrada; redação não avaliada)
- Fonte/local: `docs/DDD_LOCALIZA.md:21-28` (tabela de contextos e fonte oficial); `docs/DDD_LOCALIZA.md:30-37` (relações)
- Comando e ambiente: leitura
- Resultado observado: a tabela lista CRM, Contracts, Finance, Support, Workflow e Integration com a "fonte oficial" de cada um. Não há classificação de subdomínio (core, supporting, generic).
- Limitações: a classificação da seção 2 do mapa é inferida e precisa de validação com o negócio (premissa P1).

### E-MOD-20 — Logs do aplicativo sem módulo de origem
- Tipo: comando (saída do cenário principal)
- Fonte/local: `logs/exp_principal.txt`; `src/archcorp/observability.py:33` (`logging.getLogger("archcorp")`) e `:15-27` (formatter com `record.name`); 2026-10-19T08:07Z
- Comando e ambiente: saída do E-MOD-08
- Resultado observado (trecho literal): `{"timestamp": "2026-10-19T08:07:59Z", "level": "INFO", "module": "archcorp", "operation": "record_simulated_payment", "correlationId": "cedf962d-...", "result": "PARTIALLY_PAID", "message": "Pagamento simulado registrado"}`. Todos os registros do aplicativo têm `"module": "archcorp"`.
- Limitações: amostra de um cenário; o módulo aparece só pelo campo `operation`.

### E-MOD-21 — Linha de base de 01/10 e ADRs usados como critério
- Tipo: consulta documental (artefatos do repositório e ADRs; redação não avaliada)
- Fonte/local: `output/auditoria/2026-10-01T2035Z/REGISTRO_ACHADOS.md` (AUD-04, AUD-06, AUD-22, AUD-28, AUD-29, AUD-30, AUD-31, AUD-41, AUD-45, tabela consolidada); `PLANO_ACAO.md` (P-04 a P-25, P-22); `evidencias/agente2/evidencias.md` (E2-01, E2-02, E2-19, E2-21); `docs/adr/ADR-001` (r.5, r.6, r.7, r.8, r.11, r.12, r.13), `ADR-003` (§3 e §4), `ADR-005`, `ADR-006` (status "Proposto; aguarda aceite"); `AGENTS.md` (Arquitetura obrigatória; Propriedade dos dados; Confiabilidade)
- Comando e ambiente: leitura
- Resultado observado: ADR-001 r.13 ("não importa modelos internos de outro contexto"); ADR-003 §4 (dívida: extrair `IdempotencyStore` e `audit` para `infrastructure`); ADR-005 (rotas por contexto, `integration.public`, Session aceito, não é hexagonal completa); ADR-006 (estado pendente de F3; status Proposto). Não há ADR que decida aceitar identificador de contrato inexistente (AUD-45).
- Limitações: as referências a ADRs seguem a regra do briefing (cita-se o ADR como critério; não se avalia a redação).

### E-MOD-22 — Tamanhos e organização de `web/src`
- Tipo: comando
- Fonte/local: `logs/web_src_tamanhos.txt`; 2026-10-19 (UTC), mesma sessão de auditoria
- Comando e ambiente: contagem de linhas com `ReadAllLines` (inclui linhas em branco, como `wc -l`)
- Resultado observado: 12 arquivos, 1891 linhas no total; maiores: `api.ts` 358, `ui.tsx` 281, `style.css` 167, `contexts/Support.tsx` 165, `App.tsx` 149. `api.ts:64`: `export interface Billing { amount: number | string, ... }`. `contexts/` tem um arquivo por contexto do backend, além de `shared.tsx`.
- Limitações: inspeção; sem `npm` (testes e build são da F-QUA).
