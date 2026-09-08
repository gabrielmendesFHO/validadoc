import pytest
from cryptography.fernet import Fernet

from app.services.crypto import (
    _get_fernet,
    criptografar,
    descriptografar,
    CriptografiaNaoConfiguradaError,
)
from app.config import settings

# Chave válida gerada para uso nos testes
CHAVE_TESTE = Fernet.generate_key().decode()

@pytest.fixture(autouse=True)
def reset_fernet_cache():
    """Garante que o cache do get_fernet é limpo antes e depois de cada teste."""
    _get_fernet.cache_clear()
    yield
    _get_fernet.cache_clear()

def test_fernet_lanca_erro_se_chave_nao_configurada(monkeypatch):
    """Garante que o sistema avisa caso falte a ENCRYPTION_KEY no .env."""
    monkeypatch.setattr(settings, "encryption_key", "")
    
    with pytest.raises(CriptografiaNaoConfiguradaError) as exc_info:
        _get_fernet()
        
    assert "ENCRYPTION_KEY não configurada" in str(exc_info.value)

def test_criptografar_e_descriptografar_sucesso(monkeypatch):
    """Testa o fluxo feliz: roundtrip da criptografia."""
    monkeypatch.setattr(settings, "encryption_key", CHAVE_TESTE)
    
    texto_original = b"Conteudo confidencial do documento"
    
    criptografado = criptografar(texto_original)
    
    assert criptografado != texto_original
    assert type(criptografado) is bytes
    
    descriptografado = descriptografar(criptografado)
    
    assert descriptografado == texto_original

def test_descriptografar_dado_invalido_ou_corrompido(monkeypatch):
    """Garante que dados corrompidos levantem ValueError mapeado, escondendo detalhes."""
    monkeypatch.setattr(settings, "encryption_key", CHAVE_TESTE)
    
    dado_invalido = b"dado.corrompido.ou.falso"
    
    with pytest.raises(ValueError) as exc_info:
        descriptografar(dado_invalido)
        
    assert "Não foi possível descriptografar o arquivo" in str(exc_info.value)

def test_descriptografar_com_chave_errada_falha(monkeypatch):
    """Garante que tentar descriptografar com outra chave também levante ValueError."""
    # Criptografa com uma chave
    monkeypatch.setattr(settings, "encryption_key", CHAVE_TESTE)
    texto_original = b"Dado importante"
    criptografado = criptografar(texto_original)
    
    # Limpa o cache e simula o sistema operando com outra chave no .env
    _get_fernet.cache_clear()
    OUTRA_CHAVE = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "encryption_key", OUTRA_CHAVE)
    
    with pytest.raises(ValueError) as exc_info:
        descriptografar(criptografado)
        
    assert "Não foi possível descriptografar o arquivo" in str(exc_info.value)

