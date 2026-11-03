import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from app.services import gemini_service as service
from app.services.regras_negocio import auditar_inscricao
from app.services.validacao_documental import validar_documento_no_upload


def test_cpf_invalido_no_holerite_preserva_renda_e_exige_revisao(monkeypatch):
    resposta = {"nome": "Pessoa A", "cpf": "123456789", "renda_bruta": 1000,
                "renda_liquida": 900, "data_emissao": datetime.now().strftime("%d/%m/%Y")}
    generate = Mock(return_value=SimpleNamespace(text=json.dumps(resposta)))
    monkeypatch.setattr(service, "_get_client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    dados = service.extrair_dados_documento(b"teste", "image/jpeg", "HOLERITE")
    assert dados["renda_bruta"] == 1000
    assert dados["cpf"] is None
    assert dados["cpf_nao_confirmado"] is True
    pessoa = SimpleNamespace(nome_completo="Pessoa A", cpf="11144477735")
    valido, _, nivel, feedback = validar_documento_no_upload("HOLERITE", dados, pessoa, None, [])
    assert valido and nivel == "aviso"
    assert "CPF" in feedback
    resultado = auditar_inscricao(pessoa, [
        ("CNH", {"nome": "Pessoa A", "cpf": "11144477735"}, "CONCLUIDO", None),
        ("HOLERITE", dados, "CONCLUIDO", None),
    ], [], {}, SimpleNamespace(renda_per_capita_limite=2000))
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("CPF" in item and "HOLERITE" in item for item in resultado.inconsistencias)
