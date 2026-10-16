---
name: archcorp-diagnostico
description: >
  Use antes de corrigir quando a causa não é óbvia no ArchCorp: falha intermitente, teste que
  quebra só no PostgreSQL ou só na CI, efeito duplicado ou ausente após despacho da outbox,
  regressão de desempenho, ou quando a tarefa pede só investigação.
---

# Diagnóstico no ArchCorp

Evidência antes de edição. Sem um laço que fica vermelho **neste** defeito, não há hipótese.

## 1. Construa o laço de feedback (a parte que importa)

Um comando, já executado, que reproduz o **sintoma exato** do registro da tarefa, de forma
determinística e em segundos. Opções, nesta ordem:

1. Teste `pytest` na seam que alcança o defeito (`archcorp-tdd`):
   `PYTHONPATH=src python -m pytest tests/<arquivo>.py -k <nome> -q -p no:cacheprovider`.
2. Sequência HTTP contra `uvicorn` local ou pelo `client` de teste, incluindo
   `POST /api/v1/integration/outbox/dispatch` quando o efeito atravessa contextos.
3. Reprodução de envelope: pegue o `OutboxEvent` gravado e chame o consumidor com
   `event.envelope()` isoladamente.
4. Diferencial: mesma entrada em SQLite e em PostgreSQL (`TEST_DATABASE_URL` descartável), ou base
   × candidato.
5. Para falha intermitente: repita o gatilho muitas vezes, fixe relógio e dados, aumente a taxa de
   reprodução até ser depurável.

Aperte o laço: mais rápido, sinal mais específico (o sintoma, não "não quebrou"), mais
determinístico (relógio injetado, dados sintéticos fixos).

Não conseguiu construir o laço? **Pare** e devolva ao coordenador o que tentou e o que falta
(acesso, artefato, permissão). Não hipotetize sem laço.

## 2. Reproduza e reduza

Confirme que o laço mostra o defeito descrito, não um vizinho. Reduza o cenário retirando um
elemento por vez até que tudo o que sobra seja necessário para ficar vermelho. O cenário mínimo
vira o teste de regressão.

## 3. Hipóteses ranqueadas

Escreva de 3 a 5 hipóteses **falseáveis** antes de testar qualquer uma:
"Se X é a causa, então mudar Y faz o defeito sumir e mudar Z o piora."
Separe sintoma observado de causa inferida. Ordene por evidência e pelo custo de falsear.
Suspeitos frequentes aqui: relógio do consumidor, ordem de eventos, transação aninhada,
diferença SQLite/PostgreSQL, fixture `clean_database`, impressão digital de idempotência.

## 4. Instrumente uma variável por vez

Cada sonda testa uma previsão. Prefira depurador ou asserção pontual; se precisar de log, use um
prefixo único (`[DIAG-xxxx]`) para removê-lo com uma busca. Nunca registre token, descrição de
chamado ou payload sensível (`archcorp-seguranca`). Desempenho: meça antes (linha de base), depois
mude.

## 5. Conclua

- Causa nomeada com a prova (comando e saída relevantes, sem segredos).
- Se a tarefa autoriza correção: siga `archcorp-implementacao`, modo correção.
- Se não autoriza: entregue só o diagnóstico.
- Se não existe seam correta para o teste de regressão, isso é um achado; registre-o.
- Remova toda instrumentação `[DIAG-...]` e harness temporário antes da entrega.
