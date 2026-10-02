from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import gemini_service as service


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code


def client_com_respostas(monkeypatch, respostas):
    generate = Mock(side_effect=respostas)
    monkeypatch.setattr(service, "_get_client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(service.settings, "gemini_model", "principal")
    monkeypatch.setattr(service.settings, "gemini_fallback_model", "alternativo")
    return generate


def test_sobrecarga_usa_modelo_alternativo(monkeypatch):
    generate = client_com_respostas(monkeypatch, [ProviderError(503), SimpleNamespace(text='{"nome":"Teste"}')])
    assert service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")["nome"] == "Teste"
    assert [c.kwargs["model"] for c in generate.call_args_list] == ["principal", "alternativo"]


def test_erro_de_modelo_nao_oculta_cota(monkeypatch):
    client_com_respostas(monkeypatch, [ProviderError(429), ProviderError(404)])
    with pytest.raises(service.GeminiExtractionError, match="cota"):
        service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")


def test_erro_de_modelo_nao_oculta_sobrecarga(monkeypatch):
    client_com_respostas(monkeypatch, [ProviderError(503), ProviderError(404)])
    with pytest.raises(service.GeminiExtractionError, match="sobrecarregada"):
        service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")


def test_chave_recusada_nao_repete_chamadas(monkeypatch):
    generate = client_com_respostas(monkeypatch, [ProviderError(403)])
    with pytest.raises(service.GeminiExtractionError, match="autenticação"):
        service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")
    assert generate.call_count == 1


def test_json_invalido_tenta_resposta_sem_schema(monkeypatch):
    generate = client_com_respostas(monkeypatch, [SimpleNamespace(text="inválido"), SimpleNamespace(text='{"nome":"Teste"}')])
    assert service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")["nome"] == "Teste"
    assert generate.call_args_list[1].kwargs["config"].response_schema is None


def test_cpf_invalido_repete_leitura_sem_gravar_valor(monkeypatch):
    generate = client_com_respostas(monkeypatch, [
        SimpleNamespace(text='{"cpf":"111.111.111-11"}'),
        SimpleNamespace(text='{"cpf":"111.444.777-35"}'),
    ])
    assert service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")["cpf"] == "111.444.777-35"
    assert generate.call_count == 2


def test_cpf_invalido_em_todos_modelos_bloqueia_extracao(monkeypatch):
    client_com_respostas(monkeypatch, [SimpleNamespace(text='{"cpf":"12345678900"}')] * 4)
    with pytest.raises(service.GeminiExtractionError, match="CPF válido"):
        service.extrair_dados_documento(b"teste", "image/jpeg", "CNH")


@pytest.mark.parametrize('cpf', ['11144477735', '111.444.777-35'])
def test_cpf_valido_com_e_sem_formatacao(cpf):
    assert service.cpf_extraido_valido(cpf)


@pytest.mark.parametrize('cpf', ['11111111111', '11144477734', '123', ''])
def test_cpf_com_digitos_incorretos(cpf):
    assert not service.cpf_extraido_valido(cpf)
