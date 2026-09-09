"""Testes da auditoria cruzada de filiação — Fase 6.

Cobre os 3 cenários principais:
1. Nome do membro bate com o RG do candidato → sem inconsistência de filiação.
2. Nome do membro NÃO bate com o RG do candidato → inconsistência registrada.
3. Membro com parentesco não-progenitor (Irmão) → sem restrição de nome.
"""
import pytest
from types import SimpleNamespace

from app.services.regras_negocio import auditar_inscricao


def criar_documento(categoria, dados, status="CONCLUIDO"):
    return (categoria, dados, status, None)


@pytest.fixture
def candidato():
    return SimpleNamespace(nome_completo="João da Silva", cpf="111.111.111-11")


@pytest.fixture
def processo():
    return SimpleNamespace(renda_per_capita_limite=5000)


@pytest.fixture
def docs_candidato_com_rg():
    """Candidato com RG que registra nome_mae = 'Maria Oliveira' e nome_pai = 'Carlos da Silva'."""
    return [
        criar_documento("RG", {
            "nome": "João da Silva",
            "cpf": "11111111111",
            "nome_mae": "Maria Oliveira",
            "nome_pai": "Carlos da Silva",
            "legibilidade": 95,
            "documento_integro": True,
        }),
        criar_documento("HOLERITE", {
            "data_emissao": "01/08/2026",
            "renda_bruta": 2000,
            "renda_liquida": 1700,
            "legibilidade": 95,
            "documento_integro": True,
        }),
    ]


def test_mae_nome_coincide_sem_inconsistencia(candidato, docs_candidato_com_rg, processo):
    """Nome do membro registrado como Mãe bate com nome_mae do RG → sem inconsistência de filiação."""
    mae = SimpleNamespace(id=1, nome_completo="Maria Oliveira", parentesco="Mãe", renda_declarada=0)

    resultado = auditar_inscricao(
        candidato,
        docs_candidato_com_rg,
        [mae],
        {1: [criar_documento("HOLERITE", {"data_emissao": "01/08/2026", "renda_bruta": 1000, "renda_liquida": 900, "legibilidade": 90, "documento_integro": True})]},
        processo,
    )

    # Nenhuma inconsistência de filiação deve aparecer
    inconsistencias_filiacao = [i for i in resultado.inconsistencias if "filia" in i.lower() or "mãe" in i.lower() or "diverge" in i.lower()]
    assert inconsistencias_filiacao == [], f"Não esperava inconsistência de filiação, mas encontrou: {inconsistencias_filiacao}"


def test_mae_nome_diverge_gera_inconsistencia(candidato, docs_candidato_com_rg, processo):
    """Nome do membro registrado como Mãe diverge do nome_mae do RG → inconsistência detectada."""
    mae_errada = SimpleNamespace(id=2, nome_completo="Ana Paula Souza", parentesco="Mãe", renda_declarada=0)

    resultado = auditar_inscricao(
        candidato,
        docs_candidato_com_rg,
        [mae_errada],
        {2: []},
        processo,
    )

    inconsistencias_filiacao = [i for i in resultado.inconsistencias if "diverge" in i.lower() and "mãe" in i.lower()]
    assert len(inconsistencias_filiacao) == 1, f"Esperava 1 inconsistência de filiação da mãe, obteve: {resultado.inconsistencias}"
    assert "MARIA OLIVEIRA" in inconsistencias_filiacao[0].upper()


def test_pai_nome_diverge_gera_inconsistencia(candidato, docs_candidato_com_rg, processo):
    """Nome do membro registrado como Pai diverge do nome_pai do RG → inconsistência detectada."""
    pai_errado = SimpleNamespace(id=3, nome_completo="Roberto Lima", parentesco="Pai", renda_declarada=0)

    resultado = auditar_inscricao(
        candidato,
        docs_candidato_com_rg,
        [pai_errado],
        {3: []},
        processo,
    )

    inconsistencias_filiacao = [i for i in resultado.inconsistencias if "diverge" in i.lower() and "pai" in i.lower()]
    assert len(inconsistencias_filiacao) == 1, f"Esperava 1 inconsistência de filiação do pai, obteve: {resultado.inconsistencias}"
    assert "Carlos da Silva" in inconsistencias_filiacao[0]


def test_irmao_sem_restricao_filiacao(candidato, docs_candidato_com_rg, processo):
    """Membro com parentesco 'Irmão' não sofre restrição de nome de filiação."""
    irmao = SimpleNamespace(id=4, nome_completo="Pedro da Silva", parentesco="Irmão", renda_declarada=0)

    resultado = auditar_inscricao(
        candidato,
        docs_candidato_com_rg,
        [irmao],
        {4: []},
        processo,
    )

    inconsistencias_filiacao = [i for i in resultado.inconsistencias if "diverge" in i.lower()]
    assert inconsistencias_filiacao == [], f"Irmão não deveria ter restrição de filiação, mas obteve: {inconsistencias_filiacao}"


def test_mae_parentesco_variante_mae_sem_acento(candidato, docs_candidato_com_rg, processo):
    """Variante 'Mae' (sem acento) também é reconhecida como progenitora."""
    mae = SimpleNamespace(id=5, nome_completo="Maria Oliveira", parentesco="Mae", renda_declarada=0)

    resultado = auditar_inscricao(
        candidato,
        docs_candidato_com_rg,
        [mae],
        {5: []},
        processo,
    )

    inconsistencias_filiacao = [i for i in resultado.inconsistencias if "diverge" in i.lower()]
    assert inconsistencias_filiacao == [], f"Não deveria ter inconsistência de filiação para 'Mae' correto: {inconsistencias_filiacao}"
