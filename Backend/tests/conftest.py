import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture
def pg_engine():
    raw = os.environ.get('TEST_POSTGRESQL_URL')
    if not raw:
        pytest.skip('Requer PostgreSQL descartável em TEST_POSTGRESQL_URL')
    url = make_url(raw)
    if url.get_backend_name() != 'postgresql' or not (url.database or '').startswith('validadoc_test_'):
        pytest.fail('Banco de teste deve ser PostgreSQL dedicado chamado validadoc_test_*')
    schema = 'teste_' + uuid.uuid4().hex
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
