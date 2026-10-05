import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from app.config import Settings


def config(**overrides):
    values = dict(app_env="homologation", jwt_secret_key="ficticio" * 8,
                  encryption_key=Fernet.generate_key().decode(),
                  cors_origins=["https://grupo.example.invalid"], smtp_enabled=False)
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("secret", ["troque-essa-chave-no-.env", "curta"])
def test_homologacao_rejeita_jwt_padrao(secret):
    with pytest.raises(ValidationError, match="jwt_secret_key"):
        config(jwt_secret_key=secret)


def test_homologacao_rejeita_chave_criptografia_invalida():
    with pytest.raises(ValidationError, match="encryption_key"):
        config(encryption_key="segredo-invalido")


@pytest.mark.parametrize("origins", [[], ["*"], ["http://localhost:5173"],
                                      ["https://localhost"], ["https://grupo.invalid/caminho"]])
def test_homologacao_rejeita_cors_local_ou_curinga(origins):
    with pytest.raises(ValidationError, match="cors_origins"):
        config(cors_origins=origins)


def test_erro_configuracao_nao_expoe_segredos():
    with pytest.raises(ValidationError) as exc:
        config(jwt_secret_key="segredo-nao-exibir", database_url="postgresql://u:nao-exibir@host/db")
    assert "segredo-nao-exibir" not in str(exc.value)
    assert "postgresql://" not in str(exc.value)


def test_homologacao_valida_e_desenvolvimento_local():
    assert config().app_env == "homologation"
    assert Settings(_env_file=None, app_env="development", jwt_secret_key="curta").app_env == "development"


def test_smtp_desativado_nao_acessa_rede(monkeypatch):
    from app.services import email_service
    monkeypatch.setattr(email_service.settings, "smtp_enabled", False, raising=False)
    monkeypatch.setattr(email_service.settings, "smtp_username", "teste")
    monkeypatch.setattr(email_service.settings, "smtp_password", "teste")
    def network_forbidden(*args, **kwargs):
        raise AssertionError("SMTP foi acessado")
    monkeypatch.setattr(email_service.smtplib, "SMTP", network_forbidden)
    # Erros SMTP são capturados pelo serviço: logger torna a tentativa observável.
    monkeypatch.setattr(email_service.logger, "error", network_forbidden)
    email_service.enviar_email_boas_vindas("ficticio@example.invalid", "Teste", "teste")
