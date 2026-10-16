# Origem

Texto próprio do projeto ArchCorp (16/10/2026). Inspiração, sem cópia de texto: `deepwork` de [akitaonrails/my-skills](https://github.com/akitaonrails/my-skills) (repositório sem licença).

| Conceito de origem | Adaptação |
|---|---|
| Orquestrador como escalonador, não executor | Codex coordenador; não escreve código |
| `@fixer` | `archcorp-implementer` (Claude), um por fase |
| `@oracle` (portão por fase, 1 revisão + 2 re-revisões, contador de tentativa) | `archcorp-revisao` com o mesmo limite; ao esgotar, decisão humana |
| `@explorer` (varredura de estrutura) | `archcorp-fronteiras-e-dominio` + testes de arquitetura existentes |
| `@librarian` (pesquisa) | Pesquisa com fonte primária registrada antes do portão |
| `.slim/deepwork/<slug>.md` | `.agentes/deepwork/<slug>.md`, ignorado pelo Git |
| Guardrail do `@designer` | Removido: não há papel de designer neste projeto |
| Vários especialistas em paralelo | Um implementador por fase, sem escrita concorrente nos mesmos arquivos |
