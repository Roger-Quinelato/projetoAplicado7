---
name: archcorp-pos-merge
description: >
  Use depois de integração efetiva de um ou mais PRs na main do ArchCorp, ou antes de uma entrega
  acadêmica ou publicação, para auditar o estado combinado: interação entre PRs, CI no SHA
  integrado, contratos, documentação e regressões dos três fluxos obrigatórios. Não use para a
  revisão integrada das fases locais de um deepwork.
---

# Auditoria pós-merge

Cada PR foi revisado isoladamente; o risco agora está **entre** eles. Só se aplica a commits já
integrados na `main`; a validação conjunta das fases locais de um deepwork é a revisão integrada
de `archcorp-deepwork`, não esta.

## 1. Congele o intervalo

`HEAD_SHA` é a `main` atual. `BASE_SHA` é, nesta ordem: a base informada no pedido; o `HEAD_SHA`
do último pós-merge registrado; o commit da entrega anterior identificável (tag ou release de
entrega acadêmica). **Na primeira execução sem nenhum desses, pergunte ao responsável humano.**
Não invente intervalo (ex.: "últimos N commits") nem trate o histórico inteiro como auditado.

Liste os PRs e commits do intervalo (`git log --oneline <BASE_SHA>..<HEAD_SHA>`) e o parecer de
cada um. PR integrado sem parecer no SHA final é achado.

## 2. CI no SHA integrado

Confira os jobs do workflow `Verify` **no `HEAD_SHA`**: application, postgresql, rabbitmq. Verde
num PR não prova verde depois da integração. Classifique falhas: produto, contrato, ambiente ou
instabilidade; não reexecute até ficar verde.

## 3. Interações entre PRs

- Dois PRs que tocam o mesmo contexto, evento ou tabela: o comportamento combinado faz sentido?
- Migrações de PRs paralelos: uma cabeça só no Alembic; convergência testada.
- Formato compartilhado alterado por um PR e consumido por outro (payload, enum, `web/src/api.ts`).
- Exceções novas no baseline v1 somadas de vários PRs: todas com ADR?
- Regras ou skills alteradas (`AGENTS.md`, `CLAUDE.md`, `archcorp-*`) coerentes entre si.

## 4. Fluxos obrigatórios

Os três fluxos de `AGENTS.md` continuam provados no `HEAD_SHA`: F1 (CRM → rascunho sem
recadastro), F2 (ativação → cobrança + preparação, sem duplicidade), F3 (elegibilidade/SLA →
chamado → resolução). Use os testes de fluxo e, se a entrega pedir, o roteiro de demonstração.

## 5. Documentação e evidência

`docs/ESTADO_IMPLEMENTACAO.md`, matriz de rastreabilidade e contratos descrevem o `HEAD_SHA`.
Evidência histórica mantém a data e o SHA de origem; não reescreva registros antigos.

## 6. Saída

```markdown
## Pós-merge: <BASE_SHA>..<HEAD_SHA>
PRs: …   CI no HEAD: …
### Achados   (mesmas severidades de archcorp-revisao)
### Interações entre PRs
### Fluxos F1–F3
### Documentação
Próximo passo: …
```

Achados viram novas tarefas (`archcorp-preparar-tarefa`); o pós-merge não corrige código.
