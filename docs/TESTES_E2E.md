# Testes de interface (Playwright)

Estado em 17/10/2026, atualizado em 20/10/2026. Os roteiros exercitam a interface React/Vite (`web/`) contra a **API real** (FastAPI servindo `web/dist`), com dados sintéticos e tokens locais `demo-*`. Eles não tocam sistemas reais da Localiza.

## O que existe

| Arquivo | Cobertura | Reprova o job `e2e` |
|---|---|---|
| `web/e2e/f1.spec.ts` | F1 pela UI: cliente elegível → reserva → rascunho de contrato para o mesmo cliente | Sim |
| `web/e2e/acesso.spec.ts` | `demo-support` recebe a negativa ao cadastrar cliente; credencial inválida; "Sair" limpa a sessão | Sim |
| `web/e2e/navegacao.spec.ts` | Seis contextos por menu e por URL com hash; hash desconhecido volta à Visão geral | Sim |
| `web/e2e/selecao-e-ambiguidade.spec.ts` | #34: com mais de 200 clientes ativos, reserva para cliente fora da primeira página (paginação do seletor) e chamado para contrato da URL (cliente carregado pelo UUID); resposta perdida após a gravação, recusa de dados editados e repetição do pedido original com a mesma chave, resultando em um único registro | Sim |
| `web/e2e/papeis-e-feedback.spec.ts` | #61: cada papel `demo-*` usa seu contexto e vê a negativa `403` onde não tem permissão; despacho com falhas não é anunciado como sucesso; indicador de conexão (resposta, sem resposta, banco indisponível); edição de contato; cancelamento de fatura; contraste `color-contrast` sem violações com registros preenchidos nos seis contextos | Sim |
| `web/e2e/a11y.spec.ts` | Varredura axe (WCAG 2 A/AA) de cada contexto | Não: informativo |

O job `e2e` passou no GitHub Actions no PR #54 (run 39067995117, 17/10/2026). Em 20/10/2026, os nove roteiros bloqueantes e a varredura axe passaram localmente (Linux, Chromium 1194 pré-instalado indicado por `executablePath`); o resultado no GitHub Actions depende do PR correspondente. Ele só vira condição de merge se for configurado como check obrigatório na proteção da branch (não versionado aqui).

Fora do escopo desta versão: F2, F3 completo, cancelamento de reserva (`window.confirm`), ativação/encerramento de contrato e despacho da outbox pela UI.

## Rodar localmente

```
cd web
npm ci
npm run build              # a API serve web/dist
npx playwright install chromium
npm run test:e2e           # bloqueantes
npm run test:a11y          # informativo
```

- O roteiro sobe a própria API (`web/e2e/servidor.mjs`) na porta **8765**, com **SQLite temporário novo** a cada execução, sem RabbitMQ. A porta 8000 fica livre para o `docker compose up`.
- O Python vem de `.venv` na raiz; use `E2E_PYTHON` para indicar outro interpretador.
- Para testar uma API já em pé (por exemplo o Compose), defina `E2E_BASE_URL=http://127.0.0.1:8000`. Os cadastros ficam nesse banco e se acumulam; a tela de CRM lista 10 clientes por página, então dados antigos podem esconder os novos nessa tela.
- Relatório e traces de falha: `web/playwright-report/` e `web/test-results/` (não versionados).

## Playwright MCP (Claude Code / Codex)

Estado: configuração escrita e flags conferidas com `npx @playwright/mcp@0.0.83 --help`; **não foi executada em uma sessão do Claude Code/Codex**. `.mcp.json` registra o servidor `playwright` (`@playwright/mcp@0.0.83`, Chromium, headless, perfil isolado e navegação restrita a `127.0.0.1:8000` e `127.0.0.1:8765`). Com a API e o `web/dist` de pé:

1. Abra o Claude Code na raiz do repositório e aprove o servidor `playwright` quando for solicitado (`/mcp` lista o estado).
2. Peça, por exemplo: "abra `http://127.0.0.1:8000/#/crm`, entre com `demo-admin` e descreva a tela".

No Windows nativo, `npx` costuma exigir `cmd /c` para ser iniciado; se o servidor não conectar, troque `command`/`args` por `"command": "cmd"` e `"args": ["/c", "npx", "-y", "@playwright/mcp@0.0.83", ...]`.

Os tokens `demo-*` são públicos e locais; não coloque credenciais reais no `.mcp.json`.

## Limites conhecidos

- A prova de que a interface funciona vale para o ambiente de teste (SQLite local, sem broker). Não comprova a URL HTTPS pública, o PostgreSQL de produção, o RabbitMQ nem a persistência após reinício.
- O teste axe não tem asserção: ele anexa o resumo (`axe-resumo.json`) ao relatório e só falha por erro de execução. A última execução local reportou 0 violações A/AA, sem arquivo versionado desse resultado.
- A varredura axe cobre as telas no estado inicial (banco vazio, sem diálogos nem erros); não substitui auditoria formal de acessibilidade nem teste com leitor de tela.
- A UI não tem `data-testid`; os roteiros dependem de roles, labels e textos em português. Mudar um rótulo exige atualizar o roteiro.
