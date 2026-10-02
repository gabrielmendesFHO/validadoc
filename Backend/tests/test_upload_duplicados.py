from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.models import DocumentosSolicitados, Inscricoes, MembrosFamilia, StatusJornada
from app.routes import documentos


async def _enviar(
    monkeypatch, anteriores, conteudo=b"mesmo arquivo", solicitado_id=2,
    membro_id=None, descriptografar_fn=None, membro_inscricao_id=10,
    membro_existe=True,
):
    db = MagicMock()
    inscricao = SimpleNamespace(
        id=10,
        candidato_id=20,
        processo_id=30,
        status_funil=StatusJornada.DOCS_PENDENTES,
    )
    solicitado = SimpleNamespace(id=solicitado_id, processo_id=30, nome_documento="RESIDENCIA")
    def obter(modelo, _id):
        if modelo is Inscricoes:
            return inscricao
        if modelo is DocumentosSolicitados:
            return solicitado
        if modelo is MembrosFamilia and membro_existe:
            return SimpleNamespace(id=_id, inscricao_id=membro_inscricao_id)
        return None

    db.get.side_effect = obter
    db.query.return_value.join.return_value.filter.return_value.all.return_value = anteriores
    monkeypatch.setattr(documentos, "descriptografar", descriptografar_fn or (lambda valor: valor))
    monkeypatch.setattr(documentos, "criptografar", lambda valor: valor)
    monkeypatch.setattr(
        documentos, "preparar_para_ia_multimodal", lambda valor, _nome, mime: (valor, mime)
    )
    usuario = SimpleNamespace(id=20, perfil="CANDIDATO")
    arquivo = UploadFile(file=BytesIO(conteudo), filename="conta.pdf")
    resultado = await documentos.upload_documento(
        background_tasks=BackgroundTasks(),
        inscricao_id=10,
        solicitado_id=solicitado_id,
        membro_id=membro_id,
        file=arquivo,
        db=db,
        usuario=usuario,
    )
    return resultado, db


def _anterior(conteudo=b"mesmo arquivo", solicitado_id=1, membro_id=None):
    return SimpleNamespace(
        documento=SimpleNamespace(solicitado_id=solicitado_id, membro_id=membro_id),
        tamanho_bytes=len(conteudo),
        conteudo_criptografado=conteudo,
    )


@pytest.mark.asyncio
async def test_rejeita_arquivo_igual_em_outra_categoria_do_titular(monkeypatch):
    with pytest.raises(HTTPException) as erro:
        await _enviar(monkeypatch, [_anterior()])
    assert erro.value.status_code == 422
    assert "Arquivo duplicado" in erro.value.detail


@pytest.mark.asyncio
async def test_rejeita_arquivo_igual_entre_titular_e_familiar(monkeypatch):
    with pytest.raises(HTTPException) as erro:
        await _enviar(monkeypatch, [_anterior(solicitado_id=2)], membro_id=5)
    assert erro.value.status_code == 422


@pytest.mark.asyncio
async def test_permite_reenvio_no_mesmo_destino(monkeypatch):
    resultado, db = await _enviar(monkeypatch, [_anterior(solicitado_id=2)])
    assert resultado["status"] == "PROCESSANDO_IA"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_permite_arquivo_diferente_em_outra_categoria(monkeypatch):
    resultado, db = await _enviar(monkeypatch, [_anterior(conteudo=b"outro arquivo")])
    assert resultado["status"] == "PROCESSANDO_IA"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_falha_de_descriptografia_nao_e_ignorada(monkeypatch):
    def falhar(_valor):
        raise ValueError("dado corrompido")

    with pytest.raises(HTTPException) as erro:
        await _enviar(monkeypatch, [_anterior()], descriptografar_fn=falhar)
    assert erro.value.status_code == 503


@pytest.mark.asyncio
async def test_rejeita_membro_inexistente_antes_de_persistir(monkeypatch):
    with pytest.raises(HTTPException) as erro:
        await _enviar(monkeypatch, [], membro_id=5, membro_existe=False)
    assert erro.value.status_code == 400
    assert "membro_id inválido" in erro.value.detail


@pytest.mark.asyncio
async def test_rejeita_membro_de_outra_inscricao_antes_de_persistir(monkeypatch):
    with pytest.raises(HTTPException) as erro:
        await _enviar(monkeypatch, [], membro_id=5, membro_inscricao_id=99)
    assert erro.value.status_code == 400
    assert "membro_id inválido" in erro.value.detail
