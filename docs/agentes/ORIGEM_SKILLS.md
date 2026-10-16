# Origem e licença das skills de referência do pacote `archcorp-*`

Data: 16/10/2026. Levantado por leitura do frontmatter (`license`, `metadata.author`), de arquivos `LICENSE*` nas pastas e de `~/.agents/.skill-lock.json` na máquina do responsável, e da licença declarada no GitHub de cada repositório de origem.

Este registro define **o que pode ser copiado** para as skills `archcorp-*` e **o que só pode inspirar** um texto novo. A tabela de consolidação está em [`LEVANTAMENTO_SKILLS.md`](LEVANTAMENTO_SKILLS.md); a lista permitida, em [`pacote-skills.json`](pacote-skills.json).

## Regras de uso

| Ação | Quando | Obrigação |
|---|---|---|
| **Copiar e adaptar** | Licença permissiva identificada (MIT, Apache-2.0, CC-BY-4.0) | Manter aviso de atribuição na pasta da skill (`ORIGEM.md`) com fonte, autor e licença; registrar a adaptação |
| **Reescrever** | Origem ou licença não identificada | Escrever texto próprio a partir das ideias; não colar trechos |
| **Só ideia** | Repositório sem licença (todos os direitos reservados) | Texto próprio; citar como inspiração |

## Skills de referência

| Skill | Fonte | Autor | Licença | Ação |
|---|---|---|---|---|
| `code-review` | [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock | MIT | Copiar e adaptar |
| `tdd` | mattpocock/skills | Matt Pocock | MIT | Copiar e adaptar |
| `diagnosing-bugs` | mattpocock/skills | Matt Pocock | MIT | Copiar e adaptar |
| `domain-modeling` | mattpocock/skills | Matt Pocock | MIT | Copiar e adaptar |
| `research` | mattpocock/skills | Matt Pocock | MIT | Referência por gatilho (não copiada) |
| `pr` | mattpocock/skills (nova; não instalada) | Matt Pocock | MIT | Copiar e adaptar |
| `surgical-patch` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `lean-build` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `safe-refactor` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `migration` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `investigate-first` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `verify-and-stop` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar |
| `caveman-review` | JuliusBrussee/caveman | Julius Brussee | Apache-2.0 | Copiar e adaptar (formato de achado) |
| `security-best-practices` | [openai/skills](https://github.com/openai/skills) | OpenAI | Apache-2.0 (`LICENSE.txt` na pasta) | Copiar e adaptar |
| `security-threat-model` | openai/skills | OpenAI | Apache-2.0 (`LICENSE.txt` na pasta) | Copiar e adaptar |
| `ddia-transactions-consensus` | Autoria própria, a partir de Kleppmann, *Designing Data-Intensive Applications* | Roger Quinelato | CC-BY-4.0 | Copiar e adaptar |
| `ddia-encoding-evolution` | Autoria própria, a partir de Kleppmann | Roger Quinelato | CC-BY-4.0 | Copiar e adaptar |
| `the-fool` | [Jeffallan](https://github.com/Jeffallan) | Jeffallan | CC-BY-4.0 | Copiar e adaptar |
| `create-adr` | [tech-leads-club](https://github.com/tech-leads-club) | Tech Leads Club | CC-BY-4.0 | Referência por gatilho |
| `modular-design-principles` | Não identificada | — | Não identificada | Reescrever |
| `tactical-ddd` | Não identificada | — | Não identificada | Reescrever |
| `component-common-domain-detection` | Não identificada | — | Não identificada | Reescrever |
| `coupling-analysis` | Não identificada (baseada em *Balancing Coupling in Software Design*) | — | Não identificada | Reescrever |
| `coding-guidelines` | Não identificada | "ale" | Não identificada | Reescrever |
| `docs-writer` | Não identificada | — | Não identificada | Reescrever |
| `pr-audit`, `github-resolution`, `verification-planning`, `iss-audit`, `pr-post-audit`, `security-audit`, `deepwork` | [akitaonrails/my-skills](https://github.com/akitaonrails/my-skills) | Fabio Akita | Nenhuma no repositório | Só ideia |
| `humanizer` | [blader/humanizer](https://github.com/blader/humanizer) | blader | MIT | Instalação de projeto, sem alteração |

## Limites deste levantamento

- A licença de `openai/skills` não aparece no nível do repositório no GitHub; vale o `LICENSE.txt` Apache-2.0 presente em cada pasta instalada.
- "Não identificada" significa que nem frontmatter, nem arquivo de licença, nem registro do CLI indicaram a origem; não significa domínio público.
