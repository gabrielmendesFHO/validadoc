import csv
import secrets
from io import StringIO

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import exigir_perfil
from ..models import Inscricoes, ProcessosBolsa, StatusJornada, Usuarios
from ..security import hash_senha
from ..services.regras_negocio import _normalizar_cpf
from ..services.email_service import enviar_email_boas_vindas

router = APIRouter(prefix="/api/v1/integracao", tags=["Integração ERP"])


class PreCadastroERPIn(BaseModel):
    nome_completo: str | None = None
    nome: str | None = None
    email: EmailStr
    cpf: str
    telefone: str | None = None
    celular: str | None = None
    data_nascimento: str | None = None
    matricula: str | None = None
    ra: str | None = None
    curso: str | None = None
    campus: str | None = None
    turno: str | None = None
    semestre: str | int | None = None
    instituicao_id: int | None = None
    processo_id: int | None = None
    evento: str | None = None
    origem: str | None = None

    model_config = {
        "extra": "allow"
    }

    @property
    def nome_efetivo(self) -> str:
        valor = self.nome_completo or self.nome
        if not valor or not valor.strip():
            raise ValueError("O campo 'nome_completo' ou 'nome' é obrigatório.")
        return valor.strip()


def _processar_candidato(dados: PreCadastroERPIn, db: Session):
    """Função central reutilizável para processar a lógica de negócio do pré-cadastro."""
    try:
        nome_candidato = dados.nome_efetivo
    except ValueError as err:
        raise ValueError(str(err))

    digitos_cpf = _normalizar_cpf(dados.cpf)
    if not digitos_cpf or len(digitos_cpf) != 11:
        raise ValueError("CPF inválido. Deve conter 11 dígitos numéricos.")

    cpf_formatado = f"{digitos_cpf[:3]}.{digitos_cpf[3:6]}.{digitos_cpf[6:9]}-{digitos_cpf[9:]}"
    email_limpo = str(dados.email).lower().strip()

    # Busca usuário existente por CPF (formatado ou apenas dígitos) ou por e-mail
    usuario = (
        db.query(Usuarios)
        .filter(
            (Usuarios.cpf == cpf_formatado)
            | (Usuarios.cpf == digitos_cpf)
            | (Usuarios.email == email_limpo)
        )
        .first()
    )

    novo_usuario = False
    senha_provisoria_gerada = None
    if usuario is None:
        senha_provisoria_gerada = secrets.token_urlsafe(16)
        usuario = Usuarios(
            nome_completo=nome_candidato,
            email=email_limpo,
            senha_hash=hash_senha(senha_provisoria_gerada),
            perfil="CANDIDATO",
            cpf=cpf_formatado,
            instituicao_id=dados.instituicao_id or 1,
        )
        db.add(usuario)
        db.flush()
        novo_usuario = True
    else:
        # Atualiza dados ausentes caso necessário
        if not usuario.cpf:
            usuario.cpf = cpf_formatado
        if not usuario.instituicao_id and dados.instituicao_id:
            usuario.instituicao_id = dados.instituicao_id
        novo_usuario = False

    # Vincula ao processo seletivo de bolsa ativo ou especificado
    if dados.processo_id:
        processo = db.get(ProcessosBolsa, dados.processo_id)
    else:
        processo = (
            db.query(ProcessosBolsa)
            .order_by(ProcessosBolsa.id.desc())
            .first()
        )

    inscricao = None
    if processo:
        inscricao = (
            db.query(Inscricoes)
            .filter_by(candidato_id=usuario.id, processo_id=processo.id)
            .first()
        )
        if inscricao is None:
            inscricao = Inscricoes(
                processo_id=processo.id,
                candidato_id=usuario.id,
                status_funil=StatusJornada.PRE_CADASTRADO,
                status_geral="PENDENTE",
            )
            db.add(inscricao)
            db.flush()

    return novo_usuario, usuario, inscricao, senha_provisoria_gerada


@router.post("/pre-cadastro", status_code=status.HTTP_201_CREATED)
def pre_cadastro_webhook(
    dados: PreCadastroERPIn,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ADMIN", "ANALISTA")),
):
    """Recebe dados de pré-cadastro de estudantes via Webhook do ERP da faculdade.

    Requer autenticação com perfil ADMIN ou ANALISTA.
    """
    try:
        novo_usuario, usuario, inscricao, senha_prov = _processar_candidato(dados, db)
        
        if novo_usuario and senha_prov:
            background_tasks.add_task(
                enviar_email_boas_vindas,
                email_destino=usuario.email,
                nome_candidato=usuario.nome_completo,
                senha_temporaria=senha_prov
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    db.commit()
    db.refresh(usuario)
    if inscricao:
        db.refresh(inscricao)

    response.status_code = status.HTTP_201_CREATED if novo_usuario else status.HTTP_200_OK

    return {
        "sucesso": True,
        "mensagem": "Pré-cadastro realizado com sucesso." if novo_usuario else "Pré-cadastro atualizado com sucesso.",
        "status_jornada": StatusJornada.PRE_CADASTRADO.value,
        "novo_usuario": novo_usuario,
        "usuario": {
            "id": usuario.id,
            "nome_completo": usuario.nome_completo,
            "email": usuario.email,
            "cpf": usuario.cpf,
            "perfil": usuario.perfil,
            "instituicao_id": usuario.instituicao_id,
        },
        "inscricao": {
            "id": inscricao.id,
            "processo_id": inscricao.processo_id,
            "status_geral": inscricao.status_geral,
        } if inscricao else None,
        "dados_academicos": {
            "matricula": dados.matricula or dados.ra,
            "curso": dados.curso,
            "campus": dados.campus,
            "turno": dados.turno,
            "semestre": dados.semestre,
        } if any([dados.matricula, dados.ra, dados.curso, dados.campus, dados.turno, dados.semestre]) else None,
    }


@router.post("/upload-csv", status_code=status.HTTP_200_OK)
def upload_csv_pre_cadastro(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _usuario: Usuarios = Depends(exigir_perfil("ADMIN", "ANALISTA")),
):
    """Lê um arquivo CSV contendo dados de estudantes e insere/atualiza os pré-cadastros em lote.

    Requer autenticação com perfil ADMIN ou ANALISTA.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="O arquivo deve ser do tipo CSV (.csv).")

    try:
        conteudo = file.file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            file.file.seek(0)
            conteudo = file.file.read().decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Erro de codificação ao ler o arquivo CSV. Tente salvar como UTF-8.",
            )

    reader = csv.DictReader(StringIO(conteudo), delimiter=",")
    # Caso os CSVs usem ponto e vírgula como delimitador (padrão PT-BR no Excel)
    if reader.fieldnames and ";" in reader.fieldnames[0]:
        reader = csv.DictReader(StringIO(conteudo), delimiter=";")

    resultados = {
        "sucesso": True,
        "total_processados": 0,
        "novos_usuarios": 0,
        "usuarios_atualizados": 0,
        "erros": [],
    }

    for linha_num, linha in enumerate(reader, start=2):  # linha 1 = cabeçalho
        resultados["total_processados"] += 1

        # Limpar chaves e valores brancos
        linha_limpa = {k.strip(): v.strip() for k, v in linha.items() if k and v}

        # Pular linhas completamente vazias
        if not linha_limpa:
            resultados["total_processados"] -= 1
            continue

        try:
            dados_entrada = PreCadastroERPIn(**linha_limpa)
            novo_usuario, usuario, inscricao, senha_prov = _processar_candidato(dados_entrada, db)

            if novo_usuario:
                resultados["novos_usuarios"] += 1
                if senha_prov:
                    background_tasks.add_task(
                        enviar_email_boas_vindas,
                        email_destino=usuario.email,
                        nome_candidato=usuario.nome_completo,
                        senha_temporaria=senha_prov,
                    )
            else:
                resultados["usuarios_atualizados"] += 1

        except ValidationError as e:
            msg_erro = ", ".join([f"{err['loc'][-1]}: {err['msg']}" for err in e.errors()])
            resultados["erros"].append({
                "linha": linha_num,
                "email": linha_limpa.get("email"),
                "erro": f"Erro de validação: {msg_erro}",
            })
        except ValueError as e:
            resultados["erros"].append({
                "linha": linha_num,
                "email": linha_limpa.get("email"),
                "erro": str(e),
            })
        except Exception as e:
            resultados["erros"].append({
                "linha": linha_num,
                "email": linha_limpa.get("email"),
                "erro": f"Erro interno: {str(e)}",
            })

    # Comita todos os registros que foram processados com sucesso
    db.commit()

    if resultados["erros"]:
        resultados["sucesso"] = False

    return resultados
