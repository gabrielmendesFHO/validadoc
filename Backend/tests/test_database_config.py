import subprocess
import sys
import pytest
from app.database_config import normalize_database_url


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql', 'postgresql+psycopg'])
def test_url_neon_preserva_credenciais_e_tls(scheme):
    url = normalize_database_url(f'{scheme}://usuario:p%40ss@host.invalid:5432/banco?sslmode=require&channel_binding=require')
    assert url.drivername == 'postgresql+psycopg'
    assert url.username == 'usuario' and url.password == 'p@ss'
    assert url.host == 'host.invalid' and url.database == 'banco'
    assert dict(url.query) == {'sslmode': 'require', 'channel_binding': 'require'}


def test_mysql_continua_disponivel():
    assert normalize_database_url('mysql+pymysql://root@localhost/local').drivername == 'mysql+pymysql'


def test_importar_db_nao_conecta(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'mysql+pymysql://u:p@127.0.0.1:1/inexistente')
    result = subprocess.run([sys.executable, '-c', 'import app.db'], capture_output=True, timeout=20)
    assert result.returncode == 0, 'Importar app.db tentou conectar à rede'
