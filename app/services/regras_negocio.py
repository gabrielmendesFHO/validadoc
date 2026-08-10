"""Motor de regras de negócio — consolida os documentos de uma inscrição
num parecer único (APTO / NAO_APTO / REVISAO_MANUAL), aplicando as 4
categorias de validação da seção 3.8.2 do TCC: validade temporal,
consistência financeira, teto de elegibilidade e validação de identidade.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
import re

VALIDADE_MAXIMA_DIAS = 90
LEGIBILIDADE_MINIMA = 50
CATEGORIAS_COM_VALIDADE_TEMPORAL = {"RESIDENCIA", "HOLERITE"}


@dataclass
class ResultadoAuditoria:
    status_geral: str  # APTO | NAO_APTO | REVISAO_MANUAL
    parecer: str
    inconsistencias: list = field(default_factory=list)
    renda_per_capita: Optional[float] = None


def _parse_data_br(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor.strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None


def _normalizar_cpf(cpf):
    if not cpf:
        return None
    return re.sub(r"\D", "", cpf) or None


def _normalizar_nome(nome):
    if not nome:
        return None
    return " ".join(nome.strip().upper().split())


def _valor_para_float(valor, default=0.0):
    if valor is None or valor == "":
        return float(default)

    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return float(default)
        texto = texto.replace("R$", "").replace(" ", "")
        texto = texto.replace(".", "").replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            return float(default)

    try:
        return float(valor)
    except (TypeError, ValueError, InvalidOperation):
        return float(default)


def auditar_inscricao(candidato, documentos_com_analise, membros_familia, processo) -> ResultadoAuditoria:
    """
    candidato: objeto Usuarios (dono da inscrição)
    documentos_com_analise: lista de tuplas
        (categoria: str, dados: dict|None, status_processamento: str, status_auditoria: str|None)
    membros_familia: lista de MembrosFamilia
    processo: objeto ProcessosBolsa
    """
    inconsistencias = []

    dados_por_categoria = {
        cat: dados
        for cat, dados, status_proc, _ in documentos_com_analise
        if status_proc == "CONCLUIDO" and dados
    }

    # 1. Qualidade/legibilidade e possíveis divergências de tipo (vindas da Fase 1)
    for cat, dados, status_proc, status_auditoria in documentos_com_analise:
        if status_proc != "CONCLUIDO" or not dados:
            continue
        if status_auditoria == "POSSIVEL_DIVERGENCIA":
            inconsistencias.append(f"{cat}: documento pode não corresponder ao tipo esperado.")
        legibilidade = dados.get("legibilidade")
        if legibilidade is not None and legibilidade < LEGIBILIDADE_MINIMA:
            inconsistencias.append(f"{cat}: legibilidade baixa ({legibilidade}/100).")
        if dados.get("documento_integro") is False:
            inconsistencias.append(f"{cat}: documento aparenta não estar íntegro.")

    # 2. Validade temporal (comprovante de residência e holerite)
    for cat in CATEGORIAS_COM_VALIDADE_TEMPORAL:
        dados = dados_por_categoria.get(cat)
        if not dados:
            continue
        data_emissao = _parse_data_br(dados.get("data_emissao"))
        if data_emissao is None:
            inconsistencias.append(f"{cat}: data de emissão não identificada.")
            continue
        dias = (datetime.now() - data_emissao).days
        if dias > VALIDADE_MAXIMA_DIAS:
            inconsistencias.append(f"{cat}: documento emitido há {dias} dias (limite: {VALIDADE_MAXIMA_DIAS}).")

    # 3. Consistência financeira (holerite)
    holerite = dados_por_categoria.get("HOLERITE")
    renda_bruta_candidato = None
    if holerite:
        renda_bruta_candidato = _valor_para_float(holerite.get("renda_bruta"), default=None)
        renda_liquida = _valor_para_float(holerite.get("renda_liquida"), default=None)
        if renda_bruta_candidato is not None and renda_liquida is not None:
            if renda_liquida > renda_bruta_candidato:
                inconsistencias.append(
                    f"Renda líquida (R$ {renda_liquida:.2f}) maior que a renda bruta (R$ {renda_bruta_candidato:.2f})."
                )

    # 4. Teto de elegibilidade — renda per capita
    renda_per_capita = None
    if renda_bruta_candidato is not None:
        renda_total = renda_bruta_candidato + sum(
            _valor_para_float(m.renda_declarada) for m in membros_familia
        )
        num_membros = 1 + len(membros_familia)
        renda_per_capita = round(renda_total / num_membros, 2)

        limite = float(processo.renda_per_capita_limite) if processo.renda_per_capita_limite else None
        if limite is not None and renda_per_capita > limite:
            return ResultadoAuditoria(
                status_geral="NAO_APTO",
                parecer=(
                    f"Renda per capita calculada (R$ {renda_per_capita:.2f}) ultrapassa o "
                    f"limite máximo do processo (R$ {limite:.2f})."
                ),
                inconsistencias=inconsistencias,
                renda_per_capita=renda_per_capita,
            )
    else:
        inconsistencias.append("Renda per capita não calculada — holerite não processado ou renda_bruta ausente.")

    # 5. Validação de identidade (RG ou CNH vs. cadastro)
    doc_identidade = dados_por_categoria.get("RG") or dados_por_categoria.get("CNH")
    if doc_identidade:
        cpf_documento = _normalizar_cpf(doc_identidade.get("cpf"))
        cpf_cadastro = _normalizar_cpf(getattr(candidato, "cpf", None))
        nome_documento = _normalizar_nome(doc_identidade.get("nome"))
        nome_cadastro = _normalizar_nome(candidato.nome_completo)

        if cpf_cadastro is None:
            inconsistencias.append("CPF não cadastrado no perfil do candidato — identidade não confirmada.")
        elif cpf_documento and cpf_documento != cpf_cadastro:
            inconsistencias.append("CPF do documento de identidade diverge do CPF cadastrado.")

        if nome_documento and nome_cadastro and nome_documento != nome_cadastro:
            inconsistencias.append("Nome do documento de identidade diverge do nome cadastrado.")
    else:
        inconsistencias.append("Nenhum documento de identidade (RG/CNH) processado com sucesso.")

    if inconsistencias:
        return ResultadoAuditoria(
            status_geral="REVISAO_MANUAL",
            parecer="Inconsistências encontradas — revisão manual necessária.",
            inconsistencias=inconsistencias,
            renda_per_capita=renda_per_capita,
        )

    return ResultadoAuditoria(
        status_geral="APTO",
        parecer="Todos os critérios de validação foram atendidos automaticamente.",
        inconsistencias=[],
        renda_per_capita=renda_per_capita,
    )