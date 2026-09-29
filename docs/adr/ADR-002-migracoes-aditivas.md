# ADR-002 - Migrações de banco versionadas e aditivas com Alembic

- Status: Aceito para o protótipo acadêmico
- Data: 2026-09-29
- Decisores: equipe do Projeto Aplicado
- Tarefa: T07 (ARCH7-7) - dados sintéticos, identificadores globais, migração aditiva e contrato de erro
- Relaciona-se com: [ADR-001](ADR-001-integracao-empresa-de-servicos.md)

## Contexto

Até esta decisão, a aplicação criava as tabelas com `Base.metadata.create_all` na
inicialização. Esse comando cria somente tabelas ausentes e nunca altera uma tabela
existente. Em um PostgreSQL persistente, como o previsto em `render.yaml` e no
`docker-compose.yml`, uma coluna nova nos modelos não chegaria ao banco e a
aplicação falharia em tempo de execução. O arquivo `migrations/001_initial.sql`
apenas criava schemas vazios e não era usado por nenhum processo.

O `AGENT.md` exige migrações reproduzíveis e com estratégia de compatibilidade.
T08 e T09 acrescentam colunas a tabelas existentes, o que torna o problema
imediato.

## Decisão

1. Usar Alembic para versionar o esquema. Os scripts ficam em
   `src/archcorp/infrastructure/migrations/`, dentro do pacote, para entrar na
   imagem Docker sem mudar o `Dockerfile`.
2. A revisão `0001_baseline` reproduz as tabelas existentes na data da decisão.
3. A inicialização da aplicação executa `upgrade head` em qualquer banco
   (`src/archcorp/infrastructure/migrate.py`). Um banco criado antes desta decisão,
   com as tabelas do protótipo e sem a tabela `alembic_version`, recebe o carimbo
   da revisão base antes do upgrade, sem recriar tabelas.
4. Toda migração de `upgrade` é aditiva dentro da versão 1 da API:
   - permitido: criar tabela, criar coluna anulável ou com valor padrão, criar
     índice, criar restrição que os dados atuais já cumprem;
   - proibido: remover ou renomear tabela ou coluna, mudar tipo de forma
     incompatível, tornar obrigatória uma coluna existente sem valor padrão.
5. Mudanças destrutivas seguem expandir e contrair: primeiro uma versão adiciona a
   estrutura nova e mantém a antiga; a remoção ocorre em uma versão posterior,
   depois que nenhum leitor depende da estrutura antiga, com novo ADR.
6. Cada migração tem `downgrade` para desfazer a própria mudança.
7. Em SQLite as migrações usam `render_as_batch`, porque o SQLite não altera
   colunas diretamente.

## Verificação

`tests/test_foundation.py` verifica:

- `upgrade head` em banco vazio produz o mesmo esquema dos modelos, sem diferença
  detectada pelo autogenerate do Alembic;
- um banco criado antes das migrações é carimbado e atualizado sem erro;
- nenhum `upgrade` contém `drop_table`, `drop_column`, `alter_column` ou
  `rename_table`.

Para criar uma migração nova, altere o modelo e execute:

```bash
PYTHONPATH=src alembic revision --autogenerate --rev-id 000N_descricao -m "descrição"
```

Revise o arquivo gerado antes do commit; o autogenerate não substitui a revisão
humana.

## Consequências

- Positivas: o esquema passa a ter histórico, é reproduzível em qualquer banco e
  o teste de divergência impede que modelo e migração se afastem.
- Negativas: nova dependência (`alembic`) e um passo extra ao alterar modelos.
- Riscos abertos: a execução no PostgreSQL do Supabase/Render ainda não foi
  verificada. Os schemas por contexto previstos no antigo `001_initial.sql` não
  foram adotados; as tabelas continuam com prefixo por contexto no schema padrão.

## Alternativas consideradas

- Manter `create_all` e documentar a limitação: não resolve bancos persistentes.
- Scripts SQL numerados com executor próprio: evita dependência, mas exige
  código de controle de versão mantido pela equipe e não detecta divergência
  entre modelo e banco.
