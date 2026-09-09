"""Testes do endpoint de leitura de identidade para familiares."""
from io import BytesIO
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

# Importar a rota não deve inicializar/refletir o banco durante um teste unitário.
db_fake = types.ModuleType("app.db")
db_fake.get_db = lambda: None
sys.modules.setdefault("app.db", db_fake)

from app.routes import inscricoes as inscricoes_router


class BancoFake:
    def __init__(self, inscricao):
        self.inscricao = inscricao

    def get(self, modelo, identificador):
        return self.inscricao


def upload(nome="documento.jpg", conteudo=b"imagem"):
    return UploadFile(file=BytesIO(conteudo), filename=nome)


@pytest.mark.asyncio
async def test_extrai_identidade_de_familiar_com_tipo_e_cpf(monkeypatch):
    inscricao = SimpleNamespace(id=10, candidato_id=7)
    usuario = SimpleNamespace(id=7)
    chamadas = []

    monkeypatch.setattr(
        inscricoes_router,
        "preparar_para_ia_multimodal",
        lambda conteudo, nome, mime: (conteudo, mime),
    )

    def extrair(conteudo, mime, categoria):
        chamadas.append(categoria)
        return {"nome": "Maria Oliveira", "cpf": "123.456.789-00", "tipo_documento": "CNH"}

    monkeypatch.setattr(inscricoes_router, "extrair_dados_documento", extrair)

    resposta = await inscricoes_router.extrair_documento_membro(
        10, upload(), BancoFake(inscricao), usuario
    )

    assert resposta == {
        "nome": "Maria Oliveira",
        "cpf": "123.456.789-00",
        "tipo_detectado": "CNH",
    }
    assert chamadas == ["IDENTIDADE_FAMILIAR"]


@pytest.mark.asyncio
async def test_extracao_rejeita_arquivo_vazio():
    inscricao = SimpleNamespace(id=10, candidato_id=7)
    usuario = SimpleNamespace(id=7)

    with pytest.raises(HTTPException) as erro:
        await inscricoes_router.extrair_documento_membro(
            10, upload(conteudo=b""), BancoFake(inscricao), usuario
        )

    assert erro.value.status_code == 400


@pytest.mark.asyncio
async def test_extracao_bloqueia_inscricao_de_outro_candidato():
    inscricao = SimpleNamespace(id=10, candidato_id=99)
    usuario = SimpleNamespace(id=7)

    with pytest.raises(HTTPException) as erro:
        await inscricoes_router.extrair_documento_membro(
            10, upload(), BancoFake(inscricao), usuario
        )

    assert erro.value.status_code == 403
