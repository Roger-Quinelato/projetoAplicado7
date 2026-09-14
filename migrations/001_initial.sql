-- Migração de referência. A aplicação cria a mesma estrutura por metadados SQLAlchemy.
-- Em produção acadêmica, execute a aplicação com um usuário de migração antes de restringir permissões.
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS contracts;
CREATE SCHEMA IF NOT EXISTS finance;
CREATE SCHEMA IF NOT EXISTS support;
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS integration;

-- As tabelas físicas usam prefixos de contexto para manter o protótipo compatível
-- com SQLite nos testes. A estratégia de produção mapeia cada prefixo ao schema
-- PostgreSQL correspondente, sem conceder leitura cruzada aos módulos.
