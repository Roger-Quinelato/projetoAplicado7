# Panorama de prontidão para entrega

Avaliação de 28/10/2026, base `f1669d7`. Prazos informados pelo responsável:
09/11/2026 para documentação e projeto demonstrável; 23/11/2026 para a
apresentação avaliada. Restam 12 e 26 dias corridos, respectivamente.

## Diagnóstico

O núcleo funcional está implementado. O maior trabalho restante é fechar e
comprovar a entrega: autoria, consistência dos artefatos, execução reproduzível,
ambiente de apresentação e aceite do professor. Não há base para um percentual
único: quantidade de arquivos, tarefas fechadas e testes aprovados não mede a
prontidão acadêmica.

### Lacunas técnicas reproduzidas nesta revisão

1. **Prioridade alta — recuperação do F3:** quando `TicketOpened.v1` falha e
   `TicketResolved.v1` é confirmado antes da recuperação, o processo criado
   depois pode permanecer `STARTED` mesmo com chamado `RESOLVED` e sem eventos
   pendentes. Corrigir e cobrir a inversão de processamento antes de 09/11.
2. **Cancelamento financeiro:** leitura pode mostrar `OVERDUE` enquanto o estado
   persistido ainda é `OPEN`; nesse intervalo, o comando aceita cancelamento.
   Definir a política e alinhar comando e exibição.
3. **Encerramento de contrato:** pode resultar em processo `COMPLETED` com tarefa
   `CANCELLED`, divergindo da regra geral do agregado. Definir a exceção ou
   corrigir o comportamento e a documentação em conjunto.

Esses achados foram reproduzidos apesar da suíte aprovada. Os caminhos de
sucesso F1/F2/F3 existem, mas a prontidão exige resolver ou aceitar explicitamente
os limites; os resultados dos testes não significam ausência de defeitos.

| Frente | Situação observada | O que falta para aceite |
|---|---|---|
| Cenário, requisitos, AS-IS e TO-BE | Documentos e diagramas existentes | Conferência docente das premissas; cenário é acadêmico |
| Padrões, integrações e APIs | ADRs, OpenAPI, AsyncAPI e exemplos existentes | Manter coerência com o commit demonstrado; ADR-006 ainda proposto |
| Três fluxos integrados | Código, interface e roteiros F1/F2/F3 existentes | Ensaio integral no notebook e ambiente da apresentação |
| Qualidade e evolução | Nove atributos e estratégias documentados | Distinguir resultados medidos de metas futuras |
| CI da versão-base | Run `40199072801`: 252 testes aprovados/14 ignorados no SQLite; 262/4 no PostgreSQL; 25 E2E e axe aprovado | Suítes sobrepostas; não equivale a aprovação docente ou teste de hospedagem |
| Relatório e slides | Artefatos existentes em revisão final | Nomes/contribuições e conferência da versão renderizada |
| Operação pública | Configuração prevista no repositório | HTTPS, health, escrita/leitura, migrações e persistência após reinício não comprovados |
| Entrega e apresentação | Datas definidas | Pacote fechado, cópia de contingência, revisão do professor e ensaios |

Evidência remota consultada:
[CI da main](https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/40199072801).
Evidências locais e históricas: [validação](EVIDENCIAS_VALIDACAO.md).

## Trabalho restante até 9 de novembro

| Prazo interno | Entrega | Critério de término |
|---|---|---|
| 28–30/10 | Documentação alinhada e autoria | Índice do guia completo; nomes/contribuições corretos |
| 29/10–02/11 | Correções e decisões técnicas | Recuperação do F3 corrigida; cancelamento financeiro e regra do agregado definidos e verificados |
| 31/10–02/11 | Ambiente de demonstração | Instalação documentada, banco sintético, F1/F2/F3 completos e contingência local |
| 03–04/11 | Publicação prevista ou decisão docente | Evidência de HTTPS/persistência, ou aceite explícito da demonstração local |
| 05–06/11 | Relatório e slides conferidos | Artigo de 15–20 páginas renderizado; figuras e referências conferidas; slides coerentes |
| 07–08/11 | Ensaio e congelamento | Fluxos repetidos sem falha, backup e pacote identificado por commit |
| 09/11 | Alinhamento com professor | Projeto funcionando e documentação completa; registrar apenas ajustes solicitados |
| 10–22/11 | Ajustes e ensaios | Tratar feedback, revisar pacote e repetir roteiro após alterações |
| 23/11 | Apresentação à turma | Demonstrar a mesma versão documentada e entregar os artefatos finais |

Estimativa de planejamento: 20–36 horas de trabalho para fechamento documental,
operação/ensaio e revisão; mais 8–16 horas se mantida a publicação no provedor,
conforme o pacote H (#64). Não são horas medidas nem promessa de prazo;
dependem de acesso às contas, autoria e defeitos encontrados no ensaio.

## Backlog consultado

Consulta às issues em 28/10/2026: #15–#22 (T12–T19) continuam abertas apesar da
integração técnica pelo PR #75. Estado da issue não substitui inspeção do código.
#23/#64 cobrem publicação, #22/#65 documentação e #25/#66 revisão e submissão.
#24 trata vínculos entre ferramentas; essa organização não substitui os
entregáveis do guia. #34 exige conferir os critérios residuais de interface.
#56 (Mercado Pago sandbox) é evolução fora do mínimo de três fluxos com
pagamento simulado; não deve bloquear a entrega sem novo requisito docente.

Jira não foi consultado ao vivo nesta revisão. Trello e Notion não foram
consultados. Nenhum ticket externo foi encerrado por inferência.

## Condição para declarar pronto

A declaração exige os três fluxos executados no ambiente escolhido, documentação
da versão final, relatório dentro do limite do guia, autoria preenchida,
artefatos revisados e aceite do professor sobre as premissas e o ambiente.
CI aprovado sustenta o código; não resolve sozinho as pendências de entrega.
