# Revisão cruzada (onda 2) — Agente 3

Referência `3a3d8bd`. Tudo foi executado na cópia isolada `$SP/iso`; o manifesto continuou OK. O PostgreSQL 16 descartável em `/tmp/a3pg` (porta 55432, só 127.0.0.1) foi ligado para estes testes e parado ao final. Os logs estão em `$A/logs/`.

---

## A2-01 → convergência com A3-01

- **Veredito: CONFIRMADO, sem nova revisão** (já convergente com o meu A3-01, reproduzido em E3-17/E3-18 e confirmado pelo Agente 1).
- Causa raiz única: em `integration/service.py:37-45`, o `except` chama `commit()` sem `rollback()`. Isso gera `PendingRollbackError` e HTTP 500. O evento fica PENDING com `attempts=0` e trava a outbox.
- Recomendação: fundir A2-01 e A3-01 num único achado, severidade **alta**.
- A mesma causa aparece em mais dois experimentos meus nesta onda:
  - o despacho concorrente (A3-02);
  - o "caminho 1" da revisão de A2-03, abaixo: um erro transitório real de banco também deixa o evento preso, em vez de levá-lo a FAILED.

---

## A2-02 — RabbitMQ configurado e fora do ar: FAILED com motivo vazio, cerca de 10 s por evento, sem timeout explícito

- **Veredito: CONFIRMADO.** Recomendo **fundir com A3-04**, sob o título "Falha do broker opcional marca eventos como FAILED após efeitos concluídos, com motivo vazio e 10–15 s de bloqueio por evento".
- **Severidade do achado fundido: média**, a subir para alta se a avaliação for feita pelo Compose com o broker instável. Justificativa abaixo.

**Evidência executada** (`$A/rabbit_timing.py`, que chama `EventDispatcher._publish_broker` diretamente; log `logs/rabbit_tempo_por_evento.log`, 2026-10-01T21:07:50Z):
```
porta fechada: 0.02s por evento -> AMQPConnectionError str(exc)=''
host 10.255.255.1 (sem rota/descartado): 10.01s por evento -> AMQPConnectionError str(exc)=''
TCP aceito sem handshake AMQP: 15.01s por evento -> AMQPConnectorStackTimeout str(exc)="Timeout during AMQP handshake..."
```
O experimento do fluxo inteiro (`logs/rabbit_porta_fechada.log`) mostrou mais três pontos:
- fatura e processo são criados;
- o evento vai a `('FAILED', 3, '')` no 3º despacho;
- o reprocessamento falha de novo.

**Código:**
- `integration/service.py:53` usa `pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))`. Não há `socket_timeout`, `stack_timeout`, `blocked_connection_timeout` nem `connection_attempts` explícitos (grep em `src/`: 0 ocorrências).
- Valem os padrões do pika 1.3.2 (`pika/connection.py:52-65`): `DEFAULT_SOCKET_TIMEOUT = 10.0`, `DEFAULT_STACK_TIMEOUT = 15.0`, `DEFAULT_BLOCKED_CONNECTION_TIMEOUT = None`, `DEFAULT_CONNECTION_ATTEMPTS = 1`. Ou seja, o tempo por evento vem desses padrões, e uma conexão nova é aberta para cada evento.
- O despacho é síncrono dentro do `POST /dispatch`. Com N eventos pendentes, a requisição leva cerca de N×10 s, ou N×15 s se o host aceitar TCP e não responder.
- A publicação está no mesmo `try` dos consumidores (linha 32), por isso o evento conta tentativa mesmo depois de os efeitos de negócio terem sido commitados.
- Não existe `queue_declare`, `queue_bind` nem `confirm_delivery` no código; o grep deu 0. Isso confirma por inspeção a afirmação do A2-02 de que a "cópia" vai para uma exchange topic sem fila e é descartada pelo broker. Não executei com RabbitMQ real.

**Por que média e não alta:**
- Não há perda nem duplicação de efeito de negócio: os consumidores internos rodam e a inbox fica registrada, então o reprocessamento não reaplica os consumidores.
- O Render (`render.yaml`) não define `RABBITMQ_URL`, então a demonstração pública não é afetada.
- No Compose, `RABBITMQ_URL` é definido por padrão, mas a API só sobe depois do RabbitMQ (`depends_on: service_healthy`). O defeito aparece se o broker cair depois da inicialização.
- Contra isso pesam o diagnóstico enganoso (FAILED com motivo vazio para fatos já processados) e o bloqueio longo da requisição.

**Divergências:**
- O A2-02 mediu 30,1 s para 3 eventos, cerca de 10 s cada; isso bate com os meus 10,01 s.
- No meu primeiro experimento (E3-20) o host 192.0.2.1 falhou em 0,05 s porque a rede do contêiner recusa esse destino. O 10.255.255.1 reproduz o caso de timeout. Vou corrigir a limitação registrada em E3-20 com este resultado.
- Acrescento o caso de 15 s (TCP aceito sem handshake AMQP), que o A2-02 não cobriu.

---

## A2-03 — Reprocessar um `CustomerUpdated.v1` antigo sobrescreve a projeção mais nova em Contracts

- **Veredito: CONFIRMADO COM AJUSTE.** O mecanismo foi reproduzido de forma independente em PostgreSQL. O ajuste é que hoje ele só é alcançável por uma exceção de consumidor que não seja de banco.
- **Severidade: média** (o A2-03 propôs alta).

**Código:**
- `contracts/service.py:142-145`: `apply_customer_update` executa `UPDATE contracts_contracts SET customer_name, customer_email WHERE customer_id=...` sem condição de versão ou data. É "última escrita vence", contra a regra do `AGENT.md`.
- `main.py:547-556`: o reprocessamento volta qualquer evento FAILED para PENDING, sem verificar se existem eventos mais novos do mesmo agregado.
- O payload (`crm/service.py:43`) não leva versão nem `updatedAt` do cliente.

**Evidência executada** (meu script `$A/ordem_exp.py`, PG `ordem`, 2026-10-03T13:52:35Z, log `logs/ordem_customer_updated_pg.log`):
```
== Caminho 1: falha transitória de banco real (lock_timeout) ==
  despacho 1: 500 ...  outbox=[('Nome Versao 1', 'PENDING', 0, '')]
  despacho 2: 500 ...  outbox=[('Nome Versao 1', 'PENDING', 0, '')]
  despacho 3: 500 ...  outbox=[('Nome Versao 1', 'PENDING', 0, '')]
  após liberar lock: 200 {'processed': 1, 'failed': 0} projeção='Nome Versao 1' outbox=[('Nome Versao 1', 'PUBLISHED', 0, '')]
== Caminho 2: falha transitória não-banco (exceção Python) ==
  após 3 despachos: outbox=[('Nome Versao 1', 'FAILED', 3, 'Contracts indisponível (simulado)')] projeção='Nome Original'
  despacho v2: {'processed': 1, 'failed': 0} projeção='Nome Versao 2'
  reprocess v1: 200; despacho: {'processed': 1, 'failed': 0}
  RESULTADO: CRM (fonte oficial)='Nome Versao 2'  projeção Contracts='Nome Versao 1'
```

**Método, independente do script do Agente 2:**
- No caminho 1 usei uma falha transitória real de banco: uma linha de `contracts_contracts` bloqueada por outra conexão e `lock_timeout=300ms` na URL da aplicação.
- No caminho 2 usei uma exceção Python injetada no consumidor, com mecanismo próprio (troca da tupla do handler).

**Por que o ajuste de severidade:**
- O caminho 1 mostra que um erro de banco transitório, que é o modo de falha realista para este consumidor de um único `UPDATE`, não leva o evento a FAILED. O evento cai no defeito A3-01/A2-01 (500 e PENDING) e depois é aplicado na ordem correta, sem sobrescrita.
- Se o broker falhar, o evento vai a FAILED mas a inbox já registrou o consumo, então o reprocessamento pula o consumidor e também não sobrescreve (inspeção de `integration/service.py:27-29`).
- O cenário só se materializa com uma exceção não relacionada a banco dentro do consumidor, algo que o código atual não produz sem injeção. Também passará a se materializar quando A3-01 for corrigido: com rollback, erros de banco passam a levar a FAILED e o reprocessamento tardio passa a sobrescrever.
- O dado afetado é a cópia desnormalizada de nome e e-mail em Contracts; o CRM continua sendo a fonte correta. Por isso, defeito latente, severidade média, que deve ser corrigido junto com A3-01.

**Divergências:**
- O resultado confere com o E2-15 ("Nome Versao 1" na projeção e "Nome Versao 2" no CRM).
- Divirjo só da severidade e da alcançabilidade.
- Sugiro que o aceite da correção de A3-01 inclua o teste "falha v1 → aplica v2 → reprocessa v1 mantém v2".

---

## A1-03 — Relatório: 18 páginas Carta, cerca de 2.726 palavras, 17 quebras forçadas, sem figuras nem integrantes

- **Veredito: CONFIRMADO.**
- **Severidade: alta** frente ao enunciado/Guia, já que é o entregável final avaliado. Concordo com o A1.

**Evidência executada** sobre uma cópia própria (`$A/rel/Relatorio_Tecnico_Cenario_4.docx`; SHA-256 `740de917…1966`, igual ao manifesto e à cópia do Agente 1):
- **Parse de `word/document.xml`** (texto extraído em `$A/rel/texto.txt`):
  - 2.726 palavras;
  - 17 quebras forçadas, todas por `pageBreakBefore` e nenhuma por `<w:br w:type="page"/>`;
  - 1 `sectPr`;
  - `<w:pgSz w:w="12240" w:h="15840"/>`, ou seja, **Carta**, não A4;
  - `<w:drawing>` 0 e `<w:pict>` 0;
  - **`word/media` não existe**.
- **Renderização independente** (`soffice --headless --convert-to pdf`, `pdfinfo`): `Pages: 18`, `Page size: 612 x 792 pts (letter)`.
- **Densidade por página** (contagem `pdftotext`): de 32 a 305 tokens por página; a maioria fica entre 114 e 216. Uma página Carta cheia em corpo 11–12 tem algo como 450–550 palavras, então a faixa de 15–20 páginas é atingida por paginação, não por conteúdo.
- **Integrantes:** a capa diz "Equipe do Projeto Aplicado — nomes e contribuições pendentes". A §3.1 diz "A identificação nominal e a contribuição individual serão registradas pela equipe na versão de submissão."
- **Conceitos do Guia** (`guia.txt:466-489`), contagem sem diferenciar maiúsculas:
  - ausentes: "camadas", "BPM", "padrões arquiteturais", "integração de sistemas";
  - mencionados uma única vez: "sistemas corporativos", "microsservi", "distribuíd", "ERP".
- **Citações:** nenhuma citação direta, porque não há aspas (`“` e `"` = 0). As referências [1] a [7] aparecem duas vezes cada (texto e lista); a [8] aparece uma vez, só na lista, portanto não é citada no texto.
- **Estrutura:** não há "Justificativa" na Introdução (o Guia, linha 455, a exige).

**Critério do Guia** (`guia.txt:441-495`): "artigo, de 15 a 20 páginas"; fundamentação com 17 conceitos e "citações diretas e indiretas"; Metodologia com "Descrição dos integrantes e suas respectivas contribuições"; diagramas da arquitetura atual, da proposta, de componentes e de integração (linhas 420-423).

**Divergências:** nenhuma de substância. Detalho só que as "17 quebras forçadas" são todas `pageBreakBefore` em parágrafos (`tools/build_report.py`), e não quebras manuais.

---

## Opcional — pagamento de 100.095 sobre fatura de 100.10 em PostgreSQL (inferência do Agente 1)

- **Veredito: CONFIRMADO** (reproduzido).
- **Severidade: média.** A fatura fica com saldo zero e status OPEN, e depois que vencer passa a ser exibida como OVERDUE.

**Evidência** (`$A/pagamento_exp.py`, PG, 2026-10-03T13:53:51Z, log `logs/pagamento_fracao_pg.log`):
```
fatura=100.10 pagamento_enviado=100.095 -> HTTP 201
   gravado_no_banco=[(Decimal('100.10'),)] fatura_após={'amount': 100.1, 'paidAmount': 100.1, 'status': 'OPEN'}
fatura=100.10 pagamento_enviado=0.004 -> HTTP 201
   gravado_no_banco=[(Decimal('0.00'),)] fatura_após={'amount': 100.1, 'paidAmount': 0.0, 'status': 'OPEN'}
```
Consulta direta: `100.10|OPEN|100.10`.

**Causa** (`finance/routes.py:42,129-136`):
- `amount: Decimal = Field(gt=0)` não define `decimal_places`.
- A verificação `total + body.amount == item.amount` compara o valor não arredondado (100.095 ≠ 100.10), então o status não muda para PAID.
- A coluna `Numeric(14,2)` arredonda para 100.10 ao gravar.
- Pelo código, um pagamento posterior de 0,01 seria recusado, porque 100.10 + 0.01 > 100.10 dá 409; a fatura fica presa em OPEN. Isso é inferência do código, não executei.
- No segundo caso, um pagamento de 0,004 é aceito com 201 e gravado como 0,00.
