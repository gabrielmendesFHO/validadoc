import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient

from app.models import StatusJornada, Usuarios, Inscricoes
from app.dependencies import exigir_jornada_minima, validar_status_funil, get_current_user
from app.db import get_db

app_test = FastAPI()

@app_test.get("/inscricoes/{inscricao_id}/rota-avancada")
def rota_avancada(
    inscricao_id: int,
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_PENDENTE)),
):
    return {"sucesso": True, "mensagem": "Acesso permitido"}


@pytest.fixture
def client():
    return TestClient(app_test)


def test_bloqueio_candidato_status_inicial(client):
    """Candidato com status PRE_CADASTRADO deve ter acesso bloqueado (HTTP 403)."""
    candidato = Usuarios(id=10, nome_completo="Candidato Teste", email="c@test.com", perfil="CANDIDATO")
    inscricao = Inscricoes(id=1, candidato_id=10, status_funil=StatusJornada.PRE_CADASTRADO)

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, obj_id: inscricao if model == Inscricoes and obj_id == 1 else None

    app_test.dependency_overrides[get_current_user] = lambda: candidato
    app_test.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/inscricoes/1/rota-avancada")
    assert response.status_code == 403
    assert "Ação bloqueada" in response.json()["detail"]
    assert "PRE_CADASTRADO" in response.json()["detail"]


def test_permissao_candidato_status_avancado(client):
    """Candidato com status >= KYC_PENDENTE deve conseguir acessar."""
    candidato = Usuarios(id=10, nome_completo="Candidato Teste", email="c@test.com", perfil="CANDIDATO")
    inscricao = Inscricoes(id=1, candidato_id=10, status_funil=StatusJornada.KYC_VALIDADO)

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, obj_id: inscricao if model == Inscricoes and obj_id == 1 else None

    app_test.dependency_overrides[get_current_user] = lambda: candidato
    app_test.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/inscricoes/1/rota-avancada")
    assert response.status_code == 200
    assert response.json()["sucesso"] is True


def test_permissao_analista_independente_status(client):
    """Analista ou Admin nunca deve ser bloqueado pela jornada do candidato."""
    analista = Usuarios(id=99, nome_completo="Analista Teste", email="a@test.com", perfil="ANALISTA")
    inscricao = Inscricoes(id=1, candidato_id=10, status_funil=StatusJornada.PRE_CADASTRADO)

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, obj_id: inscricao if model == Inscricoes and obj_id == 1 else None

    app_test.dependency_overrides[get_current_user] = lambda: analista
    app_test.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/inscricoes/1/rota-avancada")
    assert response.status_code == 200
    assert response.json()["sucesso"] is True

