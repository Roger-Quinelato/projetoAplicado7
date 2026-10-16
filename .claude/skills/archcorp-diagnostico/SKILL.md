---
name: archcorp-diagnostico
description: >
  Use antes de corrigir quando a causa não está estabelecida no ArchCorp: falha intermitente, teste
  que quebra só no PostgreSQL ou só na CI, efeito duplicado ou ausente após despacho da outbox,
  regressão de desempenho, ou quando a tarefa pede só investigação. Não use quando o registro da
  tarefa já traz a causa comprovada.
---

# Diagnóstico no ArchCorp

Evidência antes de afirmar a causa. Hipóteses podem e devem orientar a coleta de evidência, mas
ficam marcadas como **provisórias** até um laço de reprodução comprová-las.

## 1. Construa o laço de feedback

Um comando, já executado, que reproduz o **sintoma do registro da tarefa** da forma mais
determinística e rápida que o defeito permitir. Opções, nesta ordem:

1. Teste `pytest` na seam que alcança o defeito (`archcorp-tdd`).
   PowerShell: `$env:PYTHONPATH="src"; python -m pytest tests/<arquivo>.py -k <nome> -q -p no:cacheprovider`
   POSIX: `PYTHONPATH=src python -m pytest tests/<arquivo>.py -k <nome> -q -p no:cacheprovider`
2. Sequência HTTP pelo `client` de teste ou contra `uvicorn` local, incluindo
   `POST /api/v1/integration/outbox/dispatch` quando o efeito atravessa contextos.
3. Reprodução de envelope: o `OutboxEvent` gravado, entregue ao consumidor com `event.envelope()`.
4. Diferencial: mesma entrada em SQLite e em PostgreSQL (`TEST_DATABASE_URL` descartável), ou base
   × candidato.
5. Falha intermitente: repita o gatilho, fixe relógio e dados e aumente a taxa de reprodução até
   ser depurável. Registre a taxa observada.

Aperte o laço quando possível: sinal específico (o sintoma, não "não quebrou"), relógio injetado,
dados sintéticos fixos.

## 2. Hipóteses provisórias

Antes e durante a construção do laço, escreva as hipóteses que a evidência atual sustenta, quantas
forem úteis, cada uma falseável: "se X é a causa, mudar Y faz o defeito sumir". Ordene por
evidência e pelo custo de falsear. Separe **sintoma observado** de **causa inferida**.

Suspeitos frequentes neste repositório: relógio do consumidor, ordem de eventos, transação
aninhada, diferença SQLite/PostgreSQL, fixture `clean_database`, impressão digital de idempotência.

## 3. Reproduza, reduza, instrumente

- Confirme que o laço mostra o defeito descrito, não um vizinho.
- Reduza o cenário retirando um elemento por vez; o mínimo vira o teste de regressão.
- Cada sonda testa uma previsão; mude uma variável por vez. Log temporário com prefixo único
  (`[DIAG-xxxx]`), sem token, descrição de chamado ou payload sensível (`archcorp-seguranca`).
- Desempenho: meça a linha de base antes de mudar.

## 4. Conclua com a força certa

| Situação | O que escrever na entrega |
|---|---|
| Laço reproduz e a correção o deixa verde | Causa **comprovada**, com comando e saída relevante |
| Laço reproduz, causa ainda não isolada | Sintoma comprovado; hipóteses **provisórias** e o que as falsearia |
| Sem laço (acesso, artefato, permissão, ambiente) | Entrega `bloqueada`: o que foi tentado e o que destravaria |

- Correção autorizada pelo registro: siga `archcorp-implementacao`, modo correção.
- Só investigação: entregue o diagnóstico; não edite código de produção.
- Sem seam adequada para o teste de regressão: registre como achado.
- Remova toda instrumentação `[DIAG-...]` e harness temporário antes da entrega.
