# ai-memory (memória de longo prazo para o Claude Code)

Esta pasta contém a configuração para rodar o [ai-memory](https://github.com/akitaonrails/ai-memory), de Fabio Akita, junto com o desenvolvimento do Projeto Aplicado 7. Ele registra o que o agente faz em cada sessão, consolida em páginas Markdown e entrega um resumo ("handoff") na sessão seguinte, inclusive ao trocar de agente (Claude Code, Codex etc.).

> **Escopo.** É ferramenta de apoio ao desenvolvimento. Não faz parte da arquitetura do protótipo (CRM, contratos, financeiro, suporte, workflow, integração) e não substitui `docs/ESTADO_IMPLEMENTACAO.md`. Não há evidência neste repositório de que a instalação tenha sido executada: o primeiro uso deve ser validado conforme a seção "Verificação".

## Arquivos

| Arquivo | Função |
|---|---|
| `docker-compose.yml` | Sobe o servidor ai-memory em `127.0.0.1:49374`, com volume Docker `ai-memory-data`. |
| `instalar-windows.ps1` | Windows nativo (Docker Desktop): instala o wrapper, sobe o servidor e conecta o Claude Code. Suporte experimental. |
| `instalar-wsl.sh` | WSL2, Linux ou macOS: faz o mesmo. Caminho recomendado para o Claude Code. |

Os dois scripts seguem a documentação oficial (`docs/windows.md` do projeto) e verificam o checksum do wrapper.

## Uso

Com o Docker Desktop em execução, a partir desta pasta:

```powershell
# Windows nativo (PowerShell)
.\instalar-windows.ps1
```

```bash
# WSL2 / Linux / macOS
bash instalar-wsl.sh
```

No WSL2, inicie o Claude Code de dentro do WSL2. Depois de instalar, reinicie o Claude Code.

## Verificação

1. `ai-memory status` responde sem erro.
2. No Claude Code, peça para executar a ferramenta `memory_status`.
3. Trabalhe uma sessão curta, encerre e abra outra no mesmo diretório; pergunte "onde paramos?".
4. Opcional: interface web somente leitura, se o servidor for iniciado com `--enable-web` (as páginas podem aparecer vazias no início, o que não significa falha de captura).

## Segurança e privacidade

- O servidor escuta apenas em loopback e sem autenticação; não exponha a porta na rede sem token (veja `docs/security.md` no projeto upstream).
- Os hooks gravam prompts e chamadas de ferramenta, com sanitização. Respeite as regras de `AGENTS.md`: não digite segredos, tokens, dados pessoais reais nem conteúdo sensível de chamados em sessões do agente.
- Não coloque chaves de API neste diretório nem no Git. Sem chaves, o ai-memory funciona sem chamadas a LLM (busca full-text); provedores de LLM e de embeddings são opcionais.
- Os dados ficam no volume `ai-memory-data`, fora do repositório.

## Manutenção

- Após atualizar a imagem ou o wrapper, rode de novo `ai-memory install-hooks --agent claude-code --apply`.
- Para remover o que foi instalado: `ai-memory uninstall --apply`; depois `docker compose down` (acrescente `-v` apenas se quiser apagar a memória).
- Windows nativo: não inicie o servidor por Tarefa Agendada nem registre o executável como serviço; o container já é o servidor.
