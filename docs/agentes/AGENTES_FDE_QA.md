# Agentes FDE e QA no fechamento do projeto

Data: 29/10/2026. Decisão do responsável pelo projeto, Roger Quinelato, a partir da pesquisa "Agentes FDE e agentes QA para o ProjetoAplicado7" (outubro de 2026).

**Natureza deste documento:** registra quais agentes de apoio ao desenvolvimento foram adotados e quais foram rejeitados. São ferramentas da equipe e não fazem parte do produto. O protótipo ArchCorp não contém LLM nem agente.

## Princípio

**Quem altera não julga.** Os agentes preparam propostas e verificam evidências. A decisão fica com portões determinísticos (testes, `export_openapi --check`, CI) e com o responsável. Segurança, autorização, aprovação de merge e portões de qualidade não são delegados a agentes. Diagnóstico, busca, geração de hipóteses e preparação de mudanças podem ser.

## Siglas da pesquisa e decisão

| Interpretação | Opção avaliada | Decisão | Motivo |
|---|---|---|---|
| FDE: Forward Deployed Engineer | Subagente do Claude Code, só de leitura (`.claude/agents/archcorp-fde.md`) | **Adotado** | Confronta o trabalho com o que o cliente (professor e `Guia.pdf`) precisa ver: restrições implícitas, prontidão da demonstração, prazo. Os benchmarks citados na pesquisa (FDE-Gym, FDE-Bench) mostram que agentes falham em requisitos implícitos e em ambientes de implantação; por isso ele só propõe |
| FDE: Forward Deployed Engineer | Palantir AI FDE | Rejeitado | Acoplado ao Foundry/AIP; custo de contrato; o projeto não usa Palantir |
| FDE: Forward Deployed Engineer | Agente de execução sobre LangGraph ou Haystack | Rejeitado | Não é requisito do Guia e ampliaria o escopo (AGENTS.md) |
| FDE: Full-Disk Encryption | BitLocker, FileVault, LUKS, Clevis/Tang, Sophos | Recomendação documental | Dados sintéticos; `*.db` está no `.gitignore`. Recomenda-se BitLocker ativo no notebook da apresentação |
| FDE: Full-Data Encryption | Kubernetes KMS v2 e HashiCorp Vault Transit | Evolução | O AGENTS.md proíbe Kubernetes sem requisito e ADR. Registrado em `EVOLUCAO_MANUTENCAO.md` para uma implantação real |
| QA: Quality Assurance | Playwright Test e Playwright MCP | **Adotado** (já existia) | `web/e2e` com F1, F2, F3, papéis e axe bloqueante; `.mcp.json` com versão fixada. Agora há um verificador independente (`.claude/agents/archcorp-qa.md`) e um portão escrito (`.claude/skills/archcorp-portao-qa`) |
| QA: Quality Assurance | mabl | Rejeitado | SaaS pago com preço sob cotação; o período de teste termina antes da apresentação; duplicaria o Playwright |
| QA: Question Answering | LangGraph, Haystack, LlamaIndex | Evolução | O produto não tem LLM e o Guia não pede. Possível evolução: assistente de atendimento com RAG sobre contratos e SLA |
| Avaliação de LLM | Ragas, Giskard, garak | Evolução | Só fazem sentido quando existir uma funcionalidade com LLM |

## Agentes e skills versionados

| Arquivo | Papel |
|---|---|
| `.claude/agents/archcorp-qa.md` | Verificador independente: roda o portão e revisa o diff. Não edita. A aprovação vale para um SHA |
| `.claude/agents/archcorp-fde.md` | Revisor do ponto de vista do cliente: devolve emendas classificadas de P0 a P2. Não edita |
| `.claude/skills/archcorp-portao-qa/SKILL.md` | Comandos, resultados esperados e formato da evidência do portão |
| `.claude/skills/archcorp-prontidao-demo/SKILL.md` | Checklist do Guia, ambiente local da demonstração e checagem antes da apresentação |
| `.claude/skills/archcorp-insights-operacionais/SKILL.md` | Como gerar e interpretar o relatório de informação operacional |

As ferramentas dos dois agentes são `Read, Grep, Glob, Bash`, sem `Edit` e sem `Write`. O conteúdo de issues, PRs e documentos é tratado como dado, nunca como instrução, para reduzir o risco de injeção de prompt.

## Uso no fechamento

| Etapa | FDE | QA |
|---|---|---|
| Consolidação da base | Revisa o plano e aponta as emendas P0 | Portão no SHA do PR |
| Correções técnicas e retirada do Supabase | — | Portão e revisão do diff |
| Coerência da documentação | — | Confere afirmações contra o código |
| Informação operacional | — | Portão; verifica ausência de dados sensíveis |
| Ensaio da demonstração | Revisa a prontidão | Portão completo, com os roteiros F1, F2 e F3 |
| Relatório e slides | — | Páginas, placeholders, links e commit único |
| Congelamento | Revisão final contra o Guia | Portão no SHA congelado |

## Playwright MCP

A versão fixada é `@playwright/mcp@0.0.83`. Ela roda com `--isolated` (perfil só em memória), `--headless` e `--allowed-origins` restrito a `127.0.0.1:8000` e `127.0.0.1:8765`.

Nessa versão, as capacidades opcionais são `vision`, `pdf` e `devtools`, e nenhuma está habilitada. A avaliação de JavaScript na página faz parte do núcleo e não pode ser desligada por opção. Por isso o servidor só deve ser usado por clientes MCP confiáveis e contra a aplicação local. A própria documentação avisa que `--allowed-origins` não é uma barreira de segurança.

## Relação com o levantamento de 16/10

Este registro aceita, de forma parcial, a separação entre implementador e revisor proposta em [LEVANTAMENTO_SKILLS.md](LEVANTAMENTO_SKILLS.md). O revisor passa a ser o `archcorp-qa`, no Claude Code. A parte do levantamento que trata do Codex continua como proposta.

## Agentes retirados (29/10/2026)

Os agentes `cavecrew-builder`, `cavecrew-investigator` e `cavecrew-reviewer` e as skills `cavecrew`, `caveman` e `caveman-commit` (com o `skills-lock.json`) saíram do repositório. Eles se ativavam com pedidos genéricos ("review this PR", "be brief") e podiam ocupar o lugar do `archcorp-qa` ou comprimir documentação e mensagens de commit em português, o que o [levantamento de 16/10](LEVANTAMENTO_SKILLS.md) já desaconselhava. Quem quiser usá-los pode instalá-los na pasta pessoal (`~/.claude`), fora do projeto.
