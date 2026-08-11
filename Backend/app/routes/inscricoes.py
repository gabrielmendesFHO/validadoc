import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..dependencies import exigir_perfil, get_current_user, usuario_pode_acessar_inscricao
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    AnalisesOcr,
    DocumentosEnviados,
    DocumentosSolicitados,
    Inscricoes,
    MembrosFamilia,
    ProcessosBolsa,
    Usuarios,
)
from ..services.regras_negocio import auditar_inscricao

router = APIRouter(prefix="/inscricoes", tags=["Inscrições"])


class MembroFamiliaIn(BaseModel):
    nome_completo: str
    parentesco: str | None = None
    renda_declarada: float | None = None


@router.post("/{inscricao_id}/membros")
def adicionar_membro(
    inscricao_id: int,
    membro: MembroFamiliaIn,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if not usuario_pode_acessar_inscricao(usuario, inscricao):
        raise HTTPException(status_code=403, detail="Você não pode acessar esta inscrição.")

    novo_membro = MembrosFamilia(inscricao_id=inscricao_id, **membro.model_dump())
    db.add(novo_membro)
    db.commit()
    db.refresh(novo_membro)
    return novo_membro


@router.get("/{inscricao_id}/membros")
def listar_membros(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if not usuario_pode_acessar_inscricao(usuario, inscricao):
        raise HTTPException(status_code=403, detail="Você não pode acessar esta inscrição.")
    return inscricao.membros_familia

@router.post("/{inscricao_id}/auditar")
def auditar_inscricao_endpoint(
    inscricao_id: int,
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")

    candidato = db.get(Usuarios, inscricao.candidato_id)
    processo = db.get(ProcessosBolsa, inscricao.processo_id)

    solicitados = db.query(DocumentosSolicitados).filter_by(processo_id=inscricao.processo_id).all()
    obrigatorios = {s.id for s in solicitados if s.obrigatorio}
    solicitado_por_id = {s.id: s.nome_documento for s in solicitados}

    enviados = db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao_id).all()
    concluidos_ids = {d.solicitado_id for d in enviados if d.status_processamento == "CONCLUIDO"}

    faltando = obrigatorios - concluidos_ids
    if faltando:
        nomes_faltando = [solicitado_por_id.get(sid, str(sid)) for sid in faltando]
        inscricao.status_geral = "PENDENTE"
        inscricao.parecer = f"Documentos obrigatórios pendentes: {', '.join(nomes_faltando)}."
        inscricao.inconsistencias = None
        db.commit()
        return {"status_geral": inscricao.status_geral, "parecer": inscricao.parecer}

    documentos_com_analise = []
    partes_rg = []
    for doc in enviados:
        categoria = solicitado_por_id.get(doc.solicitado_id, "OUTRO")
        ultima_analise = (
            db.query(AnalisesOcr)
            .filter_by(documento_id=doc.id)
            .order_by(AnalisesOcr.criado_em.desc())
            .first()
        )
        dados, status_auditoria = None, None
        if ultima_analise and ultima_analise.dados_extraidos:
            dados = json.loads(ultima_analise.dados_extraidos)
            status_auditoria = ultima_analise.status_auditoria
        if categoria in {"RG", "RG_VERSO"}:
            partes_rg.append((dados, doc.status_processamento, status_auditoria))
        else:
            documentos_com_analise.append((categoria, dados, doc.status_processamento, status_auditoria))

    if partes_rg:
        dados_rg = {}
        for dados, status_processamento, _ in partes_rg:
            if status_processamento == "CONCLUIDO" and dados:
                dados_rg.update(dados)
        status_rg = "CONCLUIDO" if dados_rg and all(
            status_processamento == "CONCLUIDO"
            for _, status_processamento, _ in partes_rg
        ) else "PENDENTE"
        status_auditoria_rg = next(
            (
                status_auditoria
                for _, _, status_auditoria in partes_rg
                if status_auditoria == "POSSIVEL_DIVERGENCIA"
            ),
            None,
        )
        documentos_com_analise.append(("RG", dados_rg or None, status_rg, status_auditoria_rg))

    membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()

    resultado = auditar_inscricao(candidato, documentos_com_analise, membros, processo)

    inscricao.status_geral = resultado.status_geral
    inscricao.parecer = resultado.parecer
    inscricao.inconsistencias = (
        json.dumps(resultado.inconsistencias, ensure_ascii=False) if resultado.inconsistencias else None
    )
    inscricao.renda_per_capita_calculada = resultado.renda_per_capita
    db.commit()
    db.refresh(inscricao)

    return {
        "status_geral": inscricao.status_geral,
        "parecer": inscricao.parecer,
        "inconsistencias": resultado.inconsistencias,
        "renda_per_capita_calculada": inscricao.renda_per_capita_calculada,
    }