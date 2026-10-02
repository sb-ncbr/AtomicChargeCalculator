import psycopg
from sqlalchemy import create_engine


def test_postgresql_uses_psycopg_binary():
    engine = create_engine("postgresql+psycopg://localhost/driver_test")
    try:
        assert engine.dialect.driver == "psycopg"
        assert engine.dialect.dbapi is psycopg
        assert psycopg.pq.__impl__ == "binary"
    finally:
        engine.dispose()
