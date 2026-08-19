import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import exigir_perfil, get_current_user
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

# Documentos que representam lados diferentes do mesmo documento físico —
# a tela de checklist mostra isso como um card só (Documento de Identidade).
GRUPOS_IDENTIDADE = {"RG", "RG_VERSO"}
ROTULOS_IDENTIDADE = {"RG": "Frente", "RG_VERSO": "Verso"}

TITULOS_CHECKLIST = {
    "IDENTIDADE": ("Documento de Identidade", "Formatos: PDF, JPG, PNG"),
    "RESIDENCIA": ("Comprovativo de Morada", "Água, Luz ou Telefone (Máx. 3 meses)"),
    "HOLERITE": ("Comprovativo de Rendimentos", "Últimos 3 meses"),
    "CNH": ("CNH", "Formatos: PDF, JPG, PNG"),
    "OUTRO": ("Outro documento", None),
}


class MembroFamiliaIn(BaseModel):
    nome_completo: str
    parentesco: str | None = None
    renda_declarada: float | None = None


@router.get("/minha")
def minha_inscricao(
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("CANDIDATO")),
):
    """Devolve a inscrição mais recente do candidato logado — cria uma nova
    (no processo de bolsa mais recente) se ele ainda não tiver nenhuma."""
    inscricao = (
        db.query(Inscricoes)
        .filter_by(candidato_id=usuario.id)
        .order_by(Inscricoes.id.desc())
        .first()
    )
    if inscricao is not None:
        return {"id": inscricao.id, "processo_id": inscricao.processo_id, "status_geral": inscricao.status_geral}

    processo = db.query(ProcessosBolsa).order_by(ProcessosBolsa.id.desc()).first()
    if processo is None:
        raise HTTPException(status_code=404, detail="Nenhum processo de bolsa cadastrado ainda.")

    nova_inscricao = Inscricoes(processo_id=processo.id, candidato_id=usuario.id, status_geral="PENDENTE")
    db.add(nova_inscricao)
    db.commit()
    db.refresh(nova_inscricao)
    return {"id": nova_inscricao.id, "processo_id": nova_inscricao.processo_id, "status_geral": nova_inscricao.status_geral}


@router.get("/{inscricao_id}/checklist")
def checklist_documentos(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

    solicitados = (
        db.query(DocumentosSolicitados)
        .filter_by(processo_id=inscricao.processo_id)
        .order_by(DocumentosSolicitados.id)
        .all()
    )
    enviados = db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao_id).all()

    ultimo_por_solicitado = {}
    for doc in enviados:
        anterior = ultimo_por_solicitado.get(doc.solicitado_id)
        if anterior is None or doc.criado_em >= anterior.criado_em:
            ultimo_por_solicitado[doc.solicitado_id] = doc

    def status_do_item(solicitado_id):
        doc = ultimo_por_solicitado.get(solicitado_id)
        if doc is None:
            return "PENDENTE", None
        if doc.status_processamento == "CONCLUIDO":
            return "ENVIADO", doc.id
        return "PENDENTE", doc.id

    grupos, ordem = {}, []
    for solicitado in solicitados:
        nome = solicitado.nome_documento
        chave = "IDENTIDADE" if nome in GRUPOS_IDENTIDADE else nome

        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)

        status, documento_id = status_do_item(solicitado.id)
        rotulo = ROTULOS_IDENTIDADE.get(nome) if chave == "IDENTIDADE" else None
        grupos[chave].append(
            {
                "solicitado_id": solicitado.id,
                "nome_documento": nome,
                "rotulo": rotulo,
                "obrigatorio": bool(solicitado.obrigatorio),
                "status": status,
                "documento_id": documento_id,
            }
        )

    resultado = []
    for chave in ordem:
        itens = grupos[chave]
        titulo, descricao_padrao = TITULOS_CHECKLIST.get(chave, (chave.title(), None))
        status_geral_item = "ENVIADO" if all(item["status"] == "ENVIADO" for item in itens) else "PENDENTE"
        resultado.append(
            {
                "chave": chave,
                "titulo": titulo,
                "descricao": descricao_padrao,
                "status": status_geral_item,
                "obrigatorio": any(item["obrigatorio"] for item in itens),
                "itens": itens,
            }
        )

    return resultado


@router.post("/{inscricao_id}/membros")
def adicionar_membro(inscricao_id: int, membro: MembroFamiliaIn, db: Session = Depends(get_db)):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")

    novo_membro = MembrosFamilia(inscricao_id=inscricao_id, **membro.model_dump())
    db.add(novo_membro)
    db.commit()
    db.refresh(novo_membro)
    return novo_membro


@router.get("/{inscricao_id}/membros")
def listar_membros(inscricao_id: int, db: Session = Depends(get_db)):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
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