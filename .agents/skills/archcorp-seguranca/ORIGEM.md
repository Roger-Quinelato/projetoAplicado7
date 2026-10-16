# Origem

- Adaptado de `security-best-practices` e `security-threat-model`, de [openai/skills](https://github.com/openai/skills), licença [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) (arquivo `LICENSE.txt` nas pastas de origem). Da primeira veio a orientação de revisão segura por padrão para Python/TypeScript; da segunda, a sequência ativo → alcance → abuso → mitigação. O texto foi reescrito e reduzido à superfície deste repositório.
- Inspiração, sem cópia de texto: `security-audit` e a seção *Trust Boundary* de `pr-audit`, de [akitaonrails/my-skills](https://github.com/akitaonrails/my-skills) (repositório sem licença).
- Licença: [`docs/agentes/licencas/APACHE-2.0-openai-skills.txt`](../../../docs/agentes/licencas/APACHE-2.0-openai-skills.txt).
- Conteúdo específico: `src/archcorp/security.py`, `main.py`, `infrastructure/db.py`, `support/domain.py` e achado Q-11 da auditoria de 16/10/2026.
