from types import SimpleNamespace
from datetime import datetime, timedelta
import pytest

from app.services.validacao_documental import validar_documento_no_upload


@pytest.fixture
def candidato():
    return SimpleNamespace(nome_completo="Gabriel Mendes", cpf="123.456.789-00")


@pytest.fixture
def membro_mae():
    return SimpleNamespace(id=1, nome_completo="Jocelina da Silva", cpf="444.555.666-77", parentesco="Mãe")


def _dados_identidade_familiar(categoria, nome="Jocelina da Silva", cpf="44455566677"):
    dados = {"nome": nome, "cpf": cpf, "legibilidade": 95, "documento_integro": True}
    if categoria == "RG":
        dados.update(lado_documento="frente", data_nascimento="01/01/1970", nome_pai="Pai", nome_mae="Mae")
    elif categoria == "RG_VERSO":
        dados.update(lado_documento="verso", numero_rg="1234567")
    else:
        dados["numero_cnh"] = "12345678901"
    return dados


@pytest.mark.parametrize("categoria,nome", [
    (categoria, nome)
    for categoria in ("RG", "RG_VERSO", "CNH")
    for nome in ("Jocelina da Silva", "Maria da Costa")
] + [("RG_VERSO", None)])
def test_rejeita_cpf_divergente_do_familiar_mesmo_com_nome_compativel(candidato, membro_mae, categoria, nome):
    valido, motivo, nivel, feedback = validar_documento_no_upload(
        categoria, _dados_identidade_familiar(categoria, nome, "99988877766"),
        candidato, membro_mae, [membro_mae],
    )
    assert valido is False
    assert nivel == "erro"
    assert "CPF do documento não confere com o CPF do familiar cadastrado" in motivo
    assert feedback == motivo
    assert "99988877766" not in feedback
    assert membro_mae.cpf not in feedback


@pytest.mark.parametrize("categoria", ["RG", "RG_VERSO", "CNH"])
@pytest.mark.parametrize("cpf_doc,cpf_membro", [
    ("44455566677", "444.555.666-77"),
    ("444.555.666-77", "44455566677"),
])
def test_cpf_formatado_do_familiar_confere(candidato, membro_mae, categoria, cpf_doc, cpf_membro):
    membro_mae.cpf = cpf_membro
    valido, motivo, nivel, _ = validar_documento_no_upload(
        categoria, _dados_identidade_familiar(categoria, cpf=cpf_doc),
        candidato, membro_mae, [membro_mae],
    )
    assert valido is True
    assert motivo is None
    assert nivel == "sucesso"


@pytest.mark.parametrize("categoria", ["RG", "RG_VERSO", "CNH"])
@pytest.mark.parametrize("cpf_doc,cpf_membro", [
    (None, "444.555.666-77"),
    ("44455566677", None),
    (None, None),
])
def test_ausencia_de_cpf_preserva_validacao_existente(candidato, membro_mae, categoria, cpf_doc, cpf_membro):
    membro_mae.cpf = cpf_membro
    dados = _dados_identidade_familiar(categoria, cpf=cpf_doc)
    if categoria == "RG" and cpf_doc is None:
        dados.pop("cpf", None)  # A frente do RG normalmente não traz CPF.
    valido, motivo, nivel, _ = validar_documento_no_upload(
        categoria, dados, candidato, membro_mae, [membro_mae],
    )
    assert valido is True
    assert motivo is None
    assert nivel == ("aviso" if categoria == "RG_VERSO" and cpf_doc is None else "sucesso")


def test_familiar_sem_atributo_cpf_preserva_validacao(candidato):
    membro = SimpleNamespace(nome_completo="Jocelina da Silva")
    valido, motivo, nivel, _ = validar_documento_no_upload(
        "CNH", _dados_identidade_familiar("CNH"), candidato, membro, [membro],
    )
    assert (valido, motivo, nivel) == (True, None, "sucesso")


@pytest.mark.parametrize("nome,cpf", [
    ("Jocelina da Silva", "12345678900"),
    ("Gabriel Mendes", "99988877766"),
])
def test_titular_tem_prioridade_sobre_cpf_divergente_do_familiar(candidato, membro_mae, nome, cpf):
    valido, motivo, nivel, _ = validar_documento_no_upload(
        "CNH", _dados_identidade_familiar("CNH", nome, cpf), candidato, membro_mae, [membro_mae],
    )
    assert valido is False
    assert nivel == "erro"
    assert "candidato titular" in motivo


@pytest.mark.parametrize("categoria,lado_errado,lado_esperado", [
    ("RG", "verso", "frente"), ("RG_VERSO", "frente", "verso"),
])
def test_lado_do_rg_tem_prioridade_sobre_cpf_divergente_do_familiar(candidato, membro_mae, categoria, lado_errado, lado_esperado):
    dados = _dados_identidade_familiar(categoria, cpf="99988877766")
    dados["lado_documento"] = lado_errado
    valido, motivo, nivel, _ = validar_documento_no_upload(
        categoria, dados, candidato, membro_mae, [membro_mae],
    )
    assert valido is False
    assert nivel == "erro"
    assert f"exige o lado {lado_esperado}" in motivo


@pytest.mark.parametrize("nome,cpf", [
    ("Outra Pessoa", "99988877766"),
    ("Gabriel Mendes", "99988877766"),
    ("Outra Pessoa", None),
])
def test_rejeita_identidade_divergente_do_titular(candidato, nome, cpf):
    valido, motivo, nivel, _ = validar_documento_no_upload(
        "CNH", {"nome": nome, "cpf": cpf, "numero_cnh": "teste"},
        candidato, None, [],
    )
    assert not valido
    assert nivel == "erro"
    assert "candidato titular" in motivo


def test_permite_primeira_identidade_em_cadastro_provisorio():
    candidato = SimpleNamespace(nome_completo="Candidato (teste)", cpf=None)
    valido, _, _, _ = validar_documento_no_upload(
        "CNH", {"nome": "Pessoa Teste", "cpf": "12345678900", "numero_cnh": "teste"},
        candidato, None, [],
    )
    assert valido


def test_cpf_formatado_do_titular_confere(candidato):
    valido, _, _, _ = validar_documento_no_upload(
        "CNH", {"nome": "Gabriel Mendes", "cpf": "12345678900", "numero_cnh": "teste"},
        candidato, None, [],
    )
    assert valido


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
        "cpf": None,
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

