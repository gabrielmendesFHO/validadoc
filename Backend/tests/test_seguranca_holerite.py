from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.regras_negocio import auditar_inscricao
from app.services.validacao_documental import validar_documento_no_upload


def documentos(holerite):
    return [
        ("CNH", {"nome": "Pessoa A", "cpf": "12345678900"}, "CONCLUIDO", None),
        ("HOLERITE", {"nome": "Pessoa A", "cpf": "12345678900",
                      "data_emissao": datetime.now().strftime("%d/%m/%Y"),
                      "renda_bruta": 1000, "renda_liquida": 900, **holerite}, "CONCLUIDO", None),
    ]


@pytest.mark.parametrize("alteracao", [
    {"cpf": "98765432100"},
    {"nome": "Pessoa B", "cpf": None},
    {"nome": None, "cpf": None},
])
def test_holerite_sem_titularidade_confirmada_exige_revisao(alteracao):
    resultado = auditar_inscricao(
        SimpleNamespace(nome_completo="Pessoa A", cpf="12345678900"),
        documentos(alteracao), [], {}, SimpleNamespace(renda_per_capita_limite=2000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("HOLERITE" in item for item in resultado.inconsistencias)


@pytest.mark.parametrize("categoria", ["RESIDENCIA", "HOLERITE"])
def test_comprovante_com_emissao_futura_exige_revisao(categoria):
    docs = documentos({})
    futuro = (datetime.now() + timedelta(days=365)).strftime("%d/%m/%Y")
    if categoria == "HOLERITE":
        docs = documentos({"data_emissao": futuro})
    else:
        docs.append((categoria, {"data_emissao": futuro}, "CONCLUIDO", None))
    resultado = auditar_inscricao(
        SimpleNamespace(nome_completo="Pessoa A", cpf="12345678900"),
        docs, [], {}, SimpleNamespace(renda_per_capita_limite=2000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("futura" in item for item in resultado.inconsistencias)


@pytest.mark.parametrize("membro", [None, SimpleNamespace(nome_completo="Pessoa B", cpf="98765432100")])
def test_upload_holerite_de_terceiro_e_rejeitado(membro):
    valido, motivo, nivel, _ = validar_documento_no_upload(
        "HOLERITE", {"nome": "Terceiro", "cpf": "11122233344", "renda_bruta": 1000},
        SimpleNamespace(nome_completo="Pessoa A", cpf="12345678900"), membro, [],
    )
    assert not valido
    assert nivel == "erro"
    assert "holerite" in motivo.lower()


def test_upload_comprovante_futuro_exibe_aviso():
    valido, _, nivel, mensagem = validar_documento_no_upload(
        "RESIDENCIA", {"data_emissao": (datetime.now() + timedelta(days=365)).strftime("%d/%m/%Y")},
        SimpleNamespace(nome_completo="Pessoa A", cpf="12345678900"), None, [],
    )
    assert valido
    assert nivel == "aviso"
    assert "futura" in mensagem
