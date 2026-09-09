"""Motor de regras de negócio — consolida os documentos de uma inscrição
num parecer único (APTO / NAO_APTO / REVISAO_MANUAL), aplicando as 4
categorias de validação da seção 3.8.2 do TCC: validade temporal,
consistência financeira, teto de elegibilidade e validação de identidade.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List
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
        return default

    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return default
        texto = texto.replace("R$", "").replace(" ", "")
        texto = texto.replace(".", "").replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            return default

    try:
        return float(valor)
    except (TypeError, ValueError, InvalidOperation):
        return default


def _validar_lote_documentos(documentos, nome_pessoa, cpf_cadastro, inconsistencias):
    """
    Roda as validações de Qualidade, Validade Temporal, Identidade e Consistência Financeira 
    para um lote de documentos pertencentes a uma pessoa.
    Retorna a renda_bruta extraída (se houver holerite).
    """
    dados_por_categoria = {
        cat: dados
        for cat, dados, status_proc, _ in documentos
        if status_proc == "CONCLUIDO" and dados
    }

    # 1. Qualidade/legibilidade e possíveis divergências de tipo
    for cat, dados, status_proc, status_auditoria in documentos:
        if status_proc != "CONCLUIDO" or not dados:
            continue
        if status_auditoria == "POSSIVEL_DIVERGENCIA":
            inconsistencias.append(f"[{nome_pessoa}] {cat}: documento pode não corresponder ao tipo esperado.")
        legibilidade = dados.get("legibilidade")
        if legibilidade is not None and legibilidade < LEGIBILIDADE_MINIMA:
            inconsistencias.append(f"[{nome_pessoa}] {cat}: legibilidade baixa ({legibilidade}/100).")
        if dados.get("documento_integro") is False:
            inconsistencias.append(f"[{nome_pessoa}] {cat}: documento aparenta não estar íntegro.")

    # 2. Validade temporal
    for cat in CATEGORIAS_COM_VALIDADE_TEMPORAL:
        dados = dados_por_categoria.get(cat)
        if not dados:
            continue
        data_emissao = _parse_data_br(dados.get("data_emissao"))
        if data_emissao is None:
            inconsistencias.append(f"[{nome_pessoa}] {cat}: data de emissão não identificada.")
            continue
        dias = (datetime.now() - data_emissao).days
        if dias > VALIDADE_MAXIMA_DIAS:
            inconsistencias.append(f"[{nome_pessoa}] {cat}: documento emitido há {dias} dias (limite: {VALIDADE_MAXIMA_DIAS}).")

    # 3. Consistência financeira (holerite)
    holerite = dados_por_categoria.get("HOLERITE")
    renda_bruta = None
    if holerite:
        renda_bruta = _valor_para_float(holerite.get("renda_bruta"), default=None)
        renda_liquida = _valor_para_float(holerite.get("renda_liquida"), default=None)
        if renda_bruta is not None and renda_liquida is not None:
            if renda_liquida > renda_bruta:
                inconsistencias.append(
                    f"[{nome_pessoa}] Renda líquida (R$ {renda_liquida:.2f}) maior que a renda bruta (R$ {renda_bruta:.2f})."
                )

    # 4. Validação de identidade (RG ou CNH vs. cadastro esperado)
    doc_identidade = dados_por_categoria.get("RG") or dados_por_categoria.get("CNH")
    if doc_identidade:
        cpf_documento = _normalizar_cpf(doc_identidade.get("cpf"))
        cpf_esperado = _normalizar_cpf(cpf_cadastro)
        nome_documento = _normalizar_nome(doc_identidade.get("nome"))
        nome_esperado = _normalizar_nome(nome_pessoa)

        if cpf_esperado and cpf_documento and cpf_documento != cpf_esperado:
            inconsistencias.append(f"[{nome_pessoa}] CPF do documento diverge do CPF informado no cadastro.")

        if nome_documento and nome_esperado and nome_documento != nome_esperado:
            inconsistencias.append(f"[{nome_pessoa}] Nome do documento ({nome_documento}) diverge do nome cadastrado ({nome_esperado}).")
    else:
        inconsistencias.append(f"[{nome_pessoa}] Nenhum documento de identidade (RG/CNH) processado com sucesso.")

    return renda_bruta


def auditar_inscricao(candidato, documentos_candidato, membros_familia, documentos_membros, processo) -> ResultadoAuditoria:
    """
    candidato: objeto Usuarios (dono da inscrição)
    documentos_candidato: lista de tuplas
    membros_familia: lista de MembrosFamilia
    documentos_membros: dict {membro_id: lista de tuplas de analise}
    processo: objeto ProcessosBolsa
    """
    inconsistencias = []

    # Auditar Candidato
    renda_bruta_candidato = _validar_lote_documentos(
        documentos=documentos_candidato, 
        nome_pessoa=candidato.nome_completo, 
        cpf_cadastro=getattr(candidato, "cpf", None),
        inconsistencias=inconsistencias
    )
    
    # Se o CPF principal não estiver no banco, a gente avisa explicitamente pro titular
    if not getattr(candidato, "cpf", None):
        inconsistencias.append(f"[{candidato.nome_completo}] CPF não cadastrado no perfil do candidato — identidade não confirmada.")

    renda_total = 0.0
    if renda_bruta_candidato is not None:
        renda_total += renda_bruta_candidato
    else:
        inconsistencias.append(f"[{candidato.nome_completo}] Renda bruta não identificada (holerite ausente ou não lido).")

    # Auditar Membros da Família
    for membro in membros_familia:
        docs_do_membro = documentos_membros.get(membro.id, [])
        renda_bruta_membro = _validar_lote_documentos(
            documentos=docs_do_membro,
            nome_pessoa=membro.nome_completo,
            cpf_cadastro=None, # Apenas valida se o nome bater, já que membro não tem CPF explícito salvo no banco ainda
            inconsistencias=inconsistencias
        )
        
        # A renda contabilizada para a família prefere o holerite lido, senão cai pro valor que o candidato declarou na tela
        if renda_bruta_membro is not None:
            renda_total += renda_bruta_membro
        else:
            renda_declarada = _valor_para_float(membro.renda_declarada, default=0.0)
            renda_total += renda_declarada
            if renda_declarada > 0:
                inconsistencias.append(f"[{membro.nome_completo}] Holerite não extraído. Usando renda declarada manualmente (R$ {renda_declarada:.2f}).")

    # Auditoria de Filiação: compara nomes dos membros progenitores com o RG do candidato
    dados_por_categoria_candidato = {
        cat: dados
        for cat, dados, status_proc, _ in documentos_candidato
        if status_proc == "CONCLUIDO" and dados
    }
    rg_candidato = dados_por_categoria_candidato.get("RG") or {}
    nome_mae_rg = _normalizar_nome(rg_candidato.get("nome_mae"))
    nome_pai_rg = _normalizar_nome(rg_candidato.get("nome_pai"))

    PARENTESCOS_MAE = {"MÃE", "MAE", "MÃE BIOLÓGICA", "MAE BIOLOGICA", "MÃEBIOLÓGICA"}
    PARENTESCOS_PAI = {"PAI", "PAI BIOLÓGICO", "PAI BIOLOGICO"}

    for membro in membros_familia:
        parentesco_norm = (getattr(membro, "parentesco", None) or "").strip().upper()
        nome_membro = _normalizar_nome(membro.nome_completo)

        if parentesco_norm in PARENTESCOS_MAE:
            if nome_mae_rg and nome_membro and nome_membro != nome_mae_rg:
                inconsistencias.append(
                    f"[{membro.nome_completo}] Nome declarado como Mãe diverge do nome da mãe no RG do candidato ({rg_candidato.get('nome_mae')})."
                )
            elif not nome_mae_rg:
                inconsistencias.append(
                    f"[{membro.nome_completo}] Não foi possível verificar filiação: nome da mãe não encontrado no RG do candidato."
                )

        elif parentesco_norm in PARENTESCOS_PAI:
            if nome_pai_rg and nome_membro and nome_membro != nome_pai_rg:
                inconsistencias.append(
                    f"[{membro.nome_completo}] Nome declarado como Pai diverge do nome do pai no RG do candidato ({rg_candidato.get('nome_pai')})."
                )
            elif not nome_pai_rg:
                inconsistencias.append(
                    f"[{membro.nome_completo}] Não foi possível verificar filiação: nome do pai não encontrado no RG do candidato."
                )


    # Cálculo final do teto
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