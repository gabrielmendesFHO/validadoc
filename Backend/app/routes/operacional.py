"""Rotas operacionais usadas pelo painel e pela auditoria manual."""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import exigir_perfil
from ..models import (
    AnalisesOcr,
    DocumentosEnviados,
    DocumentosSolicitados,
    Inscricoes,
    MembrosFamilia,
    ProcessosBolsa,
    StatusJornada,
    Usuarios,
)

router = APIRouter(tags=["Painel operacional"])


class ParecerManualIn(BaseModel):
    decisao: str
    justificativa: str = Field(min_length=3, max_length=4000)


def _valor_status(status_funil) -> str:
    return status_funil.value if isinstance(status_funil, StatusJornada) else str(status_funil)


@router.get("/dashboard/metricas")
def metricas_funil(
    processo_id: int | None = None,
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Conta inscrições por etapa do funil e devolve indicadores operacionais."""
    consulta = db.query(Inscricoes)
    if processo_id is not None:
        consulta = consulta.filter(Inscricoes.processo_id == processo_id)

    agrupado = consulta.with_entities(
        Inscricoes.status_funil, func.count(Inscricoes.id)
    ).group_by(Inscricoes.status_funil).all()

    por_status = {status.value: 0 for status in StatusJornada}
    for status_funil, quantidade in agrupado:
        por_status[_valor_status(status_funil)] = quantidade

    limite_ausencia = datetime.now() - timedelta(days=7)
    com_dificuldade = consulta.filter(Inscricoes.alertas_dificuldade > 0).count()
    sem_acesso = consulta.filter(Inscricoes.ultimo_acesso.is_(None)).count()
    ausentes = consulta.filter(
        or_(Inscricoes.ultimo_acesso.is_(None), Inscricoes.ultimo_acesso < limite_ausencia)
    ).count()

    return {
        "total": sum(por_status.values()),
        "por_status": por_status,
        "prontas_auditoria": por_status[StatusJornada.PRONTO_AUDITORIA.value],
        "concluidas": por_status[StatusJornada.CONCLUIDO.value],
        "com_dificuldade": com_dificuldade,
        "sem_acesso": sem_acesso,
        "ausentes": ausentes,
    }


@router.get("/dashboard/estagnadas")
def listar_estagnadas(
    busca: str = Query(default="", max_length=100),
    processo_id: int | None = None,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Lista apenas inscrições com dificuldade ou prontas para auditoria."""
    consulta = (
        db.query(Inscricoes, Usuarios, ProcessosBolsa)
        .join(Usuarios, Inscricoes.candidato_id == Usuarios.id)
        .join(ProcessosBolsa, Inscricoes.processo_id == ProcessosBolsa.id)
        .filter(
            or_(
                Inscricoes.alertas_dificuldade > 0,
                Inscricoes.status_funil == StatusJornada.PRONTO_AUDITORIA,
            )
        )
    )
    if processo_id is not None:
        consulta = consulta.filter(Inscricoes.processo_id == processo_id)
    termo = busca.strip()
    if termo:
        consulta = consulta.filter(
            Inscricoes.id == int(termo)
            if termo.isdigit()
            else Usuarios.nome_completo.ilike(f"%{termo}%")
        )

    total = consulta.count()
    registros = (
        consulta.order_by(Inscricoes.ultima_atividade.asc(), Inscricoes.id.asc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    return {
        "itens": [
            {
                "inscricao_id": inscricao.id,
                "candidato": candidato.nome_completo,
                "email": candidato.email,
                "processo": processo.nome,
                "status_funil": _valor_status(inscricao.status_funil),
                "situacao": (
                    "COM_DIFICULDADE"
                    if inscricao.alertas_dificuldade > 0
                    else StatusJornada.PRONTO_AUDITORIA.value
                ),
                "alertas_dificuldade": inscricao.alertas_dificuldade,
                "ultima_atividade": inscricao.ultima_atividade,
            }
            for inscricao, candidato, processo in registros
        ],
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
    }


def _json_seguro(valor):
    if not valor:
        return None
    try:
        return json.loads(valor)
    except (TypeError, ValueError):
        return {"conteudo": str(valor)}


@router.get("/auditoria/{inscricao_id}")
def obter_auditoria(
    inscricao_id: int,
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Reúne arquivo, dados declarados e extraídos para a tela split-view."""
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")

    candidato = db.get(Usuarios, inscricao.candidato_id)
    processo = db.get(ProcessosBolsa, inscricao.processo_id)
    membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()
    membros_por_id = {membro.id: membro for membro in membros}
    solicitados = {
        solicitado.id: solicitado
        for solicitado in db.query(DocumentosSolicitados)
        .filter_by(processo_id=inscricao.processo_id)
        .all()
    }

    documentos = []
    enviados = (
        db.query(DocumentosEnviados)
        .filter_by(inscricao_id=inscricao_id)
        .order_by(DocumentosEnviados.criado_em.desc(), DocumentosEnviados.id.desc())
        .all()
    )
    for documento in enviados:
        analise = (
            db.query(AnalisesOcr)
            .filter_by(documento_id=documento.id)
            .order_by(AnalisesOcr.criado_em.desc(), AnalisesOcr.id.desc())
            .first()
        )
        membro = membros_por_id.get(documento.membro_id)
        solicitado = solicitados.get(documento.solicitado_id)
        documentos.append(
            {
                "id": documento.id,
                "categoria": solicitado.nome_documento if solicitado else "OUTRO",
                "pessoa": membro.nome_completo if membro else candidato.nome_completo,
                "membro_id": documento.membro_id,
                "status_processamento": documento.status_processamento,
                "status_auditoria": analise.status_auditoria if analise else "PENDENTE",
                "parecer_ia": analise.parecer if analise else documento.mensagem_erro,
                "dados_extraidos": _json_seguro(analise.dados_extraidos) if analise else None,
                "arquivo_url": f"/documentos/{documento.id}/arquivo",
                "nome_arquivo": documento.binario.nome_arquivo_original if documento.binario else None,
                "mime_type": documento.binario.mime_type if documento.binario else None,
            }
        )

    return {
        "inscricao": {
            "id": inscricao.id,
            "status_funil": _valor_status(inscricao.status_funil),
            "status_geral": inscricao.status_geral,
            "parecer": inscricao.parecer,
            "renda_per_capita_calculada": inscricao.renda_per_capita_calculada,
        },
        "candidato": {
            "nome_completo": candidato.nome_completo,
            "cpf": candidato.cpf,
            "email": candidato.email,
        },
        "processo": {
            "id": processo.id,
            "nome": processo.nome,
            "renda_per_capita_limite": processo.renda_per_capita_limite,
        },
        "membros": [
            {
                "id": membro.id,
                "nome_completo": membro.nome_completo,
                "cpf": membro.cpf,
                "parentesco": membro.parentesco,
                "renda_declarada": membro.renda_declarada,
            }
            for membro in membros
        ],
        "documentos": documentos,
    }


@router.put("/auditoria/{inscricao_id}/parecer")
def registrar_parecer_manual(
    inscricao_id: int,
    dados: ParecerManualIn,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Persiste a decisão final e a justificativa informadas pelo analista."""
    decisao = dados.decisao.strip().upper()
    if decisao not in {"APROVAR", "REJEITAR"}:
        raise HTTPException(status_code=422, detail="A decisão deve ser APROVAR ou REJEITAR.")

    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if inscricao.status_funil == StatusJornada.ABANDONO:
        raise HTTPException(status_code=409, detail="Uma inscrição abandonada não pode receber parecer.")

    inscricao.status_geral = "APTO" if decisao == "APROVAR" else "NAO_APTO"
    inscricao.status_funil = StatusJornada.CONCLUIDO
    inscricao.parecer = dados.justificativa.strip()
    inscricao.ultima_atividade = datetime.now()
    db.add(inscricao)
    db.commit()
    db.refresh(inscricao)

    return {
        "inscricao_id": inscricao.id,
        "decisao": decisao,
        "status_geral": inscricao.status_geral,
        "status_funil": _valor_status(inscricao.status_funil),
        "parecer": inscricao.parecer,
        "analista_id": usuario.id,
    }
