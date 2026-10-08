from datetime import date, datetime, timedelta
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    AnalisesOcr, Base, DocumentosEnviados, DocumentosSolicitados, Inscricoes,
    MembrosFamilia, ProcessosBolsa, StatusJornada, Usuarios,
)
from app.routes.operacional import router
from app.routes import documentos as documentos_routes
from app.routes.inscricoes import _gerar_checklist_para_pessoa, router as inscricoes_router


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)

app_test = FastAPI()
app_test.include_router(router)
app_test.include_router(inscricoes_router)


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
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


def test_auditoria_expoe_motivos_persistidos_da_revisao(client):
    with TestingSession() as db:
        inscricao = db.get(Inscricoes, 2)
        inscricao.status_geral = "REVISAO_MANUAL"
        inscricao.inconsistencias = json.dumps(["CPF divergente.", "Holerite ausente."])
        db.commit()

    response = client.get("/auditoria/2")
    assert response.status_code == 200
    assert response.json()["inscricao"]["inconsistencias"] == ["CPF divergente.", "Holerite ausente."]


def test_revisao_automatica_permanece_na_fila_do_analista(client):
    response = client.post("/inscricoes/2/auditar")
    assert response.status_code == 200
    assert response.json()["status_geral"] == "REVISAO_MANUAL"
    with TestingSession() as db:
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.PRONTO_AUDITORIA
    fila = client.get("/dashboard/estagnadas").json()["itens"]
    assert any(item["inscricao_id"] == 2 and item["situacao"] == "PRONTO_AUDITORIA" for item in fila)


def _preparar_reenvio(categoria="RG", antigo="REJEITADO", atual="CONCLUIDO", membro_id=None):
    """Histórico fictício em SQLite; nenhum arquivo ou provedor externo é usado."""
    with TestingSession() as db:
        inscricao = db.get(Inscricoes, 2)
        inscricao.status_funil = StatusJornada.DOCS_PENDENTES
        candidato = db.get(Usuarios, 3)
        candidato.cpf = "111.444.777-35"
        db.add(DocumentosSolicitados(id=1, processo_id=1, nome_documento=categoria, obrigatorio=1))
        if membro_id is not None:
            db.add(MembrosFamilia(id=membro_id, inscricao_id=2, nome_completo="Familiar Ficticio", cpf="111.444.777-35"))
            db.add(DocumentosEnviados(id=3, inscricao_id=2, solicitado_id=1, status_processamento="CONCLUIDO"))
        for doc_id, estado, instante in (
            (1, antigo, datetime(2026, 10, 5, 10)),
            (2, atual, datetime(2026, 10, 5, 11)),
        ):
            db.add(DocumentosEnviados(
                id=doc_id, inscricao_id=2, solicitado_id=1, membro_id=membro_id,
                status_processamento=estado, criado_em=instante,
            ))
            db.add(AnalisesOcr(
                documento_id=doc_id,
                dados_extraidos=json.dumps({
                    "nome": "Bruno" if membro_id is None else "Familiar Ficticio",
                    "cpf": "111.444.777-35", "legibilidade": 95, "documento_integro": True,
                }),
                status_auditoria="POSSIVEL_DIVERGENCIA" if doc_id == 1 else "VALIDO",
            ))
        db.commit()


def test_rg_corrigido_substitui_rejeicao_na_auditoria_preservando_historico(client):
    _preparar_reenvio()
    with TestingSession() as db:
        db.add(DocumentosSolicitados(id=2, processo_id=1, nome_documento="RG_VERSO", obrigatorio=1))
        db.add(DocumentosEnviados(id=3, inscricao_id=2, solicitado_id=2, status_processamento="CONCLUIDO"))
        db.add(AnalisesOcr(documento_id=3, dados_extraidos=json.dumps({"cpf": "111.444.777-35"}), status_auditoria="VALIDO"))
        db.commit()

    response = client.post("/inscricoes/2/auditar")
    assert response.status_code == 200
    motivos = response.json()["inconsistencias"]
    assert not any("Nenhum documento de identidade" in motivo for motivo in motivos)
    assert not any("tipo esperado" in motivo for motivo in motivos)
    historico = client.get("/inscricoes/2/detalhe").json()["documentos_enviados"]
    assert {item["id"] for item in historico} == {1, 2, 3}
    assert next(item for item in historico if item["id"] == 1)["status"] == "REJEITADO"


def test_cnh_corrigida_nao_herda_alerta_da_versao_antiga(client):
    _preparar_reenvio(categoria="CNH", antigo="CONCLUIDO")
    response = client.post("/inscricoes/2/auditar")
    assert response.status_code == 200
    assert not any("tipo esperado" in motivo for motivo in response.json()["inconsistencias"])


@pytest.mark.parametrize("atual", ["REJEITADO", "ERRO_EXTRACAO", "PROCESSANDO_IA"])
@pytest.mark.parametrize("membro_id", [None, 1])
def test_conclusao_bloqueia_reenvio_pendente_mesmo_com_aprovacao_antiga(client, atual, membro_id):
    _preparar_reenvio(antigo="CONCLUIDO", atual=atual, membro_id=membro_id)
    response = client.post("/inscricoes/2/documentos/concluir")
    assert response.status_code == 409
    with TestingSession() as db:
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.DOCS_PENDENTES


@pytest.mark.parametrize("membro_id", [None, 1])
def test_auditoria_bloqueia_ultimo_obrigatorio_rejeitado(client, membro_id):
    _preparar_reenvio(antigo="CONCLUIDO", atual="REJEITADO", membro_id=membro_id)
    response = client.post("/inscricoes/2/auditar")
    assert response.status_code == 200
    assert response.json()["status_geral"] == "PENDENTE"
    with TestingSession() as db:
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.DOCS_PENDENTES


def test_checklist_desempata_data_igual_pelo_id_independentemente_da_ordem(client):
    _preparar_reenvio(antigo="CONCLUIDO", atual="REJEITADO")
    with TestingSession() as db:
        db.get(DocumentosEnviados, 1).criado_em = datetime(2026, 10, 5, 11)
        db.commit()
        enviados = db.query(DocumentosEnviados).order_by(DocumentosEnviados.id.desc()).all()
        solicitados = db.query(DocumentosSolicitados).all()
        checklist = _gerar_checklist_para_pessoa(db, None, solicitados, enviados)
        assert checklist[0]["itens"][0]["documento_id"] == 2
        assert checklist[0]["status"] == "REJEITADO"


def test_kyc_nao_avanca_por_identidade_antiga_apos_reenvio_rejeitado(client):
    _preparar_reenvio(antigo="CONCLUIDO", atual="REJEITADO")
    with TestingSession() as db:
        candidato = db.get(Usuarios, 3)
        db.expunge(candidato)
    app_test.dependency_overrides[get_current_user] = lambda: candidato
    response = client.post("/inscricoes/2/kyc/concluir")
    assert response.status_code == 409


@pytest.mark.parametrize('idade,esperado', [(30, 'PROCESSANDO_IA'), (180, 'ERRO_EXTRACAO')])
def test_kyc_libera_reenvio_interrompido_e_preserva_processamento_recente(client, idade, esperado):
    _preparar_reenvio(antigo='PROCESSANDO_IA', atual='PROCESSANDO_IA')
    with TestingSession() as db:
        db.get(Inscricoes, 2).status_funil = StatusJornada.KYC_PENDENTE
        db.get(DocumentosEnviados, 2).criado_em = datetime.now() - timedelta(seconds=idade)
        db.commit()
        candidato = db.get(Usuarios, 3)
        db.expunge(candidato)
    app_test.dependency_overrides[get_current_user] = lambda: candidato
    response = client.get('/inscricoes/2/kyc')
    assert response.status_code == 200
    assert response.json()['documentos'][0]['status'] == esperado
    with TestingSession() as db:
        assert db.get(DocumentosEnviados, 2).status_processamento == esperado
        assert db.get(DocumentosEnviados, 1).status_processamento == 'PROCESSANDO_IA'
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.KYC_PENDENTE


@pytest.mark.parametrize("membro_id", [None, 1])
def test_conclusao_aceita_reenvio_corrigido_sem_apagar_historico(client, membro_id):
    _preparar_reenvio(membro_id=membro_id)
    response = client.post("/inscricoes/2/documentos/concluir")
    assert response.status_code == 200
    assert response.json()["status_funil"] == "PRONTO_AUDITORIA"
    with TestingSession() as db:
        assert db.get(DocumentosEnviados, 1).status_processamento == "REJEITADO"
        assert db.get(DocumentosEnviados, 2).status_processamento == "CONCLUIDO"


def test_kyc_aceita_cnh_atual_aprovada_quando_rg_atual_foi_rejeitado(client):
    _preparar_reenvio(antigo="CONCLUIDO", atual="REJEITADO")
    with TestingSession() as db:
        db.add(DocumentosSolicitados(id=2, processo_id=1, nome_documento="CNH", obrigatorio=0))
        db.add(DocumentosEnviados(id=3, inscricao_id=2, solicitado_id=2, status_processamento="CONCLUIDO"))
        db.commit()
        candidato = db.get(Usuarios, 3)
        db.expunge(candidato)
    app_test.dependency_overrides[get_current_user] = lambda: candidato
    response = client.post("/inscricoes/2/kyc/concluir")
    assert response.status_code == 200
    assert response.json()["status_funil"] == "FAMILIA_PENDENTE"


@pytest.mark.parametrize("processado_id", [1, 2])
def test_extracao_so_avanca_kyc_e_preenche_cadastro_se_envio_ainda_vigente(monkeypatch, processado_id):
    _preparar_reenvio(antigo="PROCESSANDO_IA", atual="REJEITADO" if processado_id == 1 else "PROCESSANDO_IA")
    with TestingSession() as db:
        db.get(Inscricoes, 2).status_funil = StatusJornada.KYC_PENDENTE
        candidato = db.get(Usuarios, 3)
        candidato.nome_completo = "Candidato (Teste)"
        candidato.cpf = None
        db.commit()
    monkeypatch.setattr(documentos_routes, "SessionLocal", TestingSession)
    monkeypatch.setattr(documentos_routes, "extrair_dados_documento", lambda *_args: {
        "nome": "Bruno", "cpf": "111.444.777-35", "legibilidade": 95, "documento_integro": True,
        "lado_documento": "frente", "data_nascimento": "01/01/2000", "nome_mae": "Mae Ficticia",
    })
    documentos_routes._processar_ia_em_background(processado_id, b"ficticio", "image/jpeg", "RG", 2, 3, None)

    with TestingSession() as db:
        assert db.get(DocumentosEnviados, processado_id).status_processamento == "CONCLUIDO"
        assert db.query(AnalisesOcr).filter_by(documento_id=processado_id).count() == 2
        candidato = db.get(Usuarios, 3)
        if processado_id == 1:
            assert db.get(Inscricoes, 2).status_funil == StatusJornada.KYC_PENDENTE
            assert candidato.cpf is None
            assert candidato.nome_completo == "Candidato (Teste)"
        else:
            assert db.get(Inscricoes, 2).status_funil == StatusJornada.FAMILIA_PENDENTE
            assert candidato.cpf == "111.444.777-35"
            assert candidato.nome_completo == "Bruno"


def test_extracao_considera_reenvio_registrado_durante_chamada_da_ia(monkeypatch):
    _preparar_reenvio(atual="PROCESSANDO_IA")
    with TestingSession() as db:
        db.get(Inscricoes, 2).status_funil = StatusJornada.KYC_PENDENTE
        db.commit()

    sessoes = []

    def abrir_sessao():
        db = TestingSession()
        sessoes.append(db)
        return db

    def extrair_com_reenvio(*_args):
        # Não conservar a transação/snapshot inicial durante a chamada externa.
        assert not sessoes[0].in_transaction()
        with TestingSession() as db:
            db.add(DocumentosEnviados(
                id=3, inscricao_id=2, solicitado_id=1, status_processamento="REJEITADO",
                criado_em=datetime(2026, 10, 5, 12),
            ))
            db.commit()
        return {
            "nome": "Bruno", "cpf": "111.444.777-35", "lado_documento": "frente",
            "data_nascimento": "01/01/2000", "nome_mae": "Mae Ficticia",
        }

    monkeypatch.setattr(documentos_routes, "SessionLocal", abrir_sessao)
    monkeypatch.setattr(documentos_routes, "extrair_dados_documento", extrair_com_reenvio)
    documentos_routes._processar_ia_em_background(2, b"ficticio", "image/jpeg", "RG", 2, 3, None)
    with TestingSession() as db:
        assert db.get(DocumentosEnviados, 2).status_processamento == "CONCLUIDO"
        assert db.get(DocumentosEnviados, 3).status_processamento == "REJEITADO"
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.KYC_PENDENTE


def test_extracao_rejeita_cpf_divergente_do_familiar_e_aceita_reenvio_corrigido(monkeypatch):
    with TestingSession() as db:
        db.get(Inscricoes, 2).status_funil = StatusJornada.KYC_PENDENTE
        candidato = db.get(Usuarios, 3)
        candidato.nome_completo = "Candidato (Teste)"
        candidato.cpf = None
        db.add(MembrosFamilia(id=1, inscricao_id=2, nome_completo="Familiar Ficticio", cpf="529.982.247-25"))
        db.add(DocumentosSolicitados(id=1, processo_id=1, nome_documento="CNH", obrigatorio=1))
        db.add(DocumentosEnviados(
            id=1, inscricao_id=2, solicitado_id=1, membro_id=1, status_processamento="PROCESSANDO_IA",
            criado_em=datetime(2026, 10, 5, 10),
        ))
        db.commit()

    dados = {
        "nome": "Familiar Ficticio", "cpf": "390.533.447-05", "numero_cnh": "12345678901",
        "legibilidade": 95, "documento_integro": True,
    }
    monkeypatch.setattr(documentos_routes, "SessionLocal", TestingSession)
    monkeypatch.setattr(documentos_routes, "extrair_dados_documento", lambda *_args: dados.copy())
    documentos_routes._processar_ia_em_background(1, b"ficticio", "image/jpeg", "CNH", 2, 3, 1)

    with TestingSession() as db:
        documento = db.get(DocumentosEnviados, 1)
        analise = db.query(AnalisesOcr).filter_by(documento_id=1).one()
        assert documento.status_processamento == "REJEITADO"
        assert analise.status_auditoria == "REJEITADO"
        assert "CPF do documento não confere com o CPF do familiar cadastrado" in documento.mensagem_erro
        assert analise.parecer == documento.mensagem_erro
        assert "390.533.447-05" not in analise.parecer
        assert "529.982.247-25" not in analise.parecer
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.KYC_PENDENTE
        assert db.get(Usuarios, 3).nome_completo == "Candidato (Teste)"
        assert db.get(Usuarios, 3).cpf is None
        assert db.get(MembrosFamilia, 1).cpf == "529.982.247-25"
        assert db.get(MembrosFamilia, 1).nome_completo == "Familiar Ficticio"
        db.add(DocumentosEnviados(
            id=2, inscricao_id=2, solicitado_id=1, membro_id=1, status_processamento="PROCESSANDO_IA",
            criado_em=datetime(2026, 10, 5, 11),
        ))
        db.commit()

    dados["cpf"] = "52998224725"
    documentos_routes._processar_ia_em_background(2, b"corrigido", "image/jpeg", "CNH", 2, 3, 1)
    with TestingSession() as db:
        assert db.get(DocumentosEnviados, 1).status_processamento == "REJEITADO"
        assert db.get(DocumentosEnviados, 2).status_processamento == "CONCLUIDO"
        assert db.get(DocumentosEnviados, 2).mensagem_erro is None
        assert db.query(AnalisesOcr).filter_by(documento_id=1).one().status_auditoria == "REJEITADO"
        assert db.query(AnalisesOcr).filter_by(documento_id=2).one().status_auditoria == "EXTRAIDO"
        assert db.get(Inscricoes, 2).status_funil == StatusJornada.KYC_PENDENTE
        assert db.get(Usuarios, 3).nome_completo == "Candidato (Teste)"
        assert db.get(Usuarios, 3).cpf is None
        assert db.get(MembrosFamilia, 1).cpf == "529.982.247-25"
        assert db.get(MembrosFamilia, 1).nome_completo == "Familiar Ficticio"
