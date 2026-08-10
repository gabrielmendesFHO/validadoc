"""Integração com a API do Gemini para extração estruturada dos documentos.

Cada categoria de documento (igual ao `nome_documento` cadastrado em
`documentos_solicitados`: CNH, RG, RG_VERSO, RESIDENCIA, HOLERITE) tem um prompt e um
schema de resposta próprios — os campos relevantes mudam bastante entre um
RG e um holerite. Categorias sem schema específico caem no schema genérico
'OUTRO'.

Usa o SDK novo (`google-genai`), não o `google-generativeai` (deprecado desde
30/11/2025).
"""
from functools import lru_cache
from typing import Any, Dict
import json
import mimetypes
import re

from google import genai
from google.genai import types

from ..config import settings

_MIME_POR_EXTENSAO = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


class GeminiExtractionError(Exception):
    """Erro ao chamar a API do Gemini ou ao interpretar a resposta."""


def lado_documento_invalido(dados_extraidos: dict, categoria: str) -> bool:
    """Confere se o Gemini identificou o lado esperado do RG."""
    lados_esperados = {"RG": "frente", "RG_VERSO": "verso"}
    lado_esperado = lados_esperados.get(categoria.upper())
    if lado_esperado is None:
        return False

    lado_identificado = str(dados_extraidos.get("lado_documento") or "").strip().lower()
    return lado_identificado != lado_esperado


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    if not settings.gemini_api_key:
        raise GeminiExtractionError(
            "GEMINI_API_KEY não configurada. Copie .env.example para .env e "
            "preencha com sua chave do Google AI Studio."
        )
    return genai.Client(api_key=settings.gemini_api_key)


# Campos que pedimos em TODO documento, independente do tipo — servem de
# insumo direto pras regras de negócio da Fase 2 (revisão manual, etc.)
_CAMPOS_COMUNS: Dict[str, Any] = {
    "legibilidade": {
        "type": "INTEGER",
        "description": "Nota de 0 a 100 para a legibilidade geral do documento.",
    },
    "qualidade_imagem": {
        "type": "STRING",
        "description": "Avaliação curta da qualidade da imagem (iluminação, foco, resolução).",
    },
    "documento_integro": {
        "type": "BOOLEAN",
        "description": "Se o documento parece íntegro, sem rasuras, cortes ou sinais de adulteração.",
    },
}

_CAMPOS_CHAVE_POR_CATEGORIA = {
    "RG": ("nome", "data_nascimento", "nome_pai", "nome_mae"),
    "RG_VERSO": ("numero_rg", "cpf"),
    "CNH": ("nome", "numero_cnh", "cpf"),
    "RESIDENCIA": ("nome_titular", "endereco", "data_emissao"),
    "HOLERITE": ("nome", "cpf", "renda_bruta", "renda_liquida", "data_emissao"),
}

_INSTRUCAO_BASE = (
    "Você é um auditor documental. Analise a imagem do documento enviado e "
    "extraia SOMENTE os campos definidos no schema de resposta. Se um campo "
    "não estiver visível ou não existir nesse tipo de documento, retorne null "
    "para ele — nunca invente um valor. Preserve acentuação e maiúsculas/"
    "minúsculas como aparecem no documento. Datas sempre no formato DD/MM/AAAA."
)

_SCHEMAS_E_PROMPTS: Dict[str, Dict[str, Any]] = {
    "RG": {
        "prompt": _INSTRUCAO_BASE
        + " O documento é a frente do RG (Registro Geral / Carteira de Identidade) brasileiro. "
        + "A frente contém principalmente dados pessoais e de filiação. Extraia somente nome, data de nascimento, "
        + "nome do pai e nome da mãe visíveis na frente. NÃO extraia nem tente inferir CPF, número do RG, órgão "
        + "expedidor, UF ou data de expedição; esses campos pertencem ao verso. Se algum campo não estiver legível "
        + "ou não aparecer na imagem, retorne null, nunca invente dados.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome": {"type": "STRING"},
                "data_nascimento": {"type": "STRING"},
                "nome_pai": {"type": "STRING"},
                "nome_mae": {"type": "STRING"},
                "lado_documento": {"type": "STRING", "description": "Lado do documento: frente."},
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
    "RG_VERSO": {
        "prompt": _INSTRUCAO_BASE
        + " O documento é o verso do RG (Registro Geral / Carteira de Identidade) brasileiro. "
        + "Extraia somente número do RG, CPF, órgão expedidor, UF, data de expedição e informações de identificação "
        + "que estejam visíveis no verso. NÃO extraia nomes de pai ou mãe deste lado. Se um campo não estiver legível "
        + "ou não aparecer na imagem, retorne null, nunca invente dados.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "numero_rg": {"type": "STRING"},
                "cpf": {"type": "STRING"},
                "orgao_expedidor": {"type": "STRING"},
                "uf": {"type": "STRING"},
                "data_expedicao": {"type": "STRING"},
                "codigo_barras": {"type": "STRING"},
                "observacoes": {"type": "STRING"},
                "lado_documento": {"type": "STRING", "description": "Lado do documento: verso."},
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
    "CNH": {
        "prompt": _INSTRUCAO_BASE
        + " O documento é uma CNH (Carteira Nacional de Habilitação) brasileira, física ou digital.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome": {"type": "STRING"},
                "numero_cnh": {"type": "STRING"},
                "data_nascimento": {"type": "STRING"},
                "data_validade": {"type": "STRING"},
                "categorias": {"type": "ARRAY", "items": {"type": "STRING"}},
                "cpf": {"type": "STRING"},
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
    "RESIDENCIA": {
        "prompt": _INSTRUCAO_BASE
        + " O documento é um comprovante de residência (conta de água, luz, telefone ou similar).",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome_titular": {"type": "STRING"},
                "endereco": {"type": "STRING"},
                "cep": {"type": "STRING"},
                "data_emissao": {"type": "STRING"},
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
    "HOLERITE": {
        "prompt": _INSTRUCAO_BASE
        + (
            " O documento é um holerite/contracheque. Os valores monetários devem "
            "vir como número (ponto decimal, sem 'R$' e sem separador de milhar)."
        ),
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome": {"type": "STRING"},
                "cpf": {"type": "STRING"},
                "empresa": {"type": "STRING"},
                "competencia": {"type": "STRING", "description": "Mês/ano de referência, ex: 06/2026"},
                "renda_bruta": {"type": "NUMBER"},
                "renda_liquida": {"type": "NUMBER"},
                "data_emissao": {"type": "STRING"},
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
    "OUTRO": {
        "prompt": _INSTRUCAO_BASE
        + " O tipo exato do documento não está pré-definido — identifique o que for possível.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "tipo_documento_identificado": {"type": "STRING"},
                "dados_relevantes": {
                    "type": "STRING",
                    "description": "Resumo livre de outras informações relevantes encontradas. Se não houver dado claro, retorne null.",
                },
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro"],
        },
    },
}


def _mime_type(caminho_arquivo: str) -> str:
    caminho_lower = caminho_arquivo.lower()
    for ext, mime in _MIME_POR_EXTENSAO.items():
        if caminho_lower.endswith(ext):
            return mime
    tipo, _ = mimetypes.guess_type(caminho_arquivo)
    return tipo or "application/octet-stream"


def _parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Resposta vazia do Gemini.")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resposta do Gemini não é JSON válido: {exc}") from exc


def _filtrar_campos_resposta(dados: dict, schema: dict) -> dict:
    """Descarta campos que não pertencem ao contrato do documento."""
    propriedades = schema.get("properties", {})
    return {campo: dados.get(campo) for campo in propriedades if campo in dados}


def avaliar_possivel_divergencia(dados_extraidos: dict, categoria: str) -> bool:
    """Heurística simples: se metade ou mais dos campos-chave do tipo de
    documento (os campos obrigatórios específicos, sem contar legibilidade/
    qualidade_imagem/documento_integro) vieram nulos, é provável que o
    solicitado_id não bate com o arquivo enviado — ex.: holerite no card de RG."""
    categoria = categoria.upper()
    config_extracao = _SCHEMAS_E_PROMPTS.get(categoria, _SCHEMAS_E_PROMPTS["OUTRO"])
    campos_chave = _CAMPOS_CHAVE_POR_CATEGORIA.get(categoria, ())

    if not campos_chave:
        return False

    nulos = sum(
        1 for campo in campos_chave
        if dados_extraidos.get(campo) in (None, "", [])
    )
    return (nulos / len(campos_chave)) >= 0.5

def extrair_dados_documento(caminho_arquivo: str, categoria: str) -> dict:
    """Envia o documento pro Gemini e devolve os campos extraídos como dict.

    `categoria` deve bater com `documentos_solicitados.nome_documento`
    (CNH, RESIDENCIA, HOLERITE, RG, RG_VERSO). Categorias desconhecidas caem no
    schema genérico 'OUTRO'.

    Levanta GeminiExtractionError em qualquer falha (leitura do arquivo,
    chamada à API, resposta que não é JSON válido) — a rota decide o que
    fazer com isso (marcar status de erro, etc.), sem derrubar a aplicação.
    """
    config_extracao = _SCHEMAS_E_PROMPTS.get(categoria.upper(), _SCHEMAS_E_PROMPTS["OUTRO"])

    try:
        with open(caminho_arquivo, "rb") as f:
            dados_arquivo = f.read()
    except OSError as exc:
        raise GeminiExtractionError(f"Não foi possível ler o arquivo: {exc}") from exc

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                config_extracao["prompt"],
                types.Part.from_bytes(data=dados_arquivo, mime_type=_mime_type(caminho_arquivo)),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=config_extracao["schema"],
                temperature=0.1,
            ),
        )
        dados = _parse_json_response(response.text)
        return _filtrar_campos_resposta(dados, config_extracao["schema"])
    except GeminiExtractionError:
        raise
    except Exception as exc:  # falhas de rede, quota, autenticação etc.
        fallback_prompt = (
            config_extracao["prompt"]
            + " Responda SOMENTE em JSON válido, sem explicações e sem markdown. "
            + "Se não houver dado, use null."
        )
        try:
            response_fallback = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    fallback_prompt,
                    types.Part.from_bytes(data=dados_arquivo, mime_type=_mime_type(caminho_arquivo)),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            dados = _parse_json_response(response_fallback.text)
            return _filtrar_campos_resposta(dados, config_extracao["schema"])
        except Exception as fallback_exc:
            raise GeminiExtractionError(
                f"Falha na chamada à API do Gemini: {exc}. Fallback também falhou: {fallback_exc}"
            ) from fallback_exc
