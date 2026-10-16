---
name: archcorp-documentacao
description: >
  Use ao escrever ou revisar documentação do ArchCorp (docs/, README, ADR, matriz de
  rastreabilidade, ESTADO_IMPLEMENTACAO, relatório e slides em output/): classifica cada afirmação,
  liga evidência a data e SHA e evita contradição com o código. Não use para comentários de código.
---

# Documentação no ArchCorp

Documento acadêmico que afirma capacidade inexistente é o defeito de maior impacto na entrega
(caso real em [`references/historico.md`](references/historico.md)). O oposto também é defeito:
capacidade **comprovada** deve ser afirmada com clareza, com a evidência, sem ressalvas vagas que a
façam parecer hipotética. Cada frase sobre o sistema precisa caber numa destas categorias, e o
texto deve deixar claro qual é:

| Categoria | Como escrever | Exemplo |
|---|---|---|
| **Implementado e verificado** | Afirmação + evidência (teste, comando, data, SHA) | "Verificado em 16/10/2026 por `test_…` no SHA `abc1234`" |
| **Decisão aprovada** | Afirmação + ADR | "Conforme ADR-003…" |
| **Meta arquitetural** | Verbo de intenção, sem afirmar existência | "A arquitetura prevê OIDC; não implementado" |
| **Premissa a validar** | Marcada como premissa, com quem valida | "Prazo de 10 dias: premissa a validar com o docente" |

Nunca descreva o protótipo como integrado a sistemas reais da Localiza, nem OIDC/OAuth, tracing
distribuído, fila de erro no broker, escala horizontal ou deploy público como existentes **enquanto
não houver evidência verificável** (`AGENTS.md`, regras NUNCA). Quando uma dessas capacidades for
implementada e verificada, ela passa à primeira categoria, com a evidência e a atualização de
`docs/ESTADO_IMPLEMENTACAO.md` na mesma mudança.

## 1. Fonte única de cada fato

- Estado do sistema: `docs/ESTADO_IMPLEMENTACAO.md`. Outros documentos apontam para ele em vez de
  repetir números que envelhecem.
- Decisões: `docs/adr/`. Não reescreva ADR aceito; crie outro.
- Demandas e prazos: `docs/CRONOGRAMA_EXECUCAO.md`.
- Contratos: OpenAPI gerado e AsyncAPI (`archcorp-contratos-e-migracoes`).

Ao mudar comportamento, atualize essas fontes **na mesma mudança**.

## 2. Evidência datada

- Contagem de testes, desempenho e resultados de CI levam data, ambiente e SHA. Não some contagens
  de jobs que se sobrepõem.
- Evidência histórica (ex.: `output/auditoria/2026-10-01T2035Z/`) fica como está, com a data
  original. Corrija afirmações atuais, não registros antigos.
- "Não executado" e "não verificado" são escritos explicitamente.

## 3. Entregáveis acadêmicos (`output/`)

- Relatório (DOCX) e slides (PPTX) são gerados por `tools/build_report.py` e
  `tools/build_presentation.mjs`; confira as afirmações na fonte antes de regenerar, e inspecione o
  arquivo renderizado (páginas, figuras, equipe e contribuições), não só o texto.
- Conferir contra o Guia (`Guia.pdf`): requisitos, três fluxos integrados, referências.
- Prosa com cara de texto gerado: ver seção 4.

## 4. Acabamento opcional com `humanizer`

A skill externa `humanizer` (instalada no projeto, `skills-lock.json`) é acabamento, **depois** da
conferência factual, nunca antes:

1. Confira as afirmações (seções 1–2) e guarde a versão conferida.
2. Chame a `humanizer` em **modo incorporado** (*Embedded mode*: devolve só o texto final). Em
   arquivo, só prosa muda; código, comandos, caminhos, YAML e links ficam intactos.
3. Compare com a versão conferida: fatos, números, datas, SHAs, ressalvas ("não implementado",
   "não verificado", "premissa") e referências precisam continuar presentes e iguais. Ressalva
   perdida é defeito; reponha-a.

Sem a skill instalada, o texto conferido segue como está; a ausência não bloqueia a entrega.

## 5. Estilo

Português do Brasil; identificadores, endpoints e campos em inglês como no código. Frases diretas,
sem adjetivos promocionais. Links relativos válidos. Tabelas para comparações; listas curtas para
passos.

## 6. Revisão de documento (checklist)

- [ ] Cada afirmação sobre o sistema tem categoria clara e, se implementada, evidência datada.
- [ ] Capacidade comprovada aparece como implementada, sem ressalva vaga.
- [ ] Nenhuma capacidade da lista NUNCA aparece como existente.
- [ ] Números e estados não contradizem `ESTADO_IMPLEMENTACAO.md` nem o código no SHA.
- [ ] Links e caminhos citados existem.
- [ ] Registros históricos não foram reescritos.
