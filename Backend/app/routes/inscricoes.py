import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import exigir_jornada_minima, exigir_perfil, get_current_user
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
from ..services.regras_negocio import auditar_inscricao
from ..services.image_processing import preparar_para_ia_multimodal
from ..services.gemini_service import GeminiExtractionError, extrair_dados_documento

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
    cpf: str | None = None
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
        return {"id": inscricao.id, "processo_id": inscricao.processo_id, "status_geral": inscricao.status_geral, "status_funil": inscricao.status_funil.value}

    processo = db.query(ProcessosBolsa).order_by(ProcessosBolsa.id.desc()).first()
    if processo is None:
        raise HTTPException(status_code=404, detail="Nenhum processo de bolsa cadastrado ainda.")

    nova_inscricao = Inscricoes(processo_id=processo.id, candidato_id=usuario.id, status_geral="PENDENTE")
    db.add(nova_inscricao)
    db.commit()
    db.refresh(nova_inscricao)
    return {"id": nova_inscricao.id, "processo_id": nova_inscricao.processo_id, "status_geral": nova_inscricao.status_geral, "status_funil": nova_inscricao.status_funil.value}


@router.get("/dashboard/metricas")
def metricas_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    """Devolve as estatísticas reais e o histórico de documentos enviados para o Dashboard."""
    query = (
        db.query(DocumentosEnviados, DocumentosSolicitados)
        .join(DocumentosSolicitados, DocumentosEnviados.solicitado_id == DocumentosSolicitados.id)
        .join(Inscricoes, DocumentosEnviados.inscricao_id == Inscricoes.id)
    )

    if usuario.perfil == "CANDIDATO":
        query = query.filter(Inscricoes.candidato_id == usuario.id)

    todos = query.all()
    hoje = datetime.now().date()
    ultimas_hoje = sum(1 for d, _ in todos if d.criado_em and d.criado_em.date() == hoje)
    concluidos = sum(1 for d, _ in todos if d.status_processamento == "CONCLUIDO")
    total = len(todos)

    percent = round((concluidos / total) * 100) if total > 0 else 0
    label_status = "Aprovado" if percent >= 70 else ("Em Análise" if percent >= 30 else ("Pendente" if total == 0 else "Rejeitado"))

    ultimos_docs = query.order_by(DocumentosEnviados.criado_em.desc()).limit(10).all()

    historico = []
    for d, s in ultimos_docs:
        if d.status_processamento == "CONCLUIDO":
            resultado = "Aprovado"
        elif d.status_processamento == "REJEITADO":
            resultado = "Rejeitado"
        elif d.status_processamento == "ERRO_EXTRACAO":
            resultado = "Erro IA"
        else:
            resultado = "Processando"

        historico.append({
            "id": d.id,
            "data": d.criado_em.strftime("%d/%m/%Y") if d.criado_em else "—",
            "hora": d.criado_em.strftime("%H:%M") if d.criado_em else "—",
            "tipo": s.nome_documento,
            "resultado": resultado,
        })

    return {
        "stats": {
            "ultimasValidacoesHoje": ultimas_hoje,
            "statusGeral": {
                "label": label_status,
                "percent": percent,
            },
            "totalValidacoes": total,
        },
        "historico": historico,
    }


@router.get("/minha/jornada")
def minha_jornada(
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("CANDIDATO")),
):
    """Resume a etapa atual e o próximo destino seguro da jornada."""
    inscricao = db.query(Inscricoes).filter_by(candidato_id=usuario.id).order_by(Inscricoes.id.desc()).first()
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Nenhuma inscrição encontrada.")
    proximo_destino = {
        StatusJornada.PRE_CADASTRADO: "/kyc", StatusJornada.KYC_PENDENTE: "/kyc",
        StatusJornada.KYC_VALIDADO: "/familia", StatusJornada.FAMILIA_PENDENTE: "/familia",
        StatusJornada.DOCS_PENDENTES: "/upload", StatusJornada.PRONTO_AUDITORIA: "/acompanhamento",
        StatusJornada.CONCLUIDO: "/acompanhamento", StatusJornada.ABANDONO: "/acompanhamento",
    }[inscricao.status_funil]
    return {"inscricao_id": inscricao.id, "status_funil": inscricao.status_funil.value, "status_geral": inscricao.status_geral, "parecer": inscricao.parecer, "ultima_atividade": inscricao.ultima_atividade, "proximo_destino": proximo_destino}


@router.get("/auditoria/fila")
def fila_auditoria(
    busca: str = Query(default="", max_length=100),
    processo_id: int | None = None,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Fila real de inscrições que aguardam a auditoria da equipe."""
    consulta = (
        db.query(Inscricoes, Usuarios, ProcessosBolsa)
        .join(Usuarios, Inscricoes.candidato_id == Usuarios.id)
        .join(ProcessosBolsa, Inscricoes.processo_id == ProcessosBolsa.id)
        .filter(Inscricoes.status_funil == StatusJornada.PRONTO_AUDITORIA)
    )
    if processo_id is not None:
        consulta = consulta.filter(Inscricoes.processo_id == processo_id)
    termo = busca.strip()
    if termo:
        consulta = consulta.filter(
            Inscricoes.id == int(termo) if termo.isdigit() else Usuarios.nome_completo.ilike(f"%{termo}%")
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
                "processo": processo.nome,
                "motivo": "Pronta para auditoria",
                "data": inscricao.ultima_atividade,
            }
            for inscricao, candidato, processo in registros
        ],
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
    }


@router.get("/dashboard/candidatos")
def dashboard_candidatos(
    busca: str = Query(default="", max_length=100),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    """Visão operacional por candidato: acesso, dificuldade e ausência."""
    consulta = db.query(Inscricoes, Usuarios).join(Usuarios, Inscricoes.candidato_id == Usuarios.id)
    termo = busca.strip()
    if termo:
        consulta = consulta.filter(Inscricoes.id == int(termo) if termo.isdigit() else Usuarios.nome_completo.ilike(f"%{termo}%"))
    total = consulta.count()
    registros = consulta.order_by(Inscricoes.ultima_atividade.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    limite_ausencia = datetime.now() - timedelta(days=7)
    itens = []
    for inscricao, candidato in registros:
        docs = db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao.id).all()
        erros = sum(documento.status_processamento in {"REJEITADO", "ERRO_EXTRACAO"} for documento in docs)
        dificuldade = inscricao.alertas_dificuldade > 0 or erros > 0
        acessou = inscricao.ultimo_acesso is not None
        ausente = not acessou or inscricao.ultimo_acesso < limite_ausencia
        itens.append({
            "inscricao_id": inscricao.id,
            "candidato": candidato.nome_completo,
            "email": candidato.email,
            "status_funil": inscricao.status_funil.value,
            "ultimo_acesso": inscricao.ultimo_acesso,
            "acessou": acessou,
            "com_dificuldade": dificuldade,
            "ausente": ausente,
            "documentos_com_erro": erros,
        })
    return {"itens": itens, "pagina": pagina, "por_pagina": por_pagina, "total": total}


@router.post("/{inscricao_id}/familia/concluir")
def concluir_familia(inscricao_id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.FAMILIA_PENDENTE))):
    """Confirma a composição familiar, inclusive quando o candidato mora só."""
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao.status_funil not in {StatusJornada.FAMILIA_PENDENTE, StatusJornada.KYC_VALIDADO}:
        raise HTTPException(status_code=409, detail="A etapa de grupo familiar já foi concluída.")
    inscricao.status_funil = StatusJornada.DOCS_PENDENTES
    db.add(inscricao)
    db.commit()
    return {"status_funil": inscricao.status_funil.value, "proxima_etapa": "DOCUMENTOS"}


@router.post("/{inscricao_id}/documentos/concluir")
def concluir_documentos(inscricao_id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.DOCS_PENDENTES))):
    """Envia a inscrição à fila de auditoria quando todos os obrigatórios foram aprovados."""
    inscricao = db.get(Inscricoes, inscricao_id)
    obrigatorios = {s.id for s in db.query(DocumentosSolicitados).filter_by(processo_id=inscricao.processo_id).all() if s.obrigatorio}
    pessoas = [None] + [m.id for m in db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()]
    for membro_id in pessoas:
        concluidos = {d.solicitado_id for d in db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao_id, membro_id=membro_id).all() if d.status_processamento == "CONCLUIDO"}
        if obrigatorios - concluidos:
            raise HTTPException(status_code=409, detail="Ainda existem documentos obrigatórios pendentes de validação.")
    inscricao.status_funil = StatusJornada.PRONTO_AUDITORIA
    db.add(inscricao)
    db.commit()
    return {"status_funil": inscricao.status_funil.value, "mensagem": "Documentos enviados para auditoria."}



@router.post("/{inscricao_id}/membros/extrair-documento")
async def extrair_documento_membro(
    inscricao_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
):
    """Recebe foto/PDF do RG ou CNH de um familiar, extrai nome e CPF via Gemini
    e devolve os dados para preencher o formulário automaticamente."""
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

    conteudo = await file.read()
    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # Pré-processamento de imagem (deskew + contraste), PDF passa direto
    conteudo_ia, mime_ia = preparar_para_ia_multimodal(conteudo, file.filename or "doc", file.content_type or "image/jpeg")

    try:
        dados = extrair_dados_documento(conteudo_ia, mime_ia, "IDENTIDADE_FAMILIAR")
    except GeminiExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Gemini pode retornar o nome em "nome" ou, no caso de CNH, também em "nome"
    nome = dados.get("nome") or dados.get("nome_completo") or ""
    cpf = dados.get("cpf") or None
    tipo_detectado = dados.get("tipo_documento") or "IDENTIDADE"

    if not nome:
        raise HTTPException(
            status_code=422,
            detail="Não foi possível identificar o nome no documento. Tente uma foto mais nítida ou preencha manualmente.",
        )

    return {"nome": nome, "cpf": cpf, "tipo_detectado": tipo_detectado}


def _gerar_checklist_para_pessoa(db, membro_id_alvo, solicitados, enviados):
    ultimo_por_solicitado = {}
    for doc in enviados:
        if doc.membro_id != membro_id_alvo:
            continue
        anterior = ultimo_por_solicitado.get(doc.solicitado_id)
        if anterior is None or doc.criado_em >= anterior.criado_em:
            ultimo_por_solicitado[doc.solicitado_id] = doc

    def status_do_item(solicitado_id):
        doc = ultimo_por_solicitado.get(solicitado_id)
        if doc is None:
            return "PENDENTE", None, None, None

        ultima_analise = (
            db.query(AnalisesOcr)
            .filter_by(documento_id=doc.id)
            .order_by(AnalisesOcr.criado_em.desc())
            .first()
        )

        mensagem = (ultima_analise.parecer if ultima_analise and ultima_analise.parecer else doc.mensagem_erro) or None

        if doc.status_processamento == "PROCESSANDO_IA":
            idade_segundos = (datetime.now() - doc.criado_em).total_seconds() if doc.criado_em else 0
            if idade_segundos > 120:
                doc.status_processamento = "ERRO_EXTRACAO"
                doc.mensagem_erro = "Tempo limite na análise pela IA. Clique em Reenviar."
                db.add(doc)
                db.commit()
                return "ERRO", doc.id, "erro", doc.mensagem_erro
            return "PROCESSANDO", doc.id, None, "Documento em análise pela Inteligência Artificial..."
        elif doc.status_processamento == "REJEITADO":
            return "REJEITADO", doc.id, "erro", mensagem
        elif doc.status_processamento == "ERRO_EXTRACAO":
            return "ERRO", doc.id, "erro", mensagem
        elif doc.status_processamento == "CONCLUIDO":
            if ultima_analise and ultima_analise.status_auditoria == "POSSIVEL_DIVERGENCIA":
                return "ATENCAO", doc.id, "aviso", mensagem
            return "ENVIADO", doc.id, "sucesso", mensagem

        return "PENDENTE", doc.id, None, None

    grupos, ordem = {}, []
    for solicitado in solicitados:
        nome = solicitado.nome_documento
        chave = "IDENTIDADE" if nome in GRUPOS_IDENTIDADE else nome

        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)

        status, documento_id, nivel_alerta, mensagem_feedback = status_do_item(solicitado.id)
        rotulo = ROTULOS_IDENTIDADE.get(nome) if chave == "IDENTIDADE" else None
        grupos[chave].append(
            {
                "solicitado_id": solicitado.id,
                "nome_documento": nome,
                "rotulo": rotulo,
                "obrigatorio": bool(solicitado.obrigatorio),
                "status": status,
                "documento_id": documento_id,
                "nivel_alerta": nivel_alerta,
                "mensagem_feedback": mensagem_feedback,
            }
        )

    resultado = []
    for chave in ordem:
        itens = grupos[chave]
        titulo, descricao_padrao = TITULOS_CHECKLIST.get(chave, (chave.title(), None))

        if any(item["status"] == "PROCESSANDO" for item in itens):
            status_geral_item = "PROCESSANDO"
            nivel_alerta_geral = None
        elif any(item["status"] in {"REJEITADO", "ERRO"} for item in itens):
            status_geral_item = "REJEITADO"
            nivel_alerta_geral = "erro"
        elif any(item["status"] == "ATENCAO" for item in itens):
            status_geral_item = "ATENCAO"
            nivel_alerta_geral = "aviso"
        elif all(item["status"] == "ENVIADO" for item in itens):
            status_geral_item = "ENVIADO"
            nivel_alerta_geral = "sucesso"
        elif any(item["status"] in {"ENVIADO", "ATENCAO"} for item in itens):
            status_geral_item = "PARCIAL"
            nivel_alerta_geral = None
        else:
            status_geral_item = "PENDENTE"
            nivel_alerta_geral = None

        mensagens_itens = [item["mensagem_feedback"] for item in itens if item["mensagem_feedback"]]
        mensagem_feedback_geral = " | ".join(mensagens_itens) if mensagens_itens else None

        resultado.append(
            {
                "chave": chave,
                "titulo": titulo,
                "descricao": descricao_padrao,
                "status": status_geral_item,
                "nivel_alerta": nivel_alerta_geral,
                "mensagem_feedback": mensagem_feedback_geral,
                "obrigatorio": any(item["obrigatorio"] for item in itens),
                "itens": itens,
            }
        )
    return resultado


@router.get("/{inscricao_id}/checklist")
def checklist_documentos(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
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
    membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()

    candidato_obj = db.get(Usuarios, inscricao.candidato_id)
    checklist_candidato = _gerar_checklist_para_pessoa(db, None, solicitados, enviados)
    
    membros_lista = []
    for membro in membros:
        membros_lista.append({
            "membro_id": membro.id,
            "nome_completo": membro.nome_completo,
            "parentesco": membro.parentesco,
            "checklist": _gerar_checklist_para_pessoa(db, membro.id, solicitados, enviados)
        })

    return {
        "candidato": {
            "nome_completo": candidato_obj.nome_completo if candidato_obj else "Candidato",
            "checklist": checklist_candidato
        },
        "membros": membros_lista
    }


@router.post("/{inscricao_id}/membros")
def adicionar_membro(
    inscricao_id: int,
    membro: MembroFamiliaIn,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

    novo_membro = MembrosFamilia(inscricao_id=inscricao_id, **membro.model_dump())
    db.add(novo_membro)
    db.commit()
    db.refresh(novo_membro)
    return novo_membro


@router.put("/{inscricao_id}/membros/{membro_id}")
def editar_membro(
    inscricao_id: int,
    membro_id: int,
    membro_in: MembroFamiliaIn,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")
        
    membro = db.query(MembrosFamilia).filter_by(id=membro_id, inscricao_id=inscricao_id).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Membro familiar não encontrado para esta inscrição.")

    membro.nome_completo = membro_in.nome_completo
    membro.cpf = membro_in.cpf
    membro.parentesco = membro_in.parentesco
    membro.renda_declarada = membro_in.renda_declarada
    db.commit()
    db.refresh(membro)
    return membro


@router.delete("/{inscricao_id}/membros/{membro_id}")
def remover_membro(
    inscricao_id: int,
    membro_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")
        
    membro = db.query(MembrosFamilia).filter_by(id=membro_id, inscricao_id=inscricao_id).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Membro familiar não encontrado para esta inscrição.")
    
    # Remover documentos associados ao membro (ou apenas desvincular)
    db.query(DocumentosEnviados).filter_by(membro_id=membro_id).delete()
    
    db.delete(membro)
    db.commit()
    return {"message": "Membro familiar removido com sucesso."}


@router.get("/{inscricao_id}/membros")
def listar_membros(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_VALIDADO)),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")
    return inscricao.membros_familia


def _coletar_documentos_auditoria(db: Session, enviados_pessoa, solicitado_por_id):
    documentos_com_analise = []
    partes_rg = []
    
    for doc in enviados_pessoa:
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
        
    return documentos_com_analise


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
    membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()

    solicitados = db.query(DocumentosSolicitados).filter_by(processo_id=inscricao.processo_id).all()
    obrigatorios = {s.id for s in solicitados if s.obrigatorio}
    solicitado_por_id = {s.id: s.nome_documento for s in solicitados}

    enviados = db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao_id).all()
    
    # 1. Checagem de documentos obrigatórios para o Candidato
    enviados_candidato = [d for d in enviados if d.membro_id is None]
    concluidos_candidato = {d.solicitado_id for d in enviados_candidato if d.status_processamento == "CONCLUIDO"}
    faltando_candidato = obrigatorios - concluidos_candidato
    
    mensagens_falta = []
    if faltando_candidato:
        nomes_faltando = [solicitado_por_id.get(sid, str(sid)) for sid in faltando_candidato]
        mensagens_falta.append(f"Candidato pendente: {', '.join(nomes_faltando)}")

    # 2. Checagem de documentos obrigatórios para os Membros
    for membro in membros:
        enviados_membro = [d for d in enviados if d.membro_id == membro.id]
        concluidos_membro = {d.solicitado_id for d in enviados_membro if d.status_processamento == "CONCLUIDO"}
        faltando_membro = obrigatorios - concluidos_membro
        if faltando_membro:
            nomes_faltando = [solicitado_por_id.get(sid, str(sid)) for sid in faltando_membro]
            mensagens_falta.append(f"Familiar '{membro.nome_completo}' pendente: {', '.join(nomes_faltando)}")

    # Se faltar documento em qualquer um, trava a auditoria na hora
    if mensagens_falta:
        inscricao.status_geral = "PENDENTE"
        inscricao.status_funil = StatusJornada.DOCS_PENDENTES
        inscricao.parecer = "Documentos obrigatórios pendentes:\n" + "\n".join(mensagens_falta)
        inscricao.inconsistencias = None
        db.commit()
        return {"status_geral": inscricao.status_geral, "parecer": inscricao.parecer}

    # 3. Coletar documentos para auditoria profunda
    docs_candidato_analise = _coletar_documentos_auditoria(db, enviados_candidato, solicitado_por_id)
    
    docs_membros_analise = {}
    for membro in membros:
        enviados_membro = [d for d in enviados if d.membro_id == membro.id]
        docs_membros_analise[membro.id] = _coletar_documentos_auditoria(db, enviados_membro, solicitado_por_id)

    resultado = auditar_inscricao(candidato, docs_candidato_analise, membros, docs_membros_analise, processo)

    inscricao.status_geral = resultado.status_geral
    inscricao.parecer = resultado.parecer
    inscricao.inconsistencias = (
        json.dumps(resultado.inconsistencias, ensure_ascii=False) if resultado.inconsistencias else None
    )
    inscricao.renda_per_capita_calculada = resultado.renda_per_capita
    inscricao.status_funil = StatusJornada.CONCLUIDO
    db.commit()
    db.refresh(inscricao)

    return {
        "status_geral": inscricao.status_geral,
        "parecer": inscricao.parecer,
        "inconsistencias": resultado.inconsistencias,
        "renda_per_capita_calculada": inscricao.renda_per_capita_calculada,
    }


@router.get("/{inscricao_id}/kyc")
def consultar_kyc(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("CANDIDATO")),
):
    """Dados necessários para a tela de validação inicial de identidade."""
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

    solicitados = (
        db.query(DocumentosSolicitados)
        .filter(
            DocumentosSolicitados.processo_id == inscricao.processo_id,
            DocumentosSolicitados.nome_documento.in_(("RG", "RG_VERSO", "CNH")),
        )
        .order_by(DocumentosSolicitados.id)
        .all()
    )
    ultimo_por_solicitado = {}
    for documento in (
        db.query(DocumentosEnviados)
        .filter_by(inscricao_id=inscricao.id, membro_id=None)
        .order_by(DocumentosEnviados.id.desc())
        .all()
    ):
        ultimo_por_solicitado.setdefault(documento.solicitado_id, documento)

    return {
        "inscricao_id": inscricao.id,
        "status_funil": inscricao.status_funil.value,
        "documentos": [
            {
                "solicitado_id": solicitado.id,
                "nome_documento": solicitado.nome_documento,
                "obrigatorio": bool(solicitado.obrigatorio),
                "documento_id": ultimo_por_solicitado[solicitado.id].id if solicitado.id in ultimo_por_solicitado else None,
                "status": ultimo_por_solicitado[solicitado.id].status_processamento if solicitado.id in ultimo_por_solicitado else "PENDENTE",
                "mensagem": ultimo_por_solicitado[solicitado.id].mensagem_erro if solicitado.id in ultimo_por_solicitado else None,
            }
            for solicitado in solicitados
        ],
    }


@router.post("/{inscricao_id}/kyc/concluir")
def concluir_kyc(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("CANDIDATO")),
):
    """Libera o grupo familiar após um RG ou CNH do titular ser validado."""
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")
    if inscricao.status_funil == StatusJornada.ABANDONO:
        raise HTTPException(status_code=403, detail="Esta inscrição foi abandonada e não pode avançar nas etapas.")

    identidade_validada = (
        db.query(DocumentosEnviados)
        .join(DocumentosSolicitados)
        .filter(
            DocumentosEnviados.inscricao_id == inscricao.id,
            DocumentosEnviados.membro_id.is_(None),
            DocumentosEnviados.status_processamento == "CONCLUIDO",
            DocumentosSolicitados.nome_documento.in_(("RG", "CNH")),
        )
        .first()
    )
    if identidade_validada is None:
        raise HTTPException(
            status_code=409,
            detail="Aguarde a validação de um RG ou CNH aprovado antes de continuar.",
        )

    inscricao.status_funil = StatusJornada.FAMILIA_PENDENTE
    db.add(inscricao)
    db.commit()
    return {
        "status_funil": inscricao.status_funil.value,
        "proxima_etapa": "FAMILIA",
        "mensagem": "Identidade validada. Você já pode informar o grupo familiar.",
    }


@router.get("/{inscricao_id}/detalhe")
def detalhe_inscricao(
    inscricao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(exigir_perfil("ANALISTA", "ADMIN")),
):
    inscricao = db.get(Inscricoes, inscricao_id)
    if not inscricao:
        raise HTTPException(status_code=404, detail="Inscricao nao encontrada")
    
    candidato = db.get(Usuarios, inscricao.candidato_id)
    membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()
    processo = db.get(ProcessosBolsa, inscricao.processo_id)

    enviados = db.query(DocumentosEnviados).filter_by(inscricao_id=inscricao_id).order_by(DocumentosEnviados.id.desc()).all()

    return {
        "inscricao": {
            "id": inscricao.id,
            "status_geral": inscricao.status_geral,
            "status_funil": inscricao.status_funil.value,
            "renda_per_capita_calculada": inscricao.renda_per_capita_calculada,
            "criado_em": inscricao.criado_em.isoformat() if inscricao.criado_em else None,
            "parecer": inscricao.parecer
        },
        "candidato": {
            "nome": candidato.nome_completo,
            "cpf": candidato.cpf,
            "email": candidato.email,
        },
        "processo": {
            "nome": processo.nome if processo else "N/A",
            "edital": "2026.2"
        },
        "membros": [
            {
                "id": m.id,
                "nome_completo": m.nome_completo,
                "cpf": m.cpf,
                "parentesco": m.parentesco,
                "renda_declarada": m.renda_declarada
            } for m in membros
        ],
        "documentos_enviados": [
            {
                "id": e.id,
                "solicitado_id": e.solicitado_id,
                "membro_id": e.membro_id,
                "status": e.status_processamento,
                "mensagem": e.mensagem_erro
            } for e in enviados
        ]
    }
