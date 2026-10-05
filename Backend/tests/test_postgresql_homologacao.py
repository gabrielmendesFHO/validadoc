from datetime import datetime
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import DocumentoBinario, DocumentosEnviados, DocumentosSolicitados, Inscricoes, StatusJornada
from app.services.provisionamento import criar_esquema, preparar_processo_teste, criar_usuario


def test_pg_persistencia_enum_binario_e_atualizacao_atividade(pg_engine):
    criar_esquema(pg_engine)
    fernet = Fernet(Fernet.generate_key())
    payload = b'DOCUMENTO FICTICIO PARA HOMOLOGACAO'
    with Session(pg_engine) as db:
        process = preparar_processo_teste(db)
        user = criar_usuario(db, 'persistencia@example.invalid', 'SenhaFicticia!2026', 'CANDIDATO')
        inscription = Inscricoes(processo_id=process.id, candidato_id=user.id,
                                 ultima_atividade=datetime(2000, 1, 1))
        db.add(inscription)
        db.flush()
        requested = db.scalar(select(DocumentosSolicitados).where(DocumentosSolicitados.nome_documento == 'CNH'))
        document = DocumentosEnviados(inscricao_id=inscription.id, solicitado_id=requested.id)
        db.add(document)
        db.flush()
        db.add(DocumentoBinario(documento_id=document.id, conteudo_criptografado=fernet.encrypt(payload),
                               nome_arquivo_original='ficticio.txt', mime_type='text/plain', tamanho_bytes=len(payload)))
        db.commit()
        inscription.status_funil = StatusJornada.KYC_PENDENTE
        db.commit()
        inscription_id = inscription.id
    with Session(pg_engine) as db:
        persisted = db.get(Inscricoes, inscription_id)
        assert persisted.status_funil == StatusJornada.KYC_PENDENTE
        assert persisted.ultima_atividade > datetime(2026, 1, 1)
        binary = db.scalar(select(DocumentoBinario))
        assert fernet.decrypt(binary.conteudo_criptografado) == payload
