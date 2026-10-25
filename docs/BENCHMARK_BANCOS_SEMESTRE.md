# Benchmark de bancos para o semestre e aprendizado de backend

Data da pesquisa: 30/09/2026. Parecer consultivo, não uma decisão arquitetural aprovada. Nenhum código, infraestrutura, AGENT.md, CLAUDE.md ou ADR vigente foi alterado. Preços e ofertas refletem as páginas oficiais consultadas e devem ser conferidos antes da contratação.

## Recomendação

Para concluir este projeto, manter **FastAPI + PostgreSQL local no Docker**, usando **Supabase Free apenas se a demonstração precisar de banco hospedado**. O PostgreSQL já está previsto no ADR-001 e configurado no Compose; a baixa escala acadêmica não obriga uma troca de banco. A vantagem é concentrar o aprendizado em APIs, regras, transações e integração.

Para uma trajetória profissional centrada na Microsoft, **SQL Server Express é a alternativa relevante ao PostgreSQL**. É melhor alinhado a backend do que Access. Pode ser usado com a API Python existente; C#/ASP.NET Core é uma escolha posterior de linguagem/framework, não um requisito para adotar SQL Server. Migrar todo o backend neste semestre teria custo adicional que precisa ser justificado pelo objetivo pedagógico.

**Access faz sentido para um aplicativo departamental Windows, com formulários e relatórios locais, mas não é a melhor persistência para esta API web.** Ele pode comportar o volume de uma demonstração; o problema é o encaixe operacional e o retrabalho, não simplesmente capacidade.

## Evidências do projeto

Foram lidos AGENT.md, CLAUDE.md, README.md, Guia.pdf, plano de implementação, ADR-001, requisitos, AS-IS, TO-BE, TDD, estado da implementação e cronograma, além de configurações e trechos do código.

| Evidência | Consequência para a escolha |
|---|---|
| [Guia.pdf](../Guia.pdf), páginas 5 e 9: pelo menos três integrações e demonstração; páginas 7 e 8: evolução e viabilidade | Não impõe marca de banco, nuvem, data warehouse ou escala de produção. |
| [ADR-001](adr/ADR-001-integracao-empresa-de-servicos.md): monólito modular, PostgreSQL, REST e outbox/inbox | PostgreSQL é decisão aceita; substituí-lo exigiria novo ADR antes de implementar. |
| [Compose](../docker-compose.yml): PostgreSQL 16 com volume persistente; [requirements](../requirements.txt): FastAPI, SQLAlchemy e psycopg | O caminho local já está configurado; Access e SQL Server exigiriam trabalho adicional. |
| [Dockerfile](../Dockerfile): backend em imagem Linux Python | Access com o mecanismo Microsoft não se encaixa diretamente no ambiente atual. |
| [render.yaml](../render.yaml) e README: Render Free com DATABASE_URL externa | Supabase hospeda o PostgreSQL; não substitui a API própria. |
| [Estado da implementação](ESTADO_IMPLEMENTACAO.md), de 27/09/2026 | Publicação Render/Supabase, persistência remota e RLS no Supabase real ainda não foram comprovadas nesse registro. |
| [Modelos de integração](../src/archcorp/integration/models.py) e [serviço Contracts](../src/archcorp/contracts/service.py) | Há JSON, idempotência, auditoria e gravação de ativação/outbox na mesma transação. Troca de motor precisa preservar esses comportamentos. |
| [Migração de referência](../migrations/001_initial.sql) | Há schemas PostgreSQL no desenho; tabelas atuais usam prefixos para compatibilidade com SQLite. Não afirmar que schemas isolados já estão materializados em todo o runtime. |

O arquivo com o título específico “Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf”, citado pelo AGENT.md, não apareceu no inventário. A fonte acadêmica disponível e lida foi Guia.pdf. Não há comprovação de bancos, volumes ou tecnologias internos da Localiza. O contexto Microsoft no TCU é informação fornecida pelo usuário, sem inferência sobre contratos, licenças ou acesso institucional ao Azure.

## Banco, plataforma e data warehouse

PostgreSQL é o motor de banco. Supabase é uma plataforma que fornece PostgreSQL hospedado e recursos como APIs de dados, autenticação e arquivos. Portanto, escolher PostgreSQL e escolher Supabase são decisões em níveis diferentes. A aplicação pode usar PostgreSQL local, no Supabase ou em outro provedor. [Documentação Supabase](https://supabase.com/docs/guides/database/overview).

O trabalho atual é transacional: cadastrar, reservar, ativar, cobrar, abrir chamado e registrar eventos. Analytics aparece como evolução P2 no plano. Um data warehouse envolveria objetivos analíticos, histórico, modelagem e cargas próprios; não surge automaticamente por hospedar as tabelas no Supabase. Para indicadores simples no semestre, consultas, views ou uma pequena projeção de leitura podem bastar, preservando a propriedade dos dados dos módulos.

## Comparação de adequação

As classificações são julgamento qualitativo aplicado ao repositório, não resultados de testes de desempenho.

| Critério | Access | PostgreSQL local | Supabase Free com PostgreSQL | SQL Server Express |
|---|---|---|---|---|
| Volume provável de uma demo pequena | Pode atender | Pode atender | Pode atender dentro das quotas | Pode atender |
| Aproveitamento do projeto existente | Baixo | Alto | Alto; conexão remota pendente | Médio; migração necessária |
| Aprender API/backend próprio | Possível, com atrito de drivers e ambiente | Muito adequado | Muito adequado mantendo FastAPI | Muito adequado |
| Demo local sem internet | Favorável no Windows | Favorável | Depende de conexão remota | Favorável |
| Linux/Docker atual | Desfavorável com mecanismo Microsoft | Favorável | Favorável como banco remoto | Viável com drivers/configuração adicionais |
| Familiaridade Microsoft | Alta para Office | Parcial, integrado a ferramentas Microsoft | Acrescenta painel/provedor | Alta para banco de servidor |
| Operação | Arquivo, permissões e cópias | Backup e manutenção próprios | Parte gerenciada; quotas e pausas | Backup e manutenção próprios |
| Melhor uso neste contexto | Ferramenta auxiliar local, se necessária | Base principal recomendada | Hospedagem opcional para apresentação | Alternativa para aprofundar Microsoft |

## Prós, contras e dificuldades

### Microsoft Access

**Prós:** construtor visual, formulários, consultas e relatórios; útil para soluções departamentais e trabalho local. Pode aproveitar licença já disponível, desde que ela efetivamente inclua Access. O Runtime gratuito permite executar soluções, mas não equivale à licença de autoria. O produto é para PC. [Produto Access](https://www.microsoft.com/en-us/microsoft-365/access), [Runtime](https://support.microsoft.com/en-us/office/download-and-install-microsoft-365-access-runtime-185c5a32-8ba9-491e-ac76-91cbe3ea09c9).

**Contras:** arquivo de até 2 GB, descontados objetos do sistema; 255 usuários simultâneos é limite especificado, não garantia de boa vazão para 255 escritores. Não há benchmark que comprove capacidade prática deste projeto no Access. [Especificações oficiais](https://support.microsoft.com/en-us/office/access-specifications-0cf3c66f-9cf2-4e32-9568-98c1025bb47c).

**Dificuldades aqui:** instalar e compatibilizar mecanismo/ODBC e arquitetura 32/64 bits, substituir psycopg, adaptar SQL e tipos, revisar transações e concorrência, e mudar o ambiente de execução. SQLAlchemy lista um dialeto externo `sqlalchemy-access`; isso torna a integração possível, mas não prova compatibilidade com os modelos e testes existentes. A documentação do Runtime restringe seu uso como substituto de mecanismos de servidor em aplicações multiusuário/stateless. [Dialetos SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/), [restrições do Runtime](https://support.microsoft.com/en-us/office/download-and-install-microsoft-365-access-runtime-185c5a32-8ba9-491e-ac76-91cbe3ea09c9).

Não é correto dizer que Access não possui transações ou que não pode participar de uma API. A conclusão é que **o caminho suportado e reprodutível fica menos adequado à hospedagem e ao aprendizado pretendidos**. Um arquivo pequeno também não vira persistente só por estar dentro de um container.

### PostgreSQL local

**Prós:** sem taxa de licença do motor, banco cliente/servidor, transações, restrições e suporte a JSON; preserva a arquitetura vigente e reduz dependência de um provedor. É utilizável em Windows e Linux. [Licença PostgreSQL](https://www.postgresql.org/about/licence/), [visão geral](https://www.postgresql.org/about/).

**Contras:** exige operar o serviço e organizar backup, restauração, permissões e atualizações. Hospedagem pública pode custar, mesmo com licença gratuita. Um volume Docker local garante retenção entre reinícios conforme configuração, mas não é backup.

**Dificuldade no semestre:** baixa para manter a configuração existente; maior para publicar e operar por conta própria. A máquina disponível, armazenamento e carga real ainda precisam ser medidos. Não há um limite comercial de 500 MB inerente ao PostgreSQL: esse limite é do plano do Supabase.

### Supabase Free

**Prós:** evita administrar toda a infraestrutura do PostgreSQL remoto e permite continuar com a API FastAPI e SQLAlchemy. Não é necessário aprender SDKs, Edge Functions ou usar a API automática para hospedar o banco.

**Contras e custo:** a página consultada informa 500 MB de banco, 1 GB para arquivos, 5 GB de egress e 5 GB de cached egress, até dois projetos ativos e pausa após uma semana de inatividade. O Pro parte de US$ 25/mês; excedentes, projetos adicionais e recursos opcionais podem ampliar o total. O Free não inclui backup automático. [Planos oficiais](https://supabase.com/pricing).

**Dificuldades aqui:** configurar segredos, TLS, pool de conexões e permissões, aplicar/verificar estrutura e testar os três fluxos no PostgreSQL real. Quando a rede for somente IPv4, a documentação recomenda o pooler em modo sessão para backend persistente; copiar a conexão do painel e validar com psycopg. [Conexões Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

O limite de armazenamento sozinho não demonstra insuficiência. Dados sintéticos sem anexos podem caber, mas outbox, auditoria, índices e respostas idempotentes também ocupam espaço. Medir é melhor do que trocar preventivamente. Se o projeto crescer, é possível migrar o PostgreSQL e os dados para outro host; Auth/Storage/Functions específicos do Supabase, se adotados, ampliariam a migração.

### SQL Server Express e caminho Microsoft

**Prós:** motor de servidor gratuito com afinidade Microsoft e bom encaixe em APIs próprias. A versão Express 2025 admite 50 GB por banco, até um socket ou quatro cores e 1.410 MB de buffer pool; não inclui SQL Server Agent. Express 2022 tinha limite de 10 GB. [Edições SQL Server 2025](https://learn.microsoft.com/en-us/sql/sql-server/editions-and-components-of-sql-server-2025?view=sql-server-ver17).

**Contras:** limites de computação/memória, operação própria e configuração adicional; não é hospedagem cloud gratuita. Para o protótipo, esses limites parecem compatíveis com uma demo pequena, mas isso é avaliação sem carga medida.

**Dificuldades aqui:** adotar ODBC/pyodbc ou driver compatível, adaptar imagem/configurações, revisar migração SQL, JSON e consultas, e substituir a proteção RLS específica de PostgreSQL em `infrastructure/db.py`. Usar SQLAlchemy reduz o trabalho, mas não torna a troca automática. [Dialeto SQL Server](https://docs.sqlalchemy.org/en/20/dialects/mssql.html).

Azure SQL Database é a opção gerenciada relacionada, não simplesmente Express hospedado. Há oferta de até dez bancos por assinatura, com 32 GB de dados, 32 GB de backup e 100 mil vCore-segundos mensais por banco. Pode pausar ao atingir a quota; isso não cobre a hospedagem da API. Conta elegível e condições da oferta precisam ser verificadas. [Oferta Azure SQL](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-offer?view=azuresql).

## Seu contexto no TCU e o aprendizado

Faz sentido priorizar ferramentas reaproveitáveis no trabalho. Porém, familiaridade com Microsoft 365 não comprova acesso ao SQL Server, Azure ou .NET; é preciso distinguir as ferramentas que você efetivamente utiliza da marca do fornecedor. Não pressupor uso de recursos institucionais neste projeto.

Se sua atuação envolve Office e Power BI, PostgreSQL continua relevante: Microsoft oferece conector PostgreSQL em Power Query/Power BI e o serviço Azure Database for PostgreSQL. É possível preservar o motor atual e aproximar a nuvem/BI do ecossistema Microsoft. [Conector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql), [PostgreSQL no Azure](https://learn.microsoft.com/en-us/azure/postgresql/overview).

Se o objetivo profissional inclui desenvolver aplicações Microsoft, a trilha SQL Server + C#/ASP.NET Core tem alinhamento mais direto. Ainda assim, conceitos de HTTP, validação, autorização, SQL, transações, idempotência e testes aprendidos no FastAPI transferem para essa trilha. Access tende a concentrar o aprendizado em formulários e automação desktop, quando esses forem o meio principal de desenvolvimento. [Tutorial oficial ASP.NET Core API](https://learn.microsoft.com/en-us/aspnet/core/tutorials/first-web-api).

Para este semestre, praticar na API existente: explicar um endpoint completo; implementar ou revisar validação e erros; acompanhar uma transação com outbox; demonstrar repetição sem duplicidade; testar reinício e persistência; documentar o contrato. Se Microsoft tiver prioridade superior à preservação da entrega, fazer primeiro uma prova isolada FastAPI + SQL Server, com os três fluxos, antes de decidir uma migração por ADR.

## Escala, custo total e comprovação

Não existem medições suficientes para afirmar que qualquer opção já foi aprovada em carga, nem que os 500 MB serão excedidos. Esta pesquisa não executou os fluxos, migrou bancos ou publicou recursos.

Comparar custo total: licença + hospedagem + armazenamento/tráfego + tempo de migração + manutenção + risco para a apresentação. Access pode ter custo incremental baixo de licença e ainda custar mais em adaptação. PostgreSQL/Express locais não têm mensalidade de banco, mas consomem recursos da máquina. Supabase/Azure gratuitos continuam sujeitos a quotas.

Uma validação posterior proporcional pode usar uma carga sintética documentada, medir tamanho total incluindo índices/outbox/auditoria, latência p95 dos três fluxos, repetição idempotente e persistência após reinício. Isso seria benchmark experimental; este documento é comparação documental e arquitetural.

No cloud atual, Render Free hiberna após 15 minutos sem tráfego e possui filesystem efêmero; gravar Access ou SQLite ali não resolveria a persistência. Para apresentação, validar o banco remoto e preparar a demo antes do horário, mantendo o Compose local como alternativa. [Limites Render](https://render.com/docs/free).

**Escolha proposta para a entrega:** PostgreSQL local + FastAPI; Supabase Free opcional para publicação. **Escolha Microsoft para formação futura:** SQL Server Express, com Azure SQL se precisar de banco gerenciado e tiver acesso à oferta. **Access:** adotar somente se o objetivo mudar para ferramenta desktop/departamental ou houver necessidade concreta de integração com uma aplicação Access existente.

Fontes complementares verificadas e limites detalhados estão em [Pesquisa de fontes](PESQUISA_BANCOS_FONTES.md).
