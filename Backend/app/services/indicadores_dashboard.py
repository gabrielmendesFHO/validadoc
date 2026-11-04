"""Critérios comuns ao contador, à listagem e ao resumo operacional."""
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import aliased

from ..models import DocumentosEnviados, Inscricoes

STATUS_COM_ERRO = {"REJEITADO", "ERRO_EXTRACAO"}


def _sem_envio_posterior(documento):
    posterior = aliased(DocumentosEnviados)
    return ~exists(
        select(posterior.id).where(
            posterior.inscricao_id == documento.inscricao_id,
            posterior.solicitado_id == documento.solicitado_id,
            posterior.membro_id.is_not_distinct_from(documento.membro_id),
            or_(
                posterior.criado_em > documento.criado_em,
                and_(posterior.criado_em == documento.criado_em, posterior.id > documento.id),
            ),
        ).correlate(documento)
    )


def criterio_dificuldade():
    documento = aliased(DocumentosEnviados)
    erro_atual = exists(
        select(documento.id).where(
            documento.inscricao_id == Inscricoes.id,
            documento.status_processamento.in_(STATUS_COM_ERRO),
            _sem_envio_posterior(documento),
        ).correlate(Inscricoes)
    )
    return or_(Inscricoes.alertas_dificuldade > 0, erro_atual)


def documentos_vigentes(db, inscricao_id):
    return db.query(DocumentosEnviados).filter(
        DocumentosEnviados.inscricao_id == inscricao_id,
        _sem_envio_posterior(DocumentosEnviados),
    ).all()
