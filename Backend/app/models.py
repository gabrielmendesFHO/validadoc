import enum
from sqlalchemy import (
    Column,
    Date,
    DECIMAL,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# --- ENUMS DE REGRA DE NEGÓCIO ---

class StatusJornada(str, enum.Enum):
    PRE_CADASTRADO = "PRE_CADASTRADO"
    KYC_PENDENTE = "KYC_PENDENTE"
    KYC_VALIDADO = "KYC_VALIDADO"
    FAMILIA_PENDENTE = "FAMILIA_PENDENTE"
    DOCS_PENDENTES = "DOCS_PENDENTES"
    PRONTO_AUDITORIA = "PRONTO_AUDITORIA"
    CONCLUIDO = "CONCLUIDO"
    ABANDONO = "ABANDONO"


# --- MODELOS DE BANCO DE DADOS ---

class Instituicoes(Base):
    __tablename__ = "instituicoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    endereco = Column(String(255), nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    processos = relationship("ProcessosBolsa", back_populates="instituicao")
    usuarios = relationship("Usuarios", back_populates="instituicao")


class ProcessosBolsa(Base):
    __tablename__ = "processos_bolsa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instituicao_id = Column(Integer, ForeignKey("instituicoes.id"), nullable=True)
    nome = Column(String(255), nullable=False)
    renda_per_capita_limite = Column(DECIMAL(10, 2), nullable=True)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    instituicao = relationship("Instituicoes", back_populates="processos")
    documentos_solicitados = relationship("DocumentosSolicitados", back_populates="processo")
    inscricoes = relationship("Inscricoes", back_populates="processo")


class DocumentosSolicitados(Base):
    __tablename__ = "documentos_solicitados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    processo_id = Column(Integer, ForeignKey("processos_bolsa.id"), nullable=False)
    nome_documento = Column(
        Enum("RG", "RG_VERSO", "CNH", "RESIDENCIA", "HOLERITE", "OUTRO", name="documento_categoria"),
        nullable=False,
    )
    obrigatorio = Column(Integer, nullable=False, server_default=text("0"))
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    processo = relationship("ProcessosBolsa", back_populates="documentos_solicitados")
    documentos_enviados = relationship("DocumentosEnviados", back_populates="solicitado")


class Usuarios(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_completo = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(
        Enum("CANDIDATO", "ANALISTA", "ADMIN", name="perfil_enum"),
        nullable=False,
        server_default=text("'CANDIDATO'"),
    )
    cpf = Column(String(14), nullable=True)
    instituicao_id = Column(Integer, ForeignKey("instituicoes.id"), nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    instituicao = relationship("Instituicoes", back_populates="usuarios")
    inscricoes = relationship("Inscricoes", back_populates="candidato")


class Inscricoes(Base):
    __tablename__ = "inscricoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    processo_id = Column(Integer, ForeignKey("processos_bolsa.id"), nullable=False)
    candidato_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # --- NOVAS COLUNAS DO FUNIL DE CONVERSÃO ---
    status_funil = Column(
        Enum(StatusJornada, name="status_jornada_enum"), 
        nullable=False, 
        server_default=text("'PRE_CADASTRADO'")
    )
    ultima_atividade = Column(
        TIMESTAMP, 
        nullable=False, 
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )
    ultimo_acesso = Column(TIMESTAMP, nullable=True)
    alertas_dificuldade = Column(Integer, nullable=False, server_default=text("0"))
    # -------------------------------------------

    status_geral = Column(String(50), nullable=False, server_default=text("'PENDENTE'"))
    renda_per_capita_calculada = Column(DECIMAL(10, 2), nullable=True)
    parecer = Column(Text, nullable=True)
    inconsistencias = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    processo = relationship("ProcessosBolsa", back_populates="inscricoes")
    candidato = relationship("Usuarios", back_populates="inscricoes")
    documentos_enviados = relationship("DocumentosEnviados", back_populates="inscricao")
    membros_familia = relationship("MembrosFamilia", back_populates="inscricao")


class MembrosFamilia(Base):
    __tablename__ = "membros_familia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inscricao_id = Column(Integer, ForeignKey("inscricoes.id"), nullable=False)
    nome_completo = Column(String(255), nullable=False)
    cpf = Column(String(14), nullable=True)
    parentesco = Column(String(50), nullable=True)
    renda_declarada = Column(DECIMAL(10, 2), nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    inscricao = relationship("Inscricoes", back_populates="membros_familia")


class DocumentosEnviados(Base):
    __tablename__ = "documentos_enviados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inscricao_id = Column(Integer, ForeignKey("inscricoes.id"), nullable=False)
    solicitado_id = Column(Integer, ForeignKey("documentos_solicitados.id"), nullable=False)
    membro_id = Column(Integer, ForeignKey("membros_familia.id"), nullable=True)
    status_processamento = Column(String(50), nullable=False, server_default=text("'PENDENTE'"))
    mensagem_erro = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    inscricao = relationship("Inscricoes", back_populates="documentos_enviados")
    solicitado = relationship("DocumentosSolicitados", back_populates="documentos_enviados")
    membro = relationship("MembrosFamilia")
    analises_ocr = relationship("AnalisesOcr", back_populates="documento")
    binario = relationship("DocumentoBinario", back_populates="documento", uselist=False)


class DocumentoBinario(Base):
    __tablename__ = "documentos_binarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos_enviados.id"), nullable=False, unique=True)
    conteudo_criptografado = Column(LargeBinary, nullable=False)
    nome_arquivo_original = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    tamanho_bytes = Column(Integer, nullable=False)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    documento = relationship("DocumentosEnviados", back_populates="binario")


class AnalisesOcr(Base):
    __tablename__ = "analises_ocr"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos_enviados.id"), nullable=False)
    dados_extraidos = Column(Text, nullable=True)
    taxa_confianca = Column(Float, nullable=True)
    status_auditoria = Column(String(20), nullable=False, server_default=text("'PENDENTE'"))
    parecer = Column(Text, nullable=True)
    inconsistencias = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    documento = relationship("DocumentosEnviados", back_populates="analises_ocr")
