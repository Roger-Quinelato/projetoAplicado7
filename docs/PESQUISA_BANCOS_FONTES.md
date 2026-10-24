# Fontes do benchmark de bancos de dados

Consulta em **30/09/2026**. Pesquisa documental em fontes oficiais; não é um teste de desempenho e não mede a carga deste projeto. Preços, cotas e ofertas podem mudar. Esta nota não aprova migração nem altera o ADR, AGENT.md ou CLAUDE.md.

## Microsoft Access

- Arquivo `.accdb`/`.mdb`: até **2 GB**, descontados objetos de sistema; especificação de até **255 usuários concorrentes**. Esse teto não garante desempenho com 255 usuários nem representa uma recomendação de dimensionamento. [Especificações oficiais](https://support.microsoft.com/en-us/access/access-specifications).
- O Access Runtime é gratuito e instala mecanismos ODBC/OLE DB, mas remove/desabilita recursos de desenho. A própria Microsoft diz que o Access Database Engine não se destina a programas de servidor com múltiplas identidades, reentrância ou comportamento sem estado; cita aplicações web como exemplo e indica SQL Server Express como substituto geral do Jet. Há requisitos de compatibilidade com versões e arquitetura do Office. [Runtime e restrições oficiais](https://support.microsoft.com/en-us/access/download-and-install-microsoft-365-access-runtime).
- A licença de autoria do Access é diferente do Runtime e deve ser confirmada no plano pessoal/institucional do usuário; trabalhar no TCU não comprova direito de uso em projeto acadêmico pessoal. O produto vendido é para PC. [Loja Microsoft](https://www.microsoft.com/pt-br/microsoft-365/p/access/CFQ7TTC0PD0B).
- Há dialeto externo `sqlalchemy-access` via `pyodbc`, listado pela documentação SQLAlchemy; PostgreSQL e SQL Server têm dialetos incluídos. Portanto, conexão Python/ORM com Access existe, mas isso não resolve suas restrições de cenário de servidor. [Dialetos SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/).
- **Interpretação:** Access pode ser adequado a cadastros desktop, consultas e relatórios locais de poucos operadores. Para uma API web em Linux/contêiner, tentar aproveitar sua familiaridade com Office introduziria uma dependência e um modelo de implantação inadequados ao mecanismo oficial. Seu limite de armazenamento maior que o Supabase Free não elimina essa diferença. Não afirmar que Access não tem transações ou que é impossível acessá-lo por código: há conectividade oficial, com restrições de cenário.

## PostgreSQL instalado localmente

- Licença permissiva, sem cobrança de licença do banco; gastos com máquina, hospedagem, operação e backup são separados. [Licença PostgreSQL](https://www.postgresql.org/about/licence/).
- Suporta Windows e Linux, entre outras plataformas. [Plataformas PostgreSQL](https://www.postgresql.org/docs/18/supported-platforms.html).
- MVCC mantém snapshots e isolamento de transações e reduz conflito entre leitura e escrita. Isso não elimina a necessidade de projetar corretamente concorrência e retentativas. [Controle de concorrência](https://www.postgresql.org/docs/current/mvcc-intro.html).
- **Interpretação:** permite aprender SQL, conexões, transações, migrações e a API escrita no backend sem cotas comerciais de SaaS. Em uso local acadêmico, não precisa de outra plataforma cloud. Publicá-lo por conta própria exige administrar persistência, acesso, atualizações e backups. Usar Docker com volume persistente é uma opção de implantação, não um serviço gerenciado gratuito.

## Supabase hospedado

- Cada projeto tem um banco **PostgreSQL completo**; Supabase não é outro motor concorrente ao PostgreSQL. [Visão do Database](https://supabase.com/docs/guides/database/overview).
- Free: **US$ 0/mês**, **500 MB de banco por projeto**, **1 GB de arquivos**, **5 GB de egress** e **5 GB de egress em cache**, **2 projetos ativos**, pausa depois de **1 semana de inatividade**; backups automáticos não incluídos. Requisições de API ilimitadas não significam computação ou capacidade ilimitadas. Pro começa em **US$ 25/mês**; inclui crédito de US$ 10 de computação que cobre uma instância Micro; projetos/computação extra e excedentes podem aumentar a conta. [Preços oficiais](https://supabase.com/pricing).
- A conexão direta Free usa IPv6; o pooler compartilhado oferece IPv4 em modos de sessão e transação. Sessão é uma opção para backend persistente sem IPv6. Conferir compatibilidade do driver/uso de prepared statements ao escolher o modo de transação. [Conexões oficiais](https://supabase.com/docs/guides/database/connecting-to-postgres).
- O changelog foi obtido em [índice Markdown](https://supabase.com/changelog.md) e conferido: [mudança PostgreSQL 15.19/17.11](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes) em 25/09/2026 pode demandar manutenção de extensões/índices em projetos existentes; não demonstra que esse projeto utiliza extensões afetadas. [Logs por uso](https://supabase.com/changelog/logs-usage-based-pricing), também em 25/09/2026, anuncia medição de ingestão/consulta, com carência até início de 2027; não tratar como cobrança já aplicada naquela data.
- **Interpretação:** é hospedagem PostgreSQL com serviços adicionais e pode ser usado apenas como banco da API própria. Esse caminho preserva o aprendizado de backend e reduz administração cloud. API automática e serviços próprios acrescentam conceitos se utilizados, mas não são obrigatórios. É inadequado descrevê-lo simplesmente como um data warehouse: armazenamento analítico depende do modelo, das consultas e do processo de alimentação, enquanto o serviço também atende dados transacionais.

## Alternativa Microsoft: SQL Server Express

- SQL Server **2025 Express** é edição gratuita para aplicações pequenas. Limites: **50 GB por banco relacional**, menor de **1 socket ou 4 cores**, **1.410 MB para buffer pool**; sem SQL Server Agent. Não confundir buffer pool com teto de memória total do processo. [Edições e recursos](https://learn.microsoft.com/en-us/sql/sql-server/editions-and-components-of-sql-server-2025?view=sql-server-ver17). O valor antigo de 10 GB se refere a versões anteriores, não à edição 2025.
- SQL Server 2025 tem suporte a Linux/contêiner; **2 GB de memória** é o mínimo de inicialização Linux. A licença gratuita do Express não inclui um serviço cloud gratuito ou dispensa persistência/backup. [Instalação Linux oficial](https://learn.microsoft.com/en-us/sql/linux/install-upgrade/setup?view=sql-server-ver17).
- **Interpretação:** é candidato mais alinhado a banco servidor/API dentro da Microsoft que o Access. Pode atender backend Python ou .NET; mudar de banco não exige automaticamente reescrever o backend em C#. No projeto existente, exige conferir dialeto SQL, driver, DDL, transações, migrações e recursos específicos de PostgreSQL, além de rever decisões arquiteturais antes da implementação. ASP.NET Core + SQL Server é um caminho de formação Microsoft, mas reescrever o semestre inteiro para isso seria outra decisão.

## PostgreSQL também existe no ecossistema Microsoft

- Azure Database for PostgreSQL é um serviço gerenciado Microsoft, com backups, opções de rede e computação; preço depende de recursos/região/oferta. [Visão do serviço](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/overview), [preços Azure](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/).
- **Interpretação:** escolher PostgreSQL não obriga a abandonar Azure/Microsoft. Aprender um motor de banco e adotar um provedor cloud são escolhas relacionadas, mas separadas. Não supor que a infraestrutura, licenças, créditos ou tecnologias específicas do TCU estejam disponíveis ao aluno; validar apenas se necessário.

## Critérios para a síntese arquitetural

Comparar custo de licença e hospedagem separadamente; API própria versus formulários desktop; esforço de mudança no código existente; manutenção e demonstração pública; formação backend e afinidade profissional com Microsoft. Sem volume e concorrência medidos, não declarar que o Free será insuficiente nem que os limites nominais garantem toda a carga. Relatório analítico simples pode usar SQL e visualização sobre banco transacional; um data warehouse separado só se justifica por requisito específico.
