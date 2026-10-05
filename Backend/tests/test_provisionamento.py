from datetime import date
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from app.models import Base, DocumentosSolicitados, Inscricoes, ProcessosBolsa, Usuarios
from app.security import verificar_senha
from app.services.provisionamento import criar_esquema, preparar_processo_teste, criar_usuario


def test_init_repetido_preserva_dados(pg_engine):
    criar_esquema(pg_engine)
    with Session(pg_engine) as db:
        process = preparar_processo_teste(db)
        user = criar_usuario(db, 'candidato@example.invalid', 'SenhaFicticia!2026', 'CANDIDATO')
        db.add(Inscricoes(processo_id=process.id, candidato_id=user.id))
        db.commit()
        original = user.senha_hash
        first_id = process.id
    criar_esquema(pg_engine)
    with Session(pg_engine) as db:
        assert preparar_processo_teste(db).id == first_id
        with pytest.raises(ValueError, match='existente'):
            criar_usuario(db, 'CANDIDATO@example.invalid', 'OutraSenha!2026', 'ADMIN')
        db.rollback()
        user = db.scalar(select(Usuarios))
        assert user.senha_hash == original and user.perfil == 'CANDIDATO'
        assert verificar_senha('SenhaFicticia!2026', user.senha_hash)
        assert len(db.scalars(select(Inscricoes)).all()) == 1
        assert len(db.scalars(select(ProcessosBolsa)).all()) == 1
        docs = db.scalars(select(DocumentosSolicitados)).all()
        assert len(docs) == 5
        assert {d.nome_documento for d in docs if d.obrigatorio} == {'CNH'}
        assert db.scalar(select(ProcessosBolsa)).data_fim == date(2026, 12, 31)


def test_divergencia_recusada_antes_de_criar_ou_alterar(pg_engine):
    with pg_engine.begin() as conn:
        conn.execute(text('CREATE TABLE usuarios (id INTEGER PRIMARY KEY, senha_hash TEXT)'))
    with pytest.raises(ValueError, match='migração'):
        criar_esquema(pg_engine)
    assert inspect(pg_engine).get_table_names() == ['usuarios']
    assert {c['name'] for c in inspect(pg_engine).get_columns('usuarios')} == {'id', 'senha_hash'}


def test_senha_fraca_nao_cria_usuario(pg_engine):
    criar_esquema(pg_engine)
    with Session(pg_engine) as db:
        with pytest.raises(ValueError, match='senha|Senha'):
            criar_usuario(db, 'novo@example.invalid', 'curta', 'ADMIN')
        assert db.scalars(select(Usuarios)).all() == []


def test_divergencia_de_coluna_recusada(pg_engine):
    criar_esquema(pg_engine)
    with pg_engine.begin() as conn:
        conn.execute(text('ALTER TABLE usuarios ALTER COLUMN email DROP NOT NULL'))
    with pytest.raises(ValueError, match='migração'):
        criar_esquema(pg_engine)


@pytest.mark.parametrize('alteracao', [
    'ALTER TABLE inscricoes ALTER COLUMN status_funil DROP DEFAULT',
    'ALTER TABLE usuarios ALTER COLUMN id DROP DEFAULT',
])
def test_defaults_necessarios_ausentes_requerem_migracao(pg_engine, alteracao):
    criar_esquema(pg_engine)
    with pg_engine.begin() as conn:
        conn.execute(text(alteracao))
    with pytest.raises(ValueError, match='migração'):
        criar_esquema(pg_engine)


def test_candidato_provisionado_valida_identidade_e_avanca_kyc(pg_engine, monkeypatch):
    from app.routes import documentos
    from app.models import DocumentosEnviados, StatusJornada
    criar_esquema(pg_engine)
    with Session(pg_engine) as db:
        process = preparar_processo_teste(db)
        candidate = criar_usuario(db, 'integracao@example.com', 'SenhaFicticia!2026', 'CANDIDATO')
        inscription = Inscricoes(processo_id=process.id, candidato_id=candidate.id, status_funil=StatusJornada.KYC_PENDENTE)
        db.add(inscription)
        db.flush()
        requested = db.scalar(select(DocumentosSolicitados).where(DocumentosSolicitados.nome_documento == 'CNH'))
        doc = DocumentosEnviados(inscricao_id=inscription.id, solicitado_id=requested.id, status_processamento='PROCESSANDO_IA')
        db.add(doc)
        db.commit()
        ids = doc.id, inscription.id, candidate.id
    monkeypatch.setattr(documentos, 'SessionLocal', lambda: Session(pg_engine))
    monkeypatch.setattr(documentos, 'extrair_dados_documento', lambda *args: {
        'nome': 'Pessoa Ficticia de Teste', 'cpf': '11144477735', 'tipo_detectado': 'CNH', 'legibilidade': 95,
    })
    documentos._processar_ia_em_background(ids[0], b'ficticio', 'image/png', 'CNH', ids[1], ids[2], None)
    with Session(pg_engine) as db:
        assert db.get(DocumentosEnviados, ids[0]).status_processamento == 'CONCLUIDO'
        assert db.get(Usuarios, ids[2]).nome_completo == 'Pessoa Ficticia de Teste'
        assert db.get(Usuarios, ids[2]).cpf == '11144477735'
        assert db.get(Inscricoes, ids[1]).status_funil == StatusJornada.FAMILIA_PENDENTE
