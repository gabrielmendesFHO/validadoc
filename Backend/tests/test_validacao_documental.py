from types import SimpleNamespace
from datetime import datetime, timedelta
import pytest

from app.services.validacao_documental import validar_documento_no_upload


@pytest.fixture
def candidato():
    return SimpleNamespace(nome_completo="Gabriel Mendes", cpf="123.456.789-00")


@pytest.fixture
def membro_mae():
    return SimpleNamespace(id=1, nome_completo="Jocelina da Silva", parentesco="Mãe")


def test_rejeita_cnh_do_candidato_no_slot_da_mae_por_cpf(candidato, membro_mae):
    """Garante que a CNH do candidato enviada no slot da mãe seja rejeitada na hora pelo CPF."""
    dados_cnh_candidato = {
        "nome": "Gabriel Mendes",
        "cpf": "12345678900",
        "legibilidade": 95,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="CNH",
        dados_extraidos=dados_cnh_candidato,
        candidato=candidato,
        membro=membro_mae,
        outros_membros=[membro_mae],
    )

    assert valido is False
    assert nivel_alerta == "erro"
    assert "candidato titular" in motivo


def test_rejeita_cnh_do_candidato_no_slot_da_mae_por_nome(candidato, membro_mae):
    """Garante que mesmo sem CPF no doc, se o nome for do titular, seja barrado."""
    dados_sem_cpf = {
        "nome": "Gabriel Mendes",
        "cpf": None,
        "legibilidade": 95,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="RG",
        dados_extraidos={**dados_sem_cpf, "lado_documento": "frente"},
        candidato=candidato,
        membro=membro_mae,
        outros_membros=[membro_mae],
    )

    assert valido is False
    assert nivel_alerta == "erro"
    assert "candidato titular" in motivo


def test_rejeita_documento_de_terceiro_estranho_no_slot_do_membro(candidato, membro_mae):
    """Garante que um documento com nome aleatório não seja aceito para a mãe."""
    dados_terceiro = {
        "nome": "Carlos Alberto Pereira",
        "cpf": "99988877766",
        "legibilidade": 90,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="CNH",
        dados_extraidos=dados_terceiro,
        candidato=candidato,
        membro=membro_mae,
        outros_membros=[membro_mae],
    )

    assert valido is False
    assert nivel_alerta == "erro"
    assert "não confere com o familiar cadastrado" in motivo


def test_rejeita_documento_do_familiar_no_slot_do_titular(candidato, membro_mae):
    """Garante que documento da mãe não seja aceito no slot do candidato."""
    dados_mae = {
        "nome": "Jocelina da Silva",
        "cpf": "44455566677",
        "legibilidade": 92,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="CNH",
        dados_extraidos=dados_mae,
        candidato=candidato,
        membro=None,  # slot do titular
        outros_membros=[membro_mae],
    )

    assert valido is False
    assert nivel_alerta == "erro"
    assert "familiar 'Jocelina da Silva'" in motivo


def test_avisa_baixa_nitidez(candidato, membro_mae):
    """Documento com legibilidade < 50 é aceito mas recebe alerta amarelo."""
    dados = {
        "nome": "Jocelina da Silva",
        "cpf": "44455566677",
        "legibilidade": 42,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="CNH",
        dados_extraidos=dados,
        candidato=candidato,
        membro=membro_mae,
        outros_membros=[membro_mae],
    )

    assert valido is True
    assert nivel_alerta == "aviso"
    assert "baixa nitidez" in feedback


def test_avisa_comprovante_residencia_vencido(candidato):
    """Comprovante com mais de 90 dias recebe aviso de temporalidade."""
    data_antiga = (datetime.now() - timedelta(days=120)).strftime("%d/%m/%Y")
    dados = {
        "nome_titular": "Gabriel Mendes",
        "endereco": "Rua das Flores, 123",
        "data_emissao": data_antiga,
        "legibilidade": 95,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="RESIDENCIA",
        dados_extraidos=dados,
        candidato=candidato,
        membro=None,
        outros_membros=[],
    )

    assert valido is True
    assert nivel_alerta == "aviso"
    assert "limite aceito pelo processo seletivo é de até 90 dias" in feedback


def test_documento_valido_sucesso(candidato, membro_mae):
    """Documento correto gera nível de alerta sucesso."""
    dados = {
        "nome": "Jocelina da Silva",
        "cpf": "44455566677",
        "legibilidade": 95,
        "documento_integro": True,
    }

    valido, motivo, nivel_alerta, feedback = validar_documento_no_upload(
        categoria="CNH",
        dados_extraidos=dados,
        candidato=candidato,
        membro=membro_mae,
        outros_membros=[membro_mae],
    )

    assert valido is True
    assert nivel_alerta == "sucesso"
    assert "aprovado com sucesso" in feedback

