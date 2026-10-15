# Registro consolidado de achados

**Referência:** `main` = `3a3d8bd`. Os achados foram consolidados a partir de três frentes:

- **A1:** requisitos e entregas.
- **A2:** arquitetura e comportamento.
- **A3:** qualidade, segurança e operação.

Achados duplicados entre frentes foram fundidos. O registro original de cada frente, com esperado, observado, reprodução e correção completos, está em `evidencias/agente*/achados.md`. Os vereditos da revisão cruzada estão em `evidencias/agente*/revisao_cruzada.md`.

## Classificações usadas

**Natureza:**

- **Defeito:** defeito demonstrado por execução.
- **Risco:** possibilidade de dano, não demonstrada.
- **Dívida:** dívida técnica.
- **Doc:** divergência documental.
- **Meta:** meta futura.

**Confiança:**

- **Alta:** reproduzido ou consultado diretamente.
- **Média:** por inspeção.
- **Baixa:** por inferência.

**Revisão cruzada:** todo achado com severidade inicial alta foi revisado por um agente diferente do autor. O veredito e a severidade final estão na seção "Fichas" abaixo.

## Resumo

| Severidade final | Quantidade | IDs |
|---|---|---|
| Crítica | 0 | — |
| Alta | 3 | AUD-01, AUD-02, AUD-03 |
| Média | 34 | AUD-04 … AUD-38 (exceto AUD-33) |
| Baixa | 11 | AUD-33, AUD-39 … AUD-41, AUD-43 … AUD-49 |
| Informativa | 2 | AUD-42, AUD-50 |

Não houve achado crítico. Não se encontrou alegação de integração real com a Localiza, segredo exposto, perda de fato confirmado na outbox nem cobrança ou processo duplicados, nem mesmo sob concorrência em PostgreSQL.

---

## Fichas dos achados de severidade alta e dos rebaixados na revisão cruzada

### AUD-01 — Erro de banco num consumidor bloqueia toda a outbox; o evento nunca chega a FAILED
- **Origem:** A3-01 + A2-01, encontrados de forma independente pelas frentes 2 e 3.
- **Natureza:** defeito.
- **Severidade:** **alta**.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 1 deu CONFIRMADO COM AJUSTE e manteve alta. O Agente 3 registrou a convergência.
- **Esperado:**
  - `AGENT.md`, seção Confiabilidade: "Encaminhe falhas permanentes para fila de erro, preservando … motivo, tentativas" e "Nunca capture uma exceção sem registrar contexto ou convertê-la em resultado tratado".
  - RNF-02, RF-07 e os critérios de T13 e T17.
- **Observado:**
  - Os consumidores fazem `flush()` dentro do `try`. No `except`, o despachante altera `attempts` e chama `session.commit()` sem `rollback()`. O commit lança `PendingRollbackError` e a rota responde HTTP 500.
  - O incremento de `attempts` se perde e o evento fica `PENDING` com `attempts=0`. O `/integration/failures` fica vazio.
  - Como os pendentes são lidos em ordem de `occurred_at`, todo despacho para no mesmo evento, e os eventos seguintes não são processados.
- **Localização:** `src/archcorp/integration/service.py:24-45`. O `commit` da linha 45 fica fora do `try`, e não há `rollback`/`begin_nested` em `src/`. Conferido pelo coordenador.
- **Reprodução:**
  - Em PG: `evidencias/agente3/scripts/poison_exp.py` deu 5 despachos com 500. A fatura do contrato legítimo não foi criada (`logs/evento_venenoso_pg.log`).
  - Em SQLite: `evidencias/agente2/exp/e04_falhas.py` (cenário B) e `e05_bloqueio.py`.
  - Gatilho real sem injeção: dois despachos simultâneos dão `[200,500]` em 15 de 15 rodadas (AUD-11).
- **Ajuste da revisão:** o bloqueio **permanente** só foi reproduzido com evento injetado ou falha induzida. O efeito observado sem injeção é um 500 transitório no despacho concorrente. Um bloqueio permanente exige um erro de banco determinístico, como valor fora de `Numeric(14,2)` (AUD-35), deriva de esquema ou erro persistente do PG.
- **Impacto:** um único evento incompatível paralisa F2 e F3 sem aparecer na fila de falhas. A recuperação exige intervenção manual no banco. A suíte em SQLite não detecta o defeito. O achado já constava como T-02 na auditoria de 29/09 e não foi corrigido.
- **Ação:** P-04.

### AUD-02 — O relatório técnico tem erros factuais e uma contradição interna
- **Origem:** A1-02.
- **Natureza:** defeito, no entregável avaliado.
- **Severidade:** **alta**.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 2 deu CONFIRMADO e manteve alta.
- **Esperado:**
  - O `Guia.pdf` atribui a demanda à ArchCorp.
  - `AGENT.md` NUNCA: não apresentar OIDC sem evidência.
  - O relatório deve ser coerente com o código.
- **Observado:**
  - A §1.1 diz que "A Localiza recebeu a tarefa…" e cita como [1] o plano da ArchCorp. O `Guia.pdf` não aparece nas referências.
  - A §6.2 diz que o protótipo "simula tokens OIDC", mas o código usa tokens fixos (`security.py:11-34`). A própria §12.3 diz "não oferece OIDC".
  - A §8 diz que o reprocessamento "preserva o contador". O código faz `event.attempts = 0` (`main.py:554`), como diz a §12.3.
  - A frase sobre OIDC também está em `TO_BE.md` e `tools/build_report.py:296`.
- **Localização:** `output/Relatorio_Tecnico_Cenario_4.docx` (§1.1, §6.2, §8, §12.3, Referências); gerador `tools/build_report.py:182,296,367,373`.
- **Reprodução:** `unzip -p output/Relatorio_Tecnico_Cenario_4.docx word/document.xml` e extrair os `<w:t>`. Texto extraído em `evidencias/agente1/` (E1-23).
- **Impacto:** o principal entregável contradiz o enunciado, o protótipo e a si mesmo. Persiste desde a auditoria de 29/09 (C-01, C-02, C-04, C-08).
- **Ação:** P-27.

### AUD-03 — O relatório não cumpre a estrutura exigida pelo Guia
- **Origem:** A1-03.
- **Natureza:** defeito, frente ao enunciado.
- **Severidade:** **alta**.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 3 deu CONFIRMADO e manteve alta, com contagem e renderização próprias.
- **Esperado:** o `Guia.pdf` pede um artigo de 15–20 páginas com:
  - fundamentação com os conceitos listados e citações diretas e indiretas;
  - metodologia com integrantes e contribuições;
  - justificativa na introdução;
  - diagramas da arquitetura atual e da proposta, de componentes e de integração.
- **Observado:**
  - Medidas do arquivo: 2.726 palavras; 17 quebras forçadas (`pageBreakBefore`); página Carta (12240×15840); 0 `drawing`/`pict` e nenhuma pasta `word/media`.
  - Renderizado, tem 18 páginas, a maioria com 114–216 palavras. A faixa de 15–20 páginas vem da paginação, não do conteúdo.
  - Integrantes aparecem como "pendentes".
  - Não há citação direta, e a referência [8] não é citada no texto.
  - A fundamentação omite camadas, BPM, padrões arquiteturais e integração de sistemas.
  - Não há justificativa na introdução.
- **Localização:** `output/Relatorio_Tecnico_Cenario_4.docx`; `tools/build_report.py:134-135,170`.
- **Reprodução:** `soffice --headless --convert-to pdf` numa cópia. Montagem em `evidencias/agente1/render/rel_montage.png`.
- **Impacto:** faltam itens obrigatórios da avaliação acadêmica.
- **Ação:** P-27, P-35.

### AUD-04 — Reprocessar um `CustomerUpdated.v1` antigo sobrescreve a projeção mais nova
- **Origem:** A2-03.
- **Natureza:** defeito.
- **Severidade:** **média**. A frente 2 propôs alta; a frente 3 rebaixou para média. O coordenador adota média.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 3 deu CONFIRMADO COM AJUSTE e reproduziu em PG com script próprio (`scripts/ordem_exp.py`, `logs/ordem_customer_updated_pg.log`).
- **Esperado:**
  - `AGENT.md`: não aplicar "última escrita vence"; o reprocessamento não pode duplicar ou corromper efeitos.
  - RF-05 e RF-07.
- **Observado:** a v1 falha, a v2 é aplicada, e reprocessar a v1 grava "Nome Versao 1" na projeção de Contracts, enquanto o CRM, fonte oficial, mantém "Nome Versao 2".
- **Localização:** `src/archcorp/contracts/service.py:144-147`, com `UPDATE` incondicional (conferido pelo coordenador); `main.py:547-556`.
- **Reprodução:** `evidencias/agente2/exp/e09_ordem_contrato.py` e `evidencias/agente3/scripts/ordem_exp.py`.
- **Motivo do rebaixamento:** hoje o cenário só se materializa com falha injetada em memória. Com uma falha real de banco, o evento cai em AUD-01, fica `PENDING` e depois é aplicado na ordem correta. O risco passa a ser real assim que AUD-01 for corrigido, então P-04 e P-08 devem ser entregues juntos.
- **Impacto:** projeção divergente da fonte oficial, sem registro de inconsistência.
- **Ação:** P-08.

### AUD-05 — Com o broker configurado e fora do ar, o evento vira FAILED depois que os consumidores internos já concluíram; motivo vazio; 10–15 s por evento
- **Origem:** A2-02 + A3-04, fundidos.
- **Natureza:** defeito, mais um risco de descarte da cópia.
- **Severidade:** **média**. A frente 2 propôs alta; a frente 3 rebaixou para média. O coordenador adota média.
- **Confiança:** alta; o descarte da cópia tem confiança média.
- **Revisão cruzada:** o Agente 3 deu CONFIRMADO e fundiu os dois achados.
- **Esperado:**
  - README e ESTADO dizem que o RabbitMQ recebe uma "cópia opcional".
  - `AGENT.md` pede timeout em chamadas externas, motivo preservado e retentativa só para erro transitório, com backoff.
- **Observado:**
  - `_publish_broker` roda dentro do mesmo `try` dos consumidores. Fatura, processo e inbox são confirmados, mas o evento vai a `FAILED` após 3 despachos, com `reason=""` (o `str(exc)` do pika vem vazio).
  - Não há timeout explícito no `pika`, então valem os padrões: 10 s para host que não responde e 15 s para TCP sem handshake AMQP. O despacho é síncrono e custa N×10–15 s.
  - Não há `queue_declare`, `queue_bind` nem confirmação de entrega, então a cópia é descartada pelo broker. Isso é inferência por inspeção, sem RabbitMQ real.
- **Localização:** `src/archcorp/integration/service.py:32,48-64`; `docker-compose.yml` (`RABBITMQ_URL`).
- **Reprodução:** `evidencias/agente3/scripts/rabbit_exp.py` e `rabbit_timing.py`; `evidencias/agente2/exp/e04_falhas.py` (C) e `e05_bloqueio.py` (C2).
- **Motivo da severidade média:** não há perda nem duplicação de efeito. O Render não define `RABBITMQ_URL`, e no Compose a API só sobe depois do broker saudável. Sobe para alta se a demonstração usar o Compose e o broker cair depois da inicialização.
- **Ação:** P-07.

### AUD-07 — T01–T05 marcadas como "Concluído" nas ferramentas sem o aceite exigido
- **Origem:** A1-01.
- **Natureza:** divergência documental, com risco de processo.
- **Severidade:** **média**. A frente 1 propôs alta; a frente 2 rebaixou para média. O coordenador adota média.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 2 deu CONFIRMADO COM AJUSTE, com reconsulta ao Jira e ao GitHub.
- **Esperado:**
  - `CRONOGRAMA:64` diz que "Concluído exige link para artefato e verificação".
  - O critério de T01 inclui a revisão do professor; o de T05 diz "Aprovar".
  - `AGENT.md` NUNCA: não marcar como concluída uma entrega sem atender aos critérios.
- **Observado:**
  - Em 29/09, entre 13:39 e 13:44 (-03), ARCH7-1..5 foram para "Concluído" sem resolução, minutos depois de comentários do próprio autor dizendo "não marcado como concluído" e "preservada em revisão".
  - As issues GitHub #4–#8 foram fechadas às 16:54Z com `status:concluido`, e o Trello acompanhou.
  - O repositório mantém "Em revisão/Em andamento". Não há evidência de revisão docente.
- **Ajuste da revisão:**
  - Só o critério de T01 exige explicitamente o professor; T05 diz "Aprovar" sem dizer quem aprova.
  - A causa (transição manual ou efeito do fechamento da sprint) não foi determinada, porque o changelog do Jira não foi consultado.
- **Localização:** Jira ARCH7-1..5; GitHub #4–#8; Trello; `docs/CRONOGRAMA_EXECUCAO.md:40-44`.
- **Ação:** P-02.

### AUD-08 — A matriz de rastreabilidade marca como "Atendido" itens sem evidência
- **Origem:** A1-04, ampliado pela frente 2.
- **Natureza:** divergência documental.
- **Severidade:** **média**. Sobe para alta se a matriz for anexada à entrega sem correção.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 2 deu CONFIRMADO COM AJUSTE.
- **Observado:**
  - DOC-01 cita "figuras do relatório inspecionadas", mas o DOCX tem 0 figuras.
  - DOC-03 e DOC-04 apontam para arquivos anteriores a T06–T09.
  - SEC-01 (cujo título é OIDC) e OBS-01 (cujo título é traces) aparecem como "Atendido", com ressalvas na mesma célula.
  - Ampliação pela frente 2: DOC-02 e INTEROP-01 (AUD-20, AUD-21), RF-05 (AUD-04), RF-07 (AUD-01) e RF-06, que não tem teste, aparecem como atendidos.
- **Localização:** `docs/MATRIZ_RASTREABILIDADE.md:16,31,33-36`.
- **Ação:** P-03.

### AUD-09 — O pagamento aceita frações de centavo; o resultado depende do banco
- **Origem:** A2-04.
- **Natureza:** defeito.
- **Severidade:** **média**. A frente 2 propôs alta; a frente 1 rebaixou para média. O coordenador adota média.
- **Confiança:** alta.
- **Revisão cruzada:** o Agente 1 deu CONFIRMADO COM AJUSTE (experimento próprio `evidencias/agente1/rx/`). O Agente 3 confirmou em PG (`logs/pagamento_fracao_pg.log`).
- **Observado:**
  - `PaymentInput.amount` não tem `decimal_places=2` (`finance/routes.py:42`). Outros schemas têm essa restrição.
  - Pagamentos de `0.001` e `0.004` retornam 201 e são gravados como 0,00.
  - As comparações das linhas 129 e 135 usam o valor não quantizado, mas o saldo soma os valores relidos do banco com 2 casas.
  - Em PG, um pagamento de 100.095 sobre uma fatura de 100.10 retorna 201 e é gravado como 100.10, com `paidAmount` igual ao valor da fatura e status ainda **OPEN**. Pelo código, os pagamentos seguintes dariam 409 e a fatura acabaria OVERDUE mesmo paga. Essa continuação não foi executada.
- **Motivo da severidade média:** exige entrada com mais de 2 casas enviada por quem tem papel `finance`/`admin`, e o pagamento é simulado. Ainda assim viola RNF-01 e o critério de T12.
- **Ação:** P-09.

---

## Tabela consolidada (todos os achados)

Colunas: severidade final, natureza, confiança, esperado (fonte), observado (resumo), localização, reprodução e impacto. O detalhamento completo está no registro da frente de origem.

| ID | Sev. | Nat. | Conf. | Título | Esperado (fonte) | Observado / localização | Reprodução | Impacto | Origem | Ação |
|---|---|---|---|---|---|---|---|---|---|---|
| AUD-01 | Alta | Defeito | Alta | Erro de banco no consumidor bloqueia a outbox | AGENT.md Confiabilidade; RNF-02 | `integration/service.py:24-45` sem rollback | `poison_exp.py` (PG) | F2/F3 param sem aparecer em falhas | A3-01, A2-01 | P-04 |
| AUD-02 | Alta | Defeito | Alta | Relatório com erros factuais e contradição | Guia; AGENT.md NUNCA | DOCX §1.1/§6.2/§8 | extração do XML | Entregável contradiz enunciado e código | A1-02 | P-27 |
| AUD-03 | Alta | Defeito | Alta | Relatório fora da estrutura do Guia | Guia "Relatório Técnico" | 2.726 palavras, 0 figuras, sem integrantes | render LibreOffice | Itens obrigatórios ausentes | A1-03 | P-27 |
| AUD-04 | Média | Defeito | Alta | Reprocessamento sobrescreve projeção mais nova | AGENT.md (sem "última escrita vence"); RF-05 | `contracts/service.py:144-147` | `e09`, `ordem_exp.py` | Projeção diverge da fonte oficial | A2-03 | P-08 |
| AUD-05 | Média | Defeito | Alta | Broker indisponível marca FAILED após os efeitos; motivo vazio; 10–15 s por evento | README "cópia opcional"; AGENT.md timeout | `integration/service.py:32,48-64` | `rabbit_exp.py`, `rabbit_timing.py` | Falsa falha; despacho lento | A2-02, A3-04 | P-07 |
| AUD-06 | Média | Dívida | Alta | Arquitetura hexagonal só parcial | AGENT.md Arquitetura | portas recebem `Session`; regras nas rotas de finance/support/workflow; `main.py` com 619 linhas; `pika` direto | AST (E2-02) | Evolução e testes mais caros | A2-11 | P-25 |
| AUD-07 | Média | Doc | Alta | T01–T05 "Concluído" sem aceite | CRONOGRAMA:64; T01/T05 | Jira ARCH7-1..5; GitHub #4–#8; Trello | JQL; `gh issue view` | Progresso inflado | A1-01 | P-02 |
| AUD-08 | Média | Doc | Alta | Matriz marca "Atendido" sem evidência | AGENT.md NUNCA | `MATRIZ:16,31,33-36` | comparação com ESTADO e DOCX | Cobertura superestimada | A1-04 | P-03 |
| AUD-09 | Média | Defeito | Alta | Pagamento com frações de centavo | RNF-01; T12 | `finance/routes.py:42,129-135` | `e07`, `rx/x1`, `pagamento_fracao_pg.log` | Fatura presa em OPEN em PG | A2-04 | P-09 |
| AUD-10 | Média | Defeito | Alta | Ativação concorrente ou duplo clique gera 2 `ContractActivated.v1` | Fluxo mínimo 2; RNF-02 | `contracts/service.py:62-87`; `App.tsx:50,99` | `conc_exp.py` 15/15; `web_journey.py` | Fato duplicado para integrações | A2-06, A3-03 | P-06 |
| AUD-11 | Média | Defeito | Alta | Despacho concorrente sem lock: `[200,500]` | RNF-02/RNF-08 | `integration/service.py:22` | `conc_exp.py` (PG) | 500 ao operador; impede escala | A2-05, A3-02 | P-05 |
| AUD-12 | Média | Defeito | Alta | Efeito parcial do consumidor que falhou é confirmado | AGENT.md (rollback) | `integration/service.py:25-45` | `e04` (A) | Futuros handlers duplicariam efeitos | A2-07 | P-04 |
| AUD-13 | Média | Doc | Alta | Docs e entregáveis anteriores à implementação (TO-BE/DDD com 3 eventos de 6; `output/` de 27/09) | T19; AGENT.md SEMPRE | `TO_BE.md:63-75`; DDD; `output/*` | `git log -1 -- output/` × `-- src/` | Entregáveis descrevem versão anterior | A1-05, A2-19 | P-27..P-29 |
| AUD-14 | Média | Doc | Alta | Contagens de testes divergentes (13/17/18/57) | termino1 Gate 2 | `MATRIZ:59`; `termino1.md:3`; DOCX; slide 14 | grep `def test_`; pytest 57/57 | Evidência vigente ambígua | A1-06 | P-03 |
| AUD-15 | Média | Doc | Alta | Status divergente entre repositório, Jira, GitHub e Trello (T06–T09 e outras) | CRONOGRAMA:10 | CRONOGRAMA:45-48; issues #9–#12 abertas após merge do PR #28 | E1-28..E1-32 | Sem fonte única de progresso | A1-09 | P-31 |
| AUD-16 | Média | Doc | Alta | Fonte de verdade nº 1 inexistente; Localiza e hipóteses tratadas como fato | AGENT.md:37-44 e NUNCA | `AGENT.md:39`; `AS_IS.md:25-29`; `ADR-001:12`; `PLANO:52` | `ls`; buscas no Drive/Notion | Revisores buscam fonte inexistente | A1-07, A1-08 | P-30 |
| AUD-17 | Média | Defeito | Alta | Apresentação incompleta frente aos 13 tópicos do Guia | Guia "Apresentação" | sem slides de APIs e manutenção; slide 11 com título errado; sem equipe | `apr_montage.png` | Lacunas na avaliação oral | A1-10 | P-28 |
| AUD-18 | Média | Doc | Média | T21: Notion, Drive e Project não comprovados; arquivos de sincronização fora do Git | T21 | `EVIDENCIAS:11`; `.gitignore:229` | buscas MCP | 2 de 5 destinos não verificáveis | A1-12 | P-32 |
| AUD-19 | Média | Meta | Alta | T14 não cobre custo zero, limites e evolução comercial | T14 | `VISAO_NEGOCIO.md` | grep render/supabase/free | Critério interno aberto (no prazo) | A1-11 | P-33 |
| AUD-20 | Média | Defeito | Alta | 11 de 261 exemplos OpenAPI inválidos; dinheiro string × número | T06; RNF-01 | `schemas.py:110-113,230-250`; `contracts/service.py:154` | `e11`, `e10` | Clientes de API inconsistentes | A2-08 | P-10 |
| AUD-21 | Média | Defeito | Alta | `Money` do AsyncAPI (`multipleOf 0.01`) rejeita 19,99 | T06; RNF-01 | `asyncapi.yaml` `Money` | `e10` | Contrato rejeita envelopes reais | A2-09 | P-10 |
| AUD-22 | Média | Dívida | Alta | Contracts e Support importam `integration.models`; `main.py` lê e escreve outbox; testes de fronteira cegos | AGENT.md (fronteiras); ADR-001 r.13 | `contracts/service.py:11`; `support/service.py:9`; `main.py:26,534-592` | `imports_ast.py`; `e13` (detecta 1 de 8 casos) | Erosão das fronteiras sem alarme | A2-10 | P-24 |
| AUD-23 | Média | Risco | Média | `alembic_version` e sequências expostas a `anon`; anon impede a inicialização | README (REVOKE); T17 | `infrastructure/db.py:18-29` | `uvicorn_pg_after_anon_delete.log` (Supabase simulado) | Negação de serviço na demo pública | A3-05 | P-11 |
| AUD-24 | Média | Defeito | Alta | `/metrics` público e com cardinalidade ilimitada | RNF-03/04 | `observability.py:34-47`; `main.py:411-419` | `metrics_publico.txt` (600 séries) | Memória ilimitada; IDs expostos | A3-07 | P-12 |
| AUD-25 | Média | Risco | Alta | starlette 0.47.3 (transitiva) com 7 advisories; Range afeta os arquivos estáticos | T17/T18 | `requirements.txt:1` | `pip_audit_pypi.log`; `range_header_starlette.log` (7,6 s) | Degradação por requisição anônima | A3-09 | P-13 |
| AUD-26 | Média | Defeito | Alta | Frontend: chave nova por clique, formulário apagado no erro, painel só com admin, erros em inglês | T10; AGENT.md Idempotency-Key | `web/src/App.tsx:27,47-69,89,97-105` | `web_journey.py`; `shots/03,06,12` | Reenvio duplica; UX ruim | A3-10, A2-16 (parte UI) | P-06, P-18 |
| AUD-27 | Média | Defeito | Alta | Acessibilidade: contraste insuficiente (*serious*) e landmarks ausentes | T18 | `web/src/style.css`; `App.tsx:89` | axe-core 4.13 (fonte de fallback) | Critério de T18 aberto | A3-11 | P-18 |
| AUD-28 | Média | Meta / risco | Alta | Encerramento não se propaga a Finance/Support; preparação concluída com tarefa cancelada | T09/T12 | `workflow/service.py:67-79`; `main.py:342` | `e08`, `e07` | Estados incoerentes após encerramento | A2-12 | P-22 |
| AUD-29 | Média | Defeito | Alta | Inadimplência só na leitura; pagamentos sem auditoria | T12; AGENT.md auditoria | `finance/routes.py:80-87,117-138` | `e07` | Sem trilha de operação crítica | A2-14 | P-23 |
| AUD-30 | Média | Defeito | Alta | Workflow sem máquina de estados de tarefa e sem retorno ao Support | T16 | `workflow/routes.py:125-142` | `e08` | Transições inválidas aceitas | A2-13 | P-21 |
| AUD-31 | Média | Doc | Alta | Sem backoff/jitter; log de falha sem `eventId`; reprocessamento sem solicitante | AGENT.md; ADR-001 r.12 | `integration/service.py:21-46`; `main.py:547-556` | E2-12, E2-20 | Diagnóstico e auditoria fracos | A2-15 | P-04 |
| AUD-32 | Média | Defeito | Alta | Formatter JSON descarta a exceção (sem tipo nem stack) | AGENT.md (contexto do erro) | `observability.py:15-25` | grep nos logs da concorrência | Erros 500 sem causa | A3-08 | P-14 |
| AUD-34 | Média | Risco | Alta | Credencial pública com todos os papéis; sem limite de tentativas | T17 | `security.py:28-31`; `main.py:352-353` | `uvicorn_pg_public*.log` | Qualquer portador é admin | A3-12 | P-15 |
| AUD-35 | Média | Defeito | Alta | `amount` ≥ 10^12 dá 500 em PG (SQLite aceita) | AGENT.md (validação na fronteira) | `schemas.py:111`; `contracts/routes.py:85`; `finance/routes.py:42` | `uvicorn_pg_valid.log` | 500 exposto; pode gerar evento venenoso | A3-06 | P-09 |
| AUD-36 | Média | Dívida | Alta | Qualidade não verificada em PG, concorrência, acessibilidade ou desempenho de F1–F3; RLS por mock; RF-06 sem teste | T18; AGENT.md Testes | `tests/conftest.py:5`; `verify.yml`; `performance_smoke.py:19` | `pytest_postgresql_experimento.log` (57/57 só com conftest alterado) | Defeitos AUD-01/10/11/35 não detectados no CI | A3-13, A1-13 | P-17, P-19 |
| AUD-37 | Média | Doc | Alta | "OIDC simulado", "retentativa controlada" e fila no broker descritos como vigentes | ESTADO_IMPLEMENTACAO | `ATRIBUTOS_QUALIDADE.md`; `TO_BE.md:141`; `ADR-001:73` | grep | Meta apresentada como fato | A3-19, A1 (T05) | P-29 |
| AUD-38 | Média | Dívida | Alta | Gerador de slides com caminhos `C:/Users/...` e runtime local | Guia (continuidade); AGENT.md reprodutível | `tools/build_presentation.mjs:4-11` | inspeção | T19 não reproduzível por outra equipe | A1-14 | P-28 |
| AUD-33 | Baixa | Defeito | Alta | Esquema intermediário sem `alembic_version` falha em PG | ADR-002 | `infrastructure/migrate.py:48-54` | `migracoes_pg.log` (caso 5) | Caso de borda de migração | A3-14 | P-20 |
| AUD-39 | Baixa | Risco | Alta | Idempotência heterogênea (chamado ignora descrição; chaves não escopadas por principal) | AGENT.md Idempotency-Key | `support/service.py:19-22` | E2-14 | Repetição aceita com payload diferente | A2-16 | P-26 |
| AUD-40 | Baixa | Doc | Alta | Validações e códigos de erro divergentes de INTEGRACOES | INTEGRACOES (contrato de erro) | rotas de contracts/support/workflow/finance | E2-07, E2-13, E2-14 | Clientes tratam erros de forma inconsistente | A2-17 | P-26 |
| AUD-41 | Baixa | Defeito | Alta | `dueAt` sem `Z` em SQLite; teste de envelope sem FormatChecker | AGENT.md (ISO 8601 UTC) | `support/service.py`; `workflow/routes.py` | E2-16 | Datas ambíguas | A2-18 | P-10 |
| AUD-42 | Info | Meta | Alta | T20 sem evidência de publicação | T20; regras de conclusão | issue #23 aberta, nenhuma URL | E3-31, E1-35 | Publicação pendente (no prazo) | A3-20 | P-16 |
| AUD-43 | Baixa | Doc | Alta | Jira "Concluído" sem resolução; responsáveis contrários à regra do cronograma | CRONOGRAMA:11 | Jira ARCH7 | E1-30 | Autoria ambígua para T22 | A1-15 | P-31 |
| AUD-44 | Baixa | Risco | Alta | Auditoria de 29/09 não mesclada; a maioria dos achados persiste; PR #29 em rascunho | Rastrear achados | `origin/ccr-1c5dff06-gdznnu`; PR #29 | E1-19, E1-27 | Problemas reaparecem a cada rodada | A1-16 | P-34 |
| AUD-45 | Baixa | Risco | Alta | Chamado pendente aceita contrato inexistente e abre processo | RNF-06 | `support/service.py` | E2-14 | Processo de 24 h para contrato inexistente | A2-20 | — |
| AUD-46 | Baixa | Risco | Alta | Sem cabeçalhos de segurança; 405 fora de `problem+json`; Google Fonts externas | AGENT.md Segurança | middleware ausente | `cabecalhos_cors.log` | Superfície da demo pública | A3-15 | P-14 |
| AUD-47 | Baixa | Risco | Alta | E-mail em query string no log de acesso | RNF-03 | uvicorn access log | E3-22 | Dado pessoal em log | A3-16 | P-14 |
| AUD-48 | Baixa | Defeito | Alta | Mesma chave em paralelo retorna 409 em vez de replay; reserva sem chave duplica | AGENT.md Idempotency-Key | contracts/IdempotencyStore | `concorrencia_pg_1worker.log` | Cliente legítimo recebe conflito | A3-17 | P-26 |
| AUD-49 | Baixa | Dívida | Média | Transitivas sem pin nem hash; imagem como root e sem digest; Node e Python divergentes entre local e CI | AGENT.md reprodutível | `requirements*.txt`; `Dockerfile` | `freeze_311/312.txt` | Builds não reproduzíveis | A3-18 | P-13 |
| AUD-50 | Info | Risco | Alta | Trabalho declarado (`execucao-tarefas-pendentes`/`3fdb533`, 13 commits) não publicado no remoto | CRONOGRAMA ("código local isolado não comprova") | `git ls-remote` sem a ref; `git cat-file` falha | E1-17, briefing | Progresso posterior a `3a3d8bd` não auditável | Coordenador (L-01) | P-01 |

## Divergências entre frentes e como foram resolvidas

| Achado | Posições | Resolução do coordenador |
|---|---|---|
| AUD-04 (A2-03) | Frente 2: alta. Frente 3: média, porque hoje só ocorre com falha injetada | **Média**, com obrigação de entregar P-08 junto com P-04, porque a correção de AUD-01 torna o caminho alcançável |
| AUD-05 (A2-02/A3-04) | Frente 2: alta. Frente 3: média | **Média**: sem perda nem duplicação de efeito, e o broker não é usado no Render. Sobe para alta se a demonstração usar o Compose |
| AUD-07 (A1-01) | Frente 1: alta. Frente 2: média | **Média**: o repositório mantém o status correto e a correção é trivial. A regra NUNCA continua violada nas ferramentas |
| AUD-08 (A1-04) | Frente 1: alta. Frente 2: média | **Média**, condicionada: alta se a matriz for anexada à entrega sem P-03 |
| AUD-09 (A2-04) | Frente 2: alta. Frente 1: média | **Média**: exige papel `finance` e entrada com mais de 2 casas; o pagamento é simulado |
| AUD-01 | Frentes 2 e 3: alta. Frente 1: alta com ajuste de texto | **Alta**; o texto foi ajustado para separar o bloqueio permanente (injetado) do 500 transitório (real) |
| A1-17 | Frente 1 levantou o diretório criado em `output/` | **Não procede**: o coordenador criou o diretório de propósito para este pacote |

Não restaram divergências sem resolução.
