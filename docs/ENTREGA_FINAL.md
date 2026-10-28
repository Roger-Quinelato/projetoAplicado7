# Documentação de entrega — ArchCorp, Cenário 4

Revisão: 28/10/2026. Base técnica: `main` no commit `f1669d7`.
Referência acadêmica: `Guia.pdf`, páginas 9–13.

Este índice reúne a documentação do produto para avaliação e continuidade por
outra equipe. Registros de execução, backlog e auditorias são material de apoio;
não compõem o texto do relatório técnico.

## Escopo da solução

O ArchCorp demonstra a integração dos cinco sistemas do Cenário 4 por meio de
um monólito modular: CRM, contratos, financeiro, atendimento e processos.
O contexto Integration mantém contratos de comunicação, outbox/inbox,
correlação e recuperação. O domínio é inspirado na locação de veículos;
produtos e processos internos reais da Localiza não foram levantados.

As integrações funcionam com dados sintéticos. O despachante chama os
consumidores internos; o RabbitMQ recebe uma cópia dos eventos. A interface
web e as APIs demonstram F1 (cliente → contrato), F2 (ativação → fatura e
preparação) e F3 (chamado → processo de resolução).

## Documentos exigidos pelo guia

| Exigência | Documento ou artefato entregue |
|---|---|
| Requisitos funcionais e não funcionais | [Requisitos](REQUISITOS.md), [PRD](PRD_LOCALIZA.md) |
| Arquitetura atual, atores e problemas | [AS-IS](arquitetura/AS_IS.md), diagrama `arquitetura/img/as_is.png` |
| Arquitetura proposta e componentes | [TO-BE](arquitetura/TO_BE.md), diagramas de componentes e implantação em `arquitetura/img/` |
| Integração e fluxos de comunicação | [Integrações](INTEGRACOES.md), [sequências F1–F3](arquitetura/FLUXOS_INTEGRACAO.md) |
| APIs e exemplos de requisição/resposta | [OpenAPI](api/openapi.yaml), [AsyncAPI](events/asyncapi.yaml), [exemplos](EXEMPLOS_API.md) |
| Justificativa dos padrões | [ADR-001](adr/ADR-001-integracao-empresa-de-servicos.md), demais [ADRs](adr/), [desenho técnico](TDD_LOCALIZA.md) |
| Sistemas corporativos e interoperabilidade | [Domínio](DDD_LOCALIZA.md), [dados sintéticos e IDs](DADOS_SINTETICOS.md), integrações |
| Pelo menos cinco atributos de qualidade | [Análise de qualidade](ATRIBUTOS_QUALIDADE.md): nove atributos |
| Escalabilidade, manutenção e evolução | [Estratégias](EVOLUCAO_MANUTENCAO.md) |
| Público, valor, benefícios e viabilidade | [Visão de negócio](VISAO_NEGOCIO.md) |
| Protótipo e código-fonte | `src/archcorp/`, `web/`, [execução](../README.md) |
| Três fluxos funcionando | [Roteiro de demonstração](ROTEIRO_DEMONSTRACAO.md), `scripts/demo_f1.py`, `demo_f2.py`, `demo_f3.py` |
| Relatório técnico em artigo, 15–20 páginas | [Relatório PDF, 20 páginas](../output/Relatorio_Tecnico_Cenario_4.pdf) e [DOCX editável](../output/Relatorio_Tecnico_Cenario_4.docx) |
| Apresentação técnica | [Slides](../output/Apresentacao_Cenario_4.pptx) |
| Continuidade por outra equipe | README, contratos, ADRs, [estado técnico](ESTADO_IMPLEMENTACAO.md), [rastreabilidade](MATRIZ_RASTREABILIDADE.md) |

## Estrutura do relatório

O relatório deve conter resumo; introdução com objetivos; fundamentação com
citações; metodologia com participantes, recursos e métodos; descrição e
análise dos resultados; considerações finais; referências. Diagramas e
resultados devem corresponder à versão demonstrada. O limite de 15–20 páginas
precisa ser conferido no PDF renderizado da versão a submeter.

## Operação e limites

A execução local está no README e o percurso da apresentação está no roteiro.
Autenticação é demonstrativa, por bearer token e papéis; não há OIDC. Há
correlação entre operações, mas não tracing distribuído. Despacho da outbox,
reconciliação e verificação de vencimentos exigem ação explícita.
Faturamento e pagamentos são simulados. Integração real, frota completa,
emissão fiscal, alta disponibilidade e escala horizontal são evoluções.

O guia permite demonstração local e sistemas simulados. A publicação
Render/Supabase é um compromisso adicional do plano do projeto e depende de
aceite verificável; não é comprovada apenas pela existência de `render.yaml`.

## Conferência antes da submissão

- Preencher e conferir os nomes e as contribuições dos participantes.
- Confirmar se o professor aceita as premissas do cenário e a demonstração local
  ou se mantém a publicação pública prevista no plano.
- Conferir relatório de 15–20 páginas, figuras legíveis, citações e referências.
- Usar o mesmo commit no código, no relatório, nos slides e na demonstração.
- Entregar pacote funcional e documentação em 09/11/2026; apresentar à turma
  em 23/11/2026, após ajustes do professor e ensaios.

O planejamento de fechamento e as pendências estão no
[panorama de prontidão](PANORAMA_PRONTIDAO.md), separado da documentação final.
