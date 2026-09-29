from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

import archcorp.infrastructure.db as db


def test_public_postgres_disables_direct_data_api_access(monkeypatch):
    statements = []

    class Connection:
        def execute(self, statement):
            return SimpleNamespace(scalars=lambda: ["anon", "authenticated"])

        def exec_driver_sql(self, statement):
            statements.append(statement)

    monkeypatch.setattr(db, "engine", SimpleNamespace(dialect=postgresql.dialect()))
    monkeypatch.setattr(db.settings, "public_demo", True)

    db.protect_public_demo_tables(Connection())

    for table in db.Base.metadata.sorted_tables:
        name = db.engine.dialect.identifier_preparer.format_table(table)
        assert f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY" in statements
        assert f"REVOKE ALL PRIVILEGES ON TABLE {name} FROM anon" in statements
        assert f"REVOKE ALL PRIVILEGES ON TABLE {name} FROM authenticated" in statements
