import pytest
from types import SimpleNamespace
from datetime import datetime

from app.services.gemini_service import avaliar_possivel_divergencia
from app.services.regras_negocio import auditar_inscricao


def criar_documento(categoria, dados):
    return (categoria, dados, "CONCLUIDO", None)


@pytest.fixture
def candidato_padrao():
    return SimpleNamespace(nome_completo="Maria da Silva", cpf="123.456.789-00")


@pytest.fixture
def processo_padrao():
    return SimpleNamespace(renda_per_capita_limite=1412)


@pytest.fixture
def documentos_padrao():
    data_recente = datetime.now().strftime("%d/%m/%Y")
    return [
        criar_documento("RG", {"nome": "Maria da Silva", "cpf": "12345678900", "legibilidade": 95, "documento_integro": True}),
        criar_documento("RESIDENCIA", {"data_emissao": data_recente, "legibilidade": 95, "documento_integro": True}),
        criar_documento("HOLERITE", {"data_emissao": data_recente, "renda_bruta": 1800, "renda_liquida": 1500, "legibilidade": 95, "documento_integro": True}),
    ]


def test_candidato_sem_membro_fica_apto(candidato_padrao, documentos_padrao):
    """Candidato sem membros familiares, renda abaixo do teto → APTO."""
    processo = SimpleNamespace(renda_per_capita_limite=2000)
    resultado = auditar_inscricao(
        candidato_padrao,
        documentos_padrao,
        [],   # sem membros
        {},
        processo,
    )

    assert resultado.status_geral == "APTO"
    assert resultado.renda_per_capita == 1800.0


def test_membro_sem_documentos_gera_revisao(candidato_padrao, documentos_padrao, processo_padrao):
    """Membro cadastrado sem nenhum documento enviado → REVISAO_MANUAL por falta de identidade."""
    membro = SimpleNamespace(id=1, renda_declarada=500, nome_completo="José Silva")
    resultado = auditar_inscricao(
        candidato_padrao,
        documentos_padrao,
        [membro],
        {membro.id: []},  # membro sem documentos
        processo_padrao,
    )

    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("José Silva" in item for item in resultado.inconsistencias)


def test_renda_acima_do_teto(candidato_padrao, documentos_padrao):
    processo = SimpleNamespace(renda_per_capita_limite=1000)
    resultado = auditar_inscricao(
        candidato_padrao,
        documentos_padrao,
        [],
        {},  # sem documentos de membros
        processo,
    )

    assert resultado.status_geral == "NAO_APTO"
    assert resultado.renda_per_capita == 1800.0


def test_renda_exatamente_no_teto_continua_apta(candidato_padrao, documentos_padrao):
    resultado = auditar_inscricao(
        candidato_padrao, documentos_padrao, [], {},
        SimpleNamespace(renda_per_capita_limite=1800),
    )
    assert resultado.status_geral == "APTO"
    assert resultado.renda_per_capita == 1800.0


def test_cpf_divergente_do_familiar_exige_revisao(candidato_padrao, documentos_padrao):
    membro = SimpleNamespace(id=7, nome_completo="João da Silva", cpf="111.222.333-44", renda_declarada=0)
    data_recente = datetime.now().strftime("%d/%m/%Y")
    documentos_membro = [
        criar_documento("RG", {"nome": "João da Silva", "cpf": "99988877766", "legibilidade": 95, "documento_integro": True}),
        criar_documento("HOLERITE", {"data_emissao": data_recente, "renda_bruta": 1000, "renda_liquida": 900}),
    ]
    resultado = auditar_inscricao(
        candidato_padrao, documentos_padrao, [membro], {membro.id: documentos_membro},
        SimpleNamespace(renda_per_capita_limite=5000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("João da Silva" in item and "CPF do documento diverge" in item for item in resultado.inconsistencias)


def test_cpf_ausente_no_documento_nao_confirma_identidade(candidato_padrao, documentos_padrao):
    documentos = list(documentos_padrao)
    documentos[0] = criar_documento("RG", {"nome": "Maria da Silva", "legibilidade": 95, "documento_integro": True})
    resultado = auditar_inscricao(
        candidato_padrao, documentos, [], {},
        SimpleNamespace(renda_per_capita_limite=5000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("CPF não identificado" in item for item in resultado.inconsistencias)


def test_familiar_sem_cpf_cadastrado_nao_e_aprovado_automaticamente(candidato_padrao, documentos_padrao):
    membro = SimpleNamespace(id=7, nome_completo="João da Silva", cpf=None, renda_declarada=0)
    data_recente = datetime.now().strftime("%d/%m/%Y")
    documentos_membro = [
        criar_documento("RG", {"nome": "João da Silva", "cpf": "11122233344", "legibilidade": 95, "documento_integro": True}),
        criar_documento("HOLERITE", {"data_emissao": data_recente, "renda_bruta": 1000, "renda_liquida": 900}),
    ]
    resultado = auditar_inscricao(
        candidato_padrao, documentos_padrao, [membro], {membro.id: documentos_membro},
        SimpleNamespace(renda_per_capita_limite=5000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("CPF não cadastrado" in item for item in resultado.inconsistencias)


def test_divergencia_de_identidade_exige_revisao_mesmo_acima_do_teto(candidato_padrao, documentos_padrao):
    documentos = list(documentos_padrao)
    documentos[0] = criar_documento(
        "RG",
        {"nome": "Maria da Silva", "cpf": "99999999999", "legibilidade": 95, "documento_integro": True},
    )
    resultado = auditar_inscricao(
        candidato_padrao,
        documentos,
        [],
        {},
        SimpleNamespace(renda_per_capita_limite=1000),
    )
    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("CPF" in item for item in resultado.inconsistencias)
    assert any("Renda per capita" in item for item in resultado.inconsistencias)


def test_renda_liquida_maior_que_bruta_exige_revisao(candidato_padrao, documentos_padrao):
    documentos = list(documentos_padrao)
    documentos[2] = criar_documento(
        "HOLERITE",
        {"data_emissao": "01/08/2026", "renda_bruta": 1500, "renda_liquida": 1800, "legibilidade": 95, "documento_integro": True},
    )

    resultado = auditar_inscricao(
        candidato_padrao,
        documentos,
        [],
        {},  # sem documentos de membros
        SimpleNamespace(renda_per_capita_limite=5000),
    )

    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("Renda líquida" in item for item in resultado.inconsistencias)


def test_cpf_divergente_exige_revisao(candidato_padrao, documentos_padrao):
    documentos = list(documentos_padrao)
    documentos[0] = criar_documento(
        "RG",
        {"nome": "Maria da Silva", "cpf": "99999999999", "legibilidade": 95, "documento_integro": True},
    )

    resultado = auditar_inscricao(
        candidato_padrao,
        documentos,
        [],
        {},  # sem documentos de membros
        SimpleNamespace(renda_per_capita_limite=5000),
    )

    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("CPF" in item for item in resultado.inconsistencias)


def test_documento_vencido_exige_revisao(candidato_padrao, documentos_padrao):
    documentos = list(documentos_padrao)
    documentos[1] = criar_documento(
        "RESIDENCIA",
        {"data_emissao": "01/01/2026", "legibilidade": 95, "documento_integro": True},
    )

    resultado = auditar_inscricao(
        candidato_padrao,
        documentos,
        [],
        {},  # sem documentos de membros
        SimpleNamespace(renda_per_capita_limite=5000),
    )

    assert resultado.status_geral == "REVISAO_MANUAL"
    assert any("RESIDENCIA" in item for item in resultado.inconsistencias)


@pytest.mark.parametrize("dados, categoria, esperado", [
    ({"legibilidade": 95, "documento_integro": True, "renda_bruta": 1800}, "HOLERITE", True),
    ({"nome": "Maria", "cpf": "123", "renda_bruta": 1800, "renda_liquida": 1500}, "HOLERITE", False),
])
def test_documento_incompativel_e_detectado(dados, categoria, esperado):
    assert avaliar_possivel_divergencia(dados, categoria) is esperado


# === MATRIZ DE TESTES FORMAL (Base para a Pendência #3 do TCC) ===
# Cenários de Qualidade (exemplo): A = Perfeito, B = Legível mas amassado, C = Baixa qualidade/Incompleto
@pytest.mark.parametrize(
    "id_documento_real, cenario_qualidade, categoria, dados_mockados, resultado_esperado_divergencia",
    [
        ("1_4_20260810124241_RG frente _1 (1).jpg", "A", "RG", {
            "nome": "Maria", "data_nascimento": "01/01/2000", "nome_pai": "Jose", "nome_mae": "Ana", "legibilidade": 98, "documento_integro": True
        }, False),
        ("3_2_20260810135930_comprovante de residência.jpg", "A", "RESIDENCIA", {
            "nome_titular": "Maria", "endereco": "Rua X", "data_emissao": "10/08/2026", "legibilidade": 95, "documento_integro": True
        }, False),
        # Adicionar aqui os demais documentos mapeados na seção 3.8.1 do TCC.
    ]
)
def test_matriz_qualidade_documentos(id_documento_real, cenario_qualidade, categoria, dados_mockados, resultado_esperado_divergencia):
    """
    Testes estruturados exigidos pela Pendência #3 do TCC.
    Este teste simula a avaliação de inconsistências puras do modelo de dados retornados pela IA 
    para diferentes cenários de qualidade visual dos documentos originais.
    """
    divergente = avaliar_possivel_divergencia(dados_mockados, categoria)
    assert divergente is resultado_esperado_divergencia
