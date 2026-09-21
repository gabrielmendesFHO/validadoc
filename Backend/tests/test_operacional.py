from datetime import date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import DefaultClause, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Base, Inscricoes, ProcessosBolsa, StatusJornada, Usuarios
from app.routes.operacional import router


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)

app_test = FastAPI()
app_test.include_router(router)


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(engine)
    default_mysql = Inscricoes.__table__.c.ultima_atividade.server_default
    Inscricoes.__table__.c.ultima_atividade.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))
    try:
        Base.metadata.create_all(engine)
    finally:
        Inscricoes.__table__.c.ultima_atividade.server_default = default_mysql
    db = TestingSession()
    db.add(ProcessosBolsa(id=1, nome="Bolsa 2026", data_inicio=date(2026, 1, 1), data_fim=date(2026, 12, 31)))
    db.add_all([
        Usuarios(id=1, nome_completo="Admin", email="admin@example.com", senha_hash="x", perfil="ADMIN"),
        Usuarios(id=2, nome_completo="Ana", email="ana@example.com", senha_hash="x", perfil="CANDIDATO"),
        Usuarios(id=3, nome_completo="Bruno", email="bruno@example.com", senha_hash="x", perfil="CANDIDATO"),
        Usuarios(id=4, nome_completo="Carla", email="carla@example.com", senha_hash="x", perfil="CANDIDATO"),
    ])
    db.add_all([
        Inscricoes(id=1, processo_id=1, candidato_id=2, status_funil=StatusJornada.PRE_CADASTRADO, status_geral="PENDENTE", alertas_dificuldade=0),
        Inscricoes(id=2, processo_id=1, candidato_id=3, status_funil=StatusJornada.PRONTO_AUDITORIA, status_geral="PENDENTE", alertas_dificuldade=0),
        Inscricoes(id=3, processo_id=1, candidato_id=4, status_funil=StatusJornada.DOCS_PENDENTES, status_geral="PENDENTE", alertas_dificuldade=2, ultimo_acesso=datetime.now() - timedelta(days=10)),
    ])
    db.commit()
    db.close()

    admin = Usuarios(id=1, nome_completo="Admin", email="admin@example.com", perfil="ADMIN")
    app_test.dependency_overrides[get_db] = _sessao_teste
    app_test.dependency_overrides[get_current_user] = lambda: admin
    yield
    app_test.dependency_overrides.clear()


def _sessao_teste():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app_test)


def test_metricas_agrupam_status_do_funil(client):
    response = client.get("/dashboard/metricas")
    assert response.status_code == 200
    dados = response.json()
    assert dados["total"] == 3
    assert dados["por_status"]["PRE_CADASTRADO"] == 1
    assert dados["por_status"]["PRONTO_AUDITORIA"] == 1
    assert dados["com_dificuldade"] == 1


def test_estagnadas_retorna_dificuldade_e_pronto_auditoria(client):
    response = client.get("/dashboard/estagnadas")
    assert response.status_code == 200
    dados = response.json()
    assert dados["total"] == 2
    assert {item["situacao"] for item in dados["itens"]} == {"COM_DIFICULDADE", "PRONTO_AUDITORIA"}


def test_parecer_manual_conclui_inscricao(client):
    response = client.put(
        "/auditoria/2/parecer",
        json={"decisao": "APROVAR", "justificativa": "Documentação conferida pelo analista."},
    )
    assert response.status_code == 200
    assert response.json()["status_geral"] == "APTO"
    assert response.json()["status_funil"] == "CONCLUIDO"

    db = TestingSession()
    inscricao = db.get(Inscricoes, 2)
    assert inscricao.parecer == "Documentação conferida pelo analista."
    assert inscricao.status_funil == StatusJornada.CONCLUIDO
    db.close()


def test_parecer_manual_rejeita_decisao_invalida(client):
    response = client.put(
        "/auditoria/2/parecer",
        json={"decisao": "ADIAR", "justificativa": "Falta revisar."},
    )
    assert response.status_code == 422
