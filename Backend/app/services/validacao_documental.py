"""Módulo de validação de autenticidade, titularidade e qualidade dos documentos.

Executado imediatamente no momento do upload (antes ou após a IA) para garantir que:
1. Arquivos duplicados sejam barrados por comparação de bytes (anti-fraude básica).
2. O documento enviado pertence à pessoa certa (candidato titular vs. membro familiar).
3. Avisos de qualidade (legibilidade baixa, prazo vencido > 90 dias, integridade)
   sejam diagnosticados imediatamente para orientar o candidato.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .regras_negocio import (
    LEGIBILIDADE_MINIMA,
    VALIDADE_MAXIMA_DIAS,
    _normalizar_cpf,
    _normalizar_nome,
    _parse_data_br,
)
from .gemini_service import avaliar_possivel_divergencia, lado_documento_invalido


def validar_documento_no_upload(
    categoria: str,
    dados_extraidos: Dict[str, Any],
    candidato: Any,
    membro: Optional[Any],
    outros_membros: List[Any],
) -> Tuple[bool, Optional[str], str, str]:
    """Valida o documento extraído pela IA em relação ao participante selecionado.

    Retorna:
        (valido, motivo_rejeicao, nivel_alerta, mensagem_feedback)

        - valido (bool): False se o documento deve ser REJEITADO (ex: pertence a outra pessoa).
        - motivo_rejeicao (str | None): mensagem de bloqueio se valido for False.
        - nivel_alerta (str): 'sucesso' | 'aviso' | 'erro'
        - mensagem_feedback (str): texto explicativo para exibição no card do frontend.
    """
    categoria_upper = categoria.upper()

    # 1. Validação do lado do RG (Frente vs Verso)
    if categoria_upper in {"RG", "RG_VERSO"} and lado_documento_invalido(dados_extraidos, categoria_upper):
        lado_esperado = "frente" if categoria_upper == "RG" else "verso"
        motivo = f"Documento inválido: este upload exige o lado {lado_esperado} do RG."
        return False, motivo, "erro", motivo

    # 2. Validação cruzada de titularidade (RG e CNH)
    if categoria_upper in {"RG", "RG_VERSO", "CNH"}:
        cpf_doc = _normalizar_cpf(dados_extraidos.get("cpf"))
        nome_doc = _normalizar_nome(dados_extraidos.get("nome"))

        cpf_cand = _normalizar_cpf(getattr(candidato, "cpf", None))
        nome_cand = _normalizar_nome(getattr(candidato, "nome_completo", None))

        # --- Upload destinado a um MEMBRO DA FAMÍLIA ---
        if membro is not None:
            # Não pode pertencer ao candidato titular
            if cpf_doc and cpf_cand and cpf_doc == cpf_cand:
                motivo = "Documento rejeitado: este documento pertence ao candidato titular e não a este membro familiar."
                return False, motivo, "erro", motivo

            if nome_doc and nome_cand and nome_doc == nome_cand:
                motivo = f"Documento rejeitado: a identidade está em nome do candidato titular ({dados_extraidos.get('nome')}) e não do familiar."
                return False, motivo, "erro", motivo

            # O nome no documento deve conferir com o familiar selecionado
            nome_membro = _normalizar_nome(getattr(membro, "nome_completo", ""))
            if nome_doc and nome_membro:
                tokens_doc = set(nome_doc.split())
                tokens_membro = set(nome_membro.split())
                # Se não compartilham nenhuma palavra do nome
                if not (tokens_doc & tokens_membro):
                    motivo = (
                        f"Documento rejeitado: o nome no documento ({dados_extraidos.get('nome')}) "
                        f"não confere com o familiar cadastrado ({membro.nome_completo})."
                    )
                    return False, motivo, "erro", motivo

        # --- Upload destinado ao CANDIDATO TITULAR ---
        else:
            # Não pode pertencer a nenhum dos membros já cadastrados
            for m in outros_membros:
                nome_m = _normalizar_nome(getattr(m, "nome_completo", ""))
                if nome_doc and nome_m and nome_doc == nome_m:
                    motivo = f"Documento rejeitado: este documento pertence ao familiar '{m.nome_completo}' e não ao candidato titular."
                    return False, motivo, "erro", motivo

    # 3. Diagnóstico de qualidade e avisos (o documento é aceito, mas com alertas)
    avisos: List[str] = []

    # Legibilidade
    legibilidade = dados_extraidos.get("legibilidade")
    if legibilidade is not None and isinstance(legibilidade, (int, float)) and legibilidade < LEGIBILIDADE_MINIMA:
        avisos.append(f"Foto com baixa nitidez ({int(legibilidade)}/100). Recomendamos enviar uma foto mais clara e focada.")

    # Integridade
    if dados_extraidos.get("documento_integro") is False:
        avisos.append("O documento aparenta conter cortes, sombras excessivas ou sinais de rasura.")

    # Divergência de categoria
    if avaliar_possivel_divergencia(dados_extraidos, categoria_upper):
        avisos.append(f"A imagem pode não corresponder a um(a) {categoria_upper} válido(a) ou faltam campos essenciais.")

    # Validade temporal (Residência e Holerite - máx 90 dias)
    if categoria_upper in {"RESIDENCIA", "HOLERITE"}:
        data_str = dados_extraidos.get("data_emissao")
        data_emissao = _parse_data_br(data_str)
        if data_emissao:
            dias = (datetime.now() - data_emissao).days
            if dias > VALIDADE_MAXIMA_DIAS:
                avisos.append(f"Comprovante emitido há {dias} dias (o limite aceito pelo processo seletivo é de até {VALIDADE_MAXIMA_DIAS} dias).")
        elif not data_str:
            avisos.append("A data de emissão não pôde ser confirmada na imagem.")

    if avisos:
        return True, None, "aviso", " ".join(avisos)

    return True, None, "sucesso", "Documento lido e aprovado com sucesso."

