---
name: archcorp-prontidao-demo
description: Checklist do Guia.pdf e roteiro de prontidão da demonstração do ArchCorp. Use para avaliar se a entrega de 09/11 e a apresentação de 23/11 atendem ao que o professor vai cobrar, e para preparar o ambiente da demonstração.
---

# Prontidão da entrega e da demonstração

## 1. Checklist do Guia.pdf

Cada item precisa apontar para um arquivo concreto e coerente com o código.

| Item do Guia | Artefato esperado |
|---|---|
| Análise do cenário atual (AS-IS): sistemas, usuários, dados, comunicação, problemas | `docs/arquitetura/AS_IS.md` e `docs/arquitetura/img/as_is.png` |
| Requisitos funcionais e não funcionais, com os RNF prioritários explicados | `docs/REQUISITOS.md` e `docs/PRD_LOCALIZA.md` |
| Arquitetura proposta (TO-BE): componentes, sistemas, serviços, APIs, bancos, consumidores, comunicação, fluxo e fronteiras | `docs/arquitetura/TO_BE.md` e diagramas em `docs/arquitetura/img/` |
| Padrões e estilos, com por que são adequados, vantagens e limitações | `docs/adr/` (ADR-001 é a decisão central) |
| Três ou mais integrações: origem, destino, informação, objetivo, tipo, API, dados enviados e recebidos, tratamento de erros | `docs/INTEGRACOES.md` e `docs/arquitetura/FLUXOS_INTEGRACAO.md` |
| Sistemas corporativos: função, processos, dados, integrações, papel | `docs/DDD_LOCALIZA.md` e `docs/arquitetura/TO_BE.md` |
| Interoperabilidade, com um exemplo de problema e a solução | IDs legados e UUID global (`docs/DADOS_SINTETICOS.md`, `docs/INTEGRACOES.md`) |
| Cinco ou mais atributos de qualidade, com necessidade, risco, estratégia e resultado | `docs/ATRIBUTOS_QUALIDADE.md` |
| Escalabilidade, manutenção e evolução (7 perguntas) | `docs/EVOLUCAO_MANUTENCAO.md` |
| Empreendedorismo: público, problema, valor, benefícios, viabilidade | `docs/VISAO_NEGOCIO.md` |
| Apresentação técnica (13 tópicos) | `output/Apresentacao_Cenario_4.pptx` |
| Demonstração de três ou mais fluxos integrados | `docs/ROTEIRO_DEMONSTRACAO.md`, `scripts/demo_f1.py`, `demo_f2.py` e `demo_f3.py` |
| Documentação: exemplos de requisição e resposta, documentação das APIs | `docs/EXEMPLOS_API.md`, `docs/api/openapi.yaml` e `docs/events/asyncapi.yaml` |
| Relatório técnico em artigo, de 15 a 20 páginas, com citações e referências | `output/Relatorio_Tecnico_Cenario_4.pdf` (gerado por `tools/build_report.py`) |
| Continuidade por outra equipe | README, ADRs, `docs/ESTADO_IMPLEMENTACAO.md` e `docs/MATRIZ_RASTREABILIDADE.md` |

## 2. Ambiente da demonstração (local, sem Docker)

A demonstração oficial é local (ADR-007). A API serve a interface compilada a partir de `web/dist` (`src/archcorp/main.py`).

```powershell
cd web; npm run build; cd ..
$env:PYTHONPATH = "src"
$env:DATABASE_URL = "sqlite:///./tmp/demo.db"
./.venv/Scripts/python -m uvicorn archcorp.main:app --port 8000
```

- `RABBITMQ_URL` fica vazio: a cópia dos eventos no broker é opcional.
- Entre em `http://localhost:8000` com o token `demo-admin`.
- Dados sintéticos: `./.venv/Scripts/python scripts/seed_sintetico.py --base-url http://localhost:8000 --token demo-admin`.
- `scripts/demo.ps1` usa e-mail e ID legado fixos e devolve `409` se rodar duas vezes na mesma base. Use uma base nova ou prefira os roteiros `demo_f1.py`, `demo_f2.py` e `demo_f3.py`, que podem ser repetidos.
- Para mostrar a indisponibilidade de Contracts, reinicie com `CONTRACT_ADAPTER_AVAILABLE=false`.

## 3. Checagem antes da demonstração

1. `GET /health/ready` responde `UP`.
2. O token `demo-admin` é aceito.
3. A base está nova ou semeada com dados sintéticos.
4. `demo_f1.py`, `demo_f2.py` e `demo_f3.py` saem com `0`.
5. O commit demonstrado é o mesmo citado no relatório e nos slides.
6. A contingência está em `output/demo/`: capturas ou gravação dos três fluxos e o roteiro de 10 minutos.
7. Recomendação de segurança: BitLocker ativo no notebook da apresentação. Os dados são sintéticos; é uma boa prática, não um requisito do Guia.

## 4. Riscos a observar

- Prazos: 09/11/2026 (entrega e alinhamento) e 23/11/2026 (apresentação).
- O gerador de slides depende de `@oai/artifact-tool`, fora do repositório.
- A exportação do DOCX para PDF é manual.
- Premissas de negócio a validar com o professor: vencimento em 10 dias, preparação em 72 h, prazo provisório de 24 h.
