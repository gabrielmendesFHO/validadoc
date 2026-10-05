from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app import main


def test_health_banco_disponivel(monkeypatch):
    engine = create_engine('sqlite://')
    monkeypatch.setattr(main, 'engine', engine, raising=False)
    response = TestClient(main.app).get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    engine.dispose()


def test_health_banco_indisponivel_sem_segredos(monkeypatch):
    class Indisponivel:
        def connect(self):
            raise RuntimeError('postgresql://usuario:segredo-nao-exibir@host/banco')
    monkeypatch.setattr(main, 'engine', Indisponivel(), raising=False)
    response = TestClient(main.app).get('/health')
    assert response.status_code == 503
    assert 'segredo' not in response.text and 'postgresql://' not in response.text
    assert response.json() == {'detail': 'Banco temporariamente indisponível'}
