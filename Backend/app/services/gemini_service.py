"""Integração com a API do Gemini para extração estruturada dos documentos.

Cada categoria de documento (igual ao `nome_documento` cadastrado em
`documentos_solicitados`: CNH, RG, RG_VERSO, RESIDENCIA, HOLERITE) tem um
prompt e um schema de resposta próprios. Categorias sem schema específico
caem no schema genérico 'OUTRO'.

Trabalha só com bytes em memória — nada de caminho de arquivo, já que os
documentos não tocam mais o disco (vão criptografados direto pro banco).

Usa o SDK novo (`google-genai`), não o `google-generativeai` (deprecado desde
30/11/2025).
"""
from functools import lru_cache
from typing import Any, Dict
import json
import logging
import re

from google import genai
from google.genai import types

from ..config import settings

logger = logging.getLogger(__name__)


class GeminiExtractionError(Exception):
    """Erro ao chamar a API do Gemini ou ao interpretar a resposta."""


class CpfExtractionError(ValueError):
    """O CPF retornado não passa na verificação de dígitos."""


def cpf_extraido_valido(valor: str) -> bool:
    cpf = re.sub(r"\D", "", str(valor))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if int(cpf[tamanho]) != digito:
            return False
    return True


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
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=settings.gemini_timeout_ms,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


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
    "IDENTIDADE_FAMILIAR": ("nome", "cpf", "tipo_documento"),
    "RESIDENCIA": ("nome_titular", "endereco", "data_emissao"),
    "HOLERITE": ("nome", "cpf", "renda_bruta", "renda_liquida", "data_emissao"),
}

_INSTRUCAO_BASE = (
    "Você é um auditor documental. Analise a imagem do documento enviado e "
    "extraia SOMENTE os campos definidos no schema de resposta. Se um campo "
    "não estiver visível ou não existir nesse tipo de documento, retorne null "
    "para ele — nunca invente um valor. Preserve acentuação e maiúsculas/"
    "minúsculas como aparecem no documento. Datas sempre no formato DD/MM/AAAA."
    " O CPF tem 11 dígitos. Copie somente o campo explicitamente identificado como CPF "
    "(campo 4d da CNH). Não confunda CPF com número de registro, RG, QR-code ou MRZ. "
    "Confira cada dígito na imagem, sem corrigir ou inventar números."
)

_SCHEMAS_E_PROMPTS: Dict[str, Dict[str, Any]] = {
    "RG": {
        "prompt": _INSTRUCAO_BASE
        + " Este upload deveria ser a FRENTE do RG brasileiro, mas CONFIRME isso observando a imagem "
        + "antes de extrair qualquer dado — não presuma pelo que foi dito aqui. Preencha 'lado_documento' "
        + "com o que você realmente identificou ('frente' ou 'verso'). Só preencha nome, data_nascimento, "
        + "nome_pai e nome_mae se a imagem de fato mostrar a frente; caso contrário, retorne null para "
        + "esses campos, mesmo que o documento pareça ser um RG.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome": {"type": "STRING"},
                "data_nascimento": {"type": "STRING"},
                "nome_pai": {"type": "STRING"},
                "nome_mae": {"type": "STRING"},
                "lado_documento": {
                    "type": "STRING",
                    "description": "Lado do documento identificado na imagem observada: 'frente' ou 'verso'.",
                },
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro", "lado_documento"],
        },
    },
    "RG_VERSO": {
        "prompt": _INSTRUCAO_BASE
        + " Este upload deveria ser o VERSO do RG brasileiro, mas CONFIRME isso observando a imagem "
        + "antes de extrair qualquer dado — não presuma pelo que foi dito aqui. Preencha 'lado_documento' "
        + "com o que você realmente identificou ('frente' ou 'verso'). Só preencha numero_rg, cpf, "
        + "orgao_expedidor, uf e data_expedicao se a imagem de fato mostrar o verso; caso contrário, "
        + "retorne null para esses campos.",
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
                "lado_documento": {
                    "type": "STRING",
                    "description": "Lado do documento identificado na imagem observada: 'frente' ou 'verso'.",
                },
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro", "lado_documento"],
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
    "IDENTIDADE_FAMILIAR": {
        "prompt": _INSTRUCAO_BASE
        + " Analise uma identidade brasileira enviada para cadastro de familiar. "
        + "Classifique obrigatoriamente o documento como 'RG' ou 'CNH' em tipo_documento. "
        + "Extraia nome e CPF quando estiverem visíveis; não invente valores.",
        "schema": {
            "type": "OBJECT",
            "properties": {
                **_CAMPOS_COMUNS,
                "nome": {"type": "STRING"},
                "cpf": {"type": "STRING"},
                "tipo_documento": {
                    "type": "STRING",
                    "description": "Tipo de documento identificado: RG ou CNH.",
                },
            },
            "required": ["legibilidade", "qualidade_imagem", "documento_integro", "tipo_documento"],
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
            "required": ["renda_bruta", "renda_liquida", "legibilidade", "qualidade_imagem", "documento_integro"],
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
    propriedades = schema.get("properties", {})
    return {campo: dados.get(campo) for campo in propriedades if campo in dados}


def avaliar_possivel_divergencia(dados_extraidos: dict, categoria: str) -> bool:
    categoria = categoria.upper()
    campos_chave = _CAMPOS_CHAVE_POR_CATEGORIA.get(categoria, ())
    if not campos_chave:
        return False
    nulos = sum(1 for campo in campos_chave if dados_extraidos.get(campo) in (None, "", []))
    return (nulos / len(campos_chave)) >= 0.5


def extrair_dados_documento(conteudo: bytes, mime_type: str, categoria: str) -> dict:
    """Envia o documento (em bytes) pro Gemini e devolve os campos extraídos.

    Levanta GeminiExtractionError em qualquer falha — a rota decide o que
    fazer com isso, sem derrubar a aplicação.
    Usa o modelo principal e o fallback configurados, com prazo por chamada.
    Registra apenas modelo, categoria e código do erro, sem dados pessoais.
    """
    config_extracao = _SCHEMAS_E_PROMPTS.get(categoria.upper(), _SCHEMAS_E_PROMPTS["OUTRO"])
    client = _get_client()

    modelos = list(dict.fromkeys(m for m in (
        settings.gemini_model, settings.gemini_fallback_model
    ) if m))
    erros = []

    for modelo in modelos:
        for usar_schema in (True, False):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=[
                        config_extracao["prompt"],
                        types.Part.from_bytes(data=conteudo, mime_type=mime_type),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=config_extracao["schema"] if usar_schema else None,
                        temperature=0.1,
                    ),
                )
                dados = _parse_json_response(response.text)
                if dados.get("cpf") and not cpf_extraido_valido(dados["cpf"]):
                    raise CpfExtractionError("CPF extraído inválido.")
                return _filtrar_campos_resposta(dados, config_extracao["schema"])
            except Exception as exc:
                codigo = getattr(exc, "code", None)
                erros.append((codigo, type(exc).__name__))
                logger.warning("Extração Gemini falhou: modelo=%s categoria=%s codigo=%s tipo=%s",
                               modelo, categoria, codigo, type(exc).__name__)
                if codigo in (401, 403):
                    raise GeminiExtractionError(
                        "A IA recusou a autenticação ou o acesso. O administrador deve conferir a chave e as permissões."
                    ) from exc
                # Remover o schema só ajuda em falhas de formato, não em
                # sobrecarga, cota ou modelo indisponível.
                if usar_schema and (codigo == 400 or isinstance(exc, ValueError)):
                    continue
                break

    codigos = {codigo for codigo, _ in erros}
    if any(tipo == "CpfExtractionError" for _, tipo in erros):
        raise GeminiExtractionError(
            "A IA não confirmou um CPF válido no documento. Envie uma imagem mais nítida ou solicite revisão manual."
        )
    if 429 in codigos:
        raise GeminiExtractionError(
            "A cota de uso da IA foi atingida. Aguarde e tente novamente; se persistir, confira a cota do projeto."
        )
    if 503 in codigos:
        raise GeminiExtractionError(
            "A IA está sobrecarregada no momento. Aguarde e clique em Reenviar."
        )
    if erros and all(codigo == 404 for codigo, _ in erros):
        raise GeminiExtractionError(
            "Os modelos de IA configurados não estão disponíveis. O administrador deve revisar a configuração."
        )
    raise GeminiExtractionError(
        "A IA não concluiu a extração no prazo ou retornou dados inválidos. Clique em Reenviar."
    )
