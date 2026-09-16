import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.integracao import router as integracao_router, PreCadastroERPIn
from app.models import StatusJornada, Usuarios, ProcessosBolsa, Inscricoes
from app.dependencies import get_current_user
from app.db import get_db

# Usuário admin falso para bypassar autenticação nos testes
_usuario_admin_fake = Usuarios(id=1, nome_completo="Admin Teste", email="admin@test.com", perfil="ADMIN")

app_integracao = FastAPI()
app_integracao.include_router(integracao_router)


@pytest.fixture
def client():
    # Substitui validação de token JWT por retorno direto do usuário admin fake a cada requisição do fixture client
    app_integracao.dependency_overrides[get_current_user] = lambda: _usuario_admin_fake
    yield TestClient(app_integracao)
    app_integracao.dependency_overrides.clear()


def test_status_jornada_enum():
    """Valida se o enum StatusJornada contém os estados esperados e se comporta como string."""
    assert StatusJornada.PRE_CADASTRADO == "PRE_CADASTRADO"
    assert StatusJornada.KYC_PENDENTE == "KYC_PENDENTE"
    assert StatusJornada.KYC_VALIDADO == "KYC_VALIDADO"
    assert StatusJornada.FAMILIA_PENDENTE == "FAMILIA_PENDENTE"
    assert StatusJornada.DOCS_PENDENTES == "DOCS_PENDENTES"
    assert StatusJornada.PRONTO_AUDITORIA == "PRONTO_AUDITORIA"
    assert StatusJornada.CONCLUIDO == "CONCLUIDO"
    assert StatusJornada.ABANDONO == "ABANDONO"
    assert isinstance(StatusJornada.PRE_CADASTRADO, str)


def test_precadastro_schema_valid():
    """Valida o parser Pydantic com nome_completo e campos adicionais do ERP."""
    payload = {
        "nome_completo": "Gabriel Mendes",
        "email": "gabriel@exemplo.com",
        "cpf": "123.456.789-00",
        "curso": "Engenharia de Software",
        "matricula": "12345",
        "custom_erp_id": 999,  # Campo extra permitido
    }
    obj = PreCadastroERPIn(**payload)
    assert obj.nome_efetivo == "Gabriel Mendes"
    assert obj.cpf == "123.456.789-00"


def test_precadastro_schema_suporta_nome_simples():
    """Valida suporte ao campo alternativo 'nome'."""
    payload = {
        "nome": "Gabriel Mendes",
        "email": "gabriel@exemplo.com",
        "cpf": "12345678900",
    }
    obj = PreCadastroERPIn(**payload)
    assert obj.nome_efetivo == "Gabriel Mendes"


def test_precadastro_schema_sem_nome_lanca_erro():
    """Garante erro quando nenhum nome é informado."""
    payload = {
        "email": "gabriel@exemplo.com",
        "cpf": "12345678900",
    }
    obj = PreCadastroERPIn(**payload)
    with pytest.raises(ValueError):
        _ = obj.nome_efetivo


def test_endpoint_pre_cadastro_novo_candidato(client):
    """Testa criação com sucesso de novo candidato pré-cadastrado."""
    mock_db = MagicMock()
    
    # Simula nenhum usuário existente
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query_user = MagicMock()
    mock_query_user.filter.return_value = mock_filter

    # Simula processo seletivo ativo existente
    mock_processo = ProcessosBolsa(
        id=1,
        nome="Processo 2026",
    )
    mock_query_proc = MagicMock()
    mock_order = MagicMock()
    mock_order.first.return_value = mock_processo
    mock_query_proc.order_by.return_value = mock_order

    # Simula ausência de inscrição prévia
    mock_filter_inscricao = MagicMock()
    mock_filter_inscricao.first.return_value = None
    mock_query_inscricao = MagicMock()
    mock_query_inscricao.filter_by.return_value = mock_filter_inscricao

    def query_side_effect(model):
        if model == Usuarios:
            return mock_query_user
        if model == ProcessosBolsa:
            return mock_query_proc
        if model == Inscricoes:
            return mock_query_inscricao
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    # Mock de flush/refresh para popular IDs
    def flush_side_effect():
        for call_arg in mock_db.add.call_args_list:
            instance = call_arg[0][0]
            if isinstance(instance, Usuarios) and not instance.id:
                instance.id = 42
            elif isinstance(instance, Inscricoes) and not instance.id:
                instance.id = 99
    mock_db.flush.side_effect = flush_side_effect

    app_integracao.dependency_overrides[get_db] = lambda: mock_db

    response = client.post(
        "/api/v1/integracao/pre-cadastro",
        json={
            "nome_completo": "Candidato Novo Teste",
            "email": "novo@exemplo.com",
            "cpf": "12345678901",
            "curso": "Sistemas de Informação",
            "matricula": "2026001",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sucesso"] is True
    assert data["status_jornada"] == "PRE_CADASTRADO"
    assert data["novo_usuario"] is True
    assert data["usuario"]["nome_completo"] == "Candidato Novo Teste"
    assert data["usuario"]["cpf"] == "123.456.789-01"
    assert data["dados_academicos"]["curso"] == "Sistemas de Informação"


def test_endpoint_pre_cadastro_usuario_existente(client):
    """Testa idempotência: webhook reenviado para aluno já cadastrado."""
    mock_db = MagicMock()

    usuario_existente = Usuarios(
        id=10,
        nome_completo="Aluno Já Cadastrado",
        email="existente@exemplo.com",
        cpf="123.456.789-01",
        perfil="CANDIDATO",
        instituicao_id=1,
    )

    mock_filter = MagicMock()
    mock_filter.first.return_value = usuario_existente
    mock_query_user = MagicMock()
    mock_query_user.filter.return_value = mock_filter

    mock_processo = ProcessosBolsa(id=1, nome="Processo 2026")
    mock_query_proc = MagicMock()
    mock_order = MagicMock()
    mock_order.first.return_value = mock_processo
    mock_query_proc.order_by.return_value = mock_order

    inscricao_existente = Inscricoes(
        id=55,
        processo_id=1,
        candidato_id=10,
        status_funil=StatusJornada.PRE_CADASTRADO,
        status_geral="PENDENTE",
    )
    mock_filter_insc = MagicMock()
    mock_filter_insc.first.return_value = inscricao_existente
    mock_query_insc = MagicMock()
    mock_query_insc.filter_by.return_value = mock_filter_insc

    def query_side_effect(model):
        if model == Usuarios:
            return mock_query_user
        if model == ProcessosBolsa:
            return mock_query_proc
        if model == Inscricoes:
            return mock_query_insc
        return MagicMock()

    mock_db.query.side_effect = query_side_effect
    app_integracao.dependency_overrides[get_db] = lambda: mock_db

    response = client.post(
        "/api/v1/integracao/pre-cadastro",
        json={
            "nome": "Aluno Já Cadastrado",
            "email": "existente@exemplo.com",
            "cpf": "123.456.789-01",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sucesso"] is True
    assert data["novo_usuario"] is False
    assert data["usuario"]["id"] == 10
    assert data["status_jornada"] == "PRE_CADASTRADO"


def test_endpoint_pre_cadastro_cpf_invalido(client):
    """Garante retorno 422 quando CPF não contém 11 dígitos."""
    response = client.post(
        "/api/v1/integracao/pre-cadastro",
        json={
            "nome": "Candidato Erro CPF",
            "email": "erro@exemplo.com",
            "cpf": "123",
        },
    )
    assert response.status_code == 422
    assert "CPF inválido" in response.text


def test_disparo_email_novo_candidato(client):
    """Garante que a task de envio de e-mail com senha temporária é acionada ao criar novo candidato."""
    from unittest.mock import patch
    mock_db = MagicMock()

    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query_user = MagicMock()
    mock_query_user.filter.return_value = mock_filter

    mock_processo = ProcessosBolsa(id=1, nome="Processo 2026")
    mock_query_proc = MagicMock()
    mock_order = MagicMock()
    mock_order.first.return_value = mock_processo
    mock_query_proc.order_by.return_value = mock_order

    mock_filter_insc = MagicMock()
    mock_filter_insc.first.return_value = None
    mock_query_insc = MagicMock()
    mock_query_insc.filter_by.return_value = mock_filter_insc

    def query_side_effect(model):
        if model == Usuarios:
            return mock_query_user
        if model == ProcessosBolsa:
            return mock_query_proc
        if model == Inscricoes:
            return mock_query_insc
        return MagicMock()

    mock_db.query.side_effect = query_side_effect
    app_integracao.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.routes.integracao.enviar_email_boas_vindas") as mock_email:
        response = client.post(
            "/api/v1/integracao/pre-cadastro",
            json={
                "nome_completo": "Aluno Teste Email",
                "email": "email_teste@exemplo.com",
                "cpf": "99988877766",
            },
        )
        assert response.status_code == 201
        # Verifica se o serviço de email foi agendado e chamado pela background task
        assert mock_email.called
        call_kwargs = mock_email.call_args.kwargs
        assert call_kwargs["email_destino"] == "email_teste@exemplo.com"
        assert call_kwargs["nome_candidato"] == "Aluno Teste Email"
        assert len(call_kwargs["senha_temporaria"]) > 0


def test_upload_csv_em_massa(client):
    """Testa leitura e inserção em lote via upload de arquivo CSV."""
    from pathlib import Path
    from unittest.mock import patch

    mock_db = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query_user = MagicMock()
    mock_query_user.filter.return_value = mock_filter

    mock_processo = ProcessosBolsa(id=1, nome="Processo 2026")
    mock_query_proc = MagicMock()
    mock_order = MagicMock()
    mock_order.first.return_value = mock_processo
    mock_query_proc.order_by.return_value = mock_order

    mock_filter_insc = MagicMock()
    mock_filter_insc.first.return_value = None
    mock_query_insc = MagicMock()
    mock_query_insc.filter_by.return_value = mock_filter_insc

    def query_side_effect(model):
        if model == Usuarios:
            return mock_query_user
        if model == ProcessosBolsa:
            return mock_query_proc
        if model == Inscricoes:
            return mock_query_insc
        return MagicMock()

    mock_db.query.side_effect = query_side_effect
    app_integracao.dependency_overrides[get_db] = lambda: mock_db

    csv_path = Path(__file__).resolve().parents[1] / "candidatos_teste.csv"
    assert csv_path.exists(), "Arquivo candidatos_teste.csv não encontrado"

    with patch("app.routes.integracao.enviar_email_boas_vindas") as mock_email:
        with open(csv_path, "rb") as f:
            response = client.post(
                "/api/v1/integracao/upload-csv",
                files={"file": ("candidatos_teste.csv", f, "text/csv")}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["sucesso"] is True
        assert data["total_processados"] == 5
        assert data["novos_usuarios"] == 5
        assert data["erros"] == []
        assert mock_email.call_count == 5


