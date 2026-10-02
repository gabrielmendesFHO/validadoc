"""Rodada isolada de validação, sem gravar documentos no banco local do usuário."""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import DefaultClause, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    AnalisesOcr,
    Base,
    DocumentosSolicitados,
    Inscricoes,
    MembrosFamilia,
    ProcessosBolsa,
    StatusJornada,
    Usuarios,
)
from app.routes import documentos, inscricoes, operacional


SOURCE = Path(r"C:\Users\gabri\OneDrive\Documentos\TCC")
RESULTS = Path(__file__).with_name("resultados_rodada_20261001.json")
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False)
default_mysql = Inscricoes.__table__.c.ultima_atividade.server_default
Inscricoes.__table__.c.ultima_atividade.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))
try:
    Base.metadata.create_all(engine)
finally:
    Inscricoes.__table__.c.ultima_atividade.server_default = default_mysql

with TestingSession() as db:
    db.add(ProcessosBolsa(id=1, nome="Processo de teste", renda_per_capita_limite=1412,
                           data_inicio=date(2026, 1, 1), data_fim=date(2026, 12, 31)))
    db.add_all([
        DocumentosSolicitados(id=1, processo_id=1, nome_documento="RG", obrigatorio=1),
        DocumentosSolicitados(id=2, processo_id=1, nome_documento="CNH", obrigatorio=1),
        DocumentosSolicitados(id=3, processo_id=1, nome_documento="RESIDENCIA", obrigatorio=1),
        DocumentosSolicitados(id=4, processo_id=1, nome_documento="HOLERITE", obrigatorio=0),
    ])
    db.add_all([
        Usuarios(id=1, nome_completo="Candidato (teste A)", email="teste-a@example.invalid", senha_hash="x", perfil="CANDIDATO"),
        Usuarios(id=2, nome_completo="Candidato (teste B)", email="teste-b@example.invalid", senha_hash="x", perfil="CANDIDATO"),
        Usuarios(id=3, nome_completo="Analista teste", email="analista@example.invalid", senha_hash="x", perfil="ANALISTA"),
    ])
    db.add_all([
        Inscricoes(id=1, processo_id=1, candidato_id=1, status_funil=StatusJornada.PRE_CADASTRADO, status_geral="PENDENTE"),
        Inscricoes(id=2, processo_id=1, candidato_id=2, status_funil=StatusJornada.PRE_CADASTRADO, status_geral="PENDENTE"),
    ])
    db.add(MembrosFamilia(id=1, inscricao_id=2, nome_completo="Familiar de teste", parentesco="IRMÃO"))
    db.commit()

app = FastAPI()
app.include_router(documentos.router)
app.include_router(inscricoes.router)
app.include_router(operacional.router)
active_user = {"id": 1}


def db_session():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def current_user():
    with TestingSession() as db:
        return db.get(Usuarios, active_user["id"])


app.dependency_overrides[get_db] = db_session
app.dependency_overrides[get_current_user] = current_user
documentos.SessionLocal = TestingSession
client = TestClient(app)
results = []


def record(case_id, response, expected, *, document_id=None, note=""):
    status = response.status_code
    payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
    doc_status = None
    if document_id is not None:
        state = client.get(f"/documentos/{document_id}/status")
        if state.status_code == 200:
            doc_status = state.json().get("status")
    item = {"id": case_id, "http": status, "esperado_http": expected,
            "documento_id": document_id, "status_documento": doc_status,
            "observacao": note}
    if case_id == "T23":
        item["status_auditoria"] = payload.get("status_geral")
    results.append(item)
    print(json.dumps(item, ensure_ascii=False), flush=True)
    return payload


def upload(case_id, source, solicitado_id=1, membro_id=None, filename=None, content=None, expected=202):
    data = {"inscricao_id": "1", "solicitado_id": str(solicitado_id)}
    if membro_id is not None:
        data["membro_id"] = str(membro_id)
    blob = content if content is not None else source.read_bytes()
    name = filename or (source.name if source else "arquivo.jpg")
    response = client.post("/documentos/upload", data=data, files={"file": (name, blob)})
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    return record(case_id, response, expected, document_id=payload.get("documento_id"))


if os.getenv("FOCUS_IDENTITY") == "1":
    own = SOURCE / "doc-gabriel-mendes" / "CNH_DIG_GA.pdf"
    other = SOURCE / "doc-gustavo-paes" / "CNH_ZERO_BOA.jpg"
    first_upload = upload("T05", own, solicitado_id=2)
    second_upload = upload("T07", other, solicitado_id=2)
    with TestingSession() as db:
        user = db.get(Usuarios, 1)
        identity_ready = bool(user.cpf) and not user.nome_completo.startswith("Candidato (")
        extracted = []
        for document_id in (first_upload.get("documento_id"), second_upload.get("documento_id")):
            analysis = db.query(AnalisesOcr).filter_by(documento_id=document_id).first()
            extracted.append(json.loads(analysis.dados_extraidos) if analysis and analysis.dados_extraidos else {})
        cpf_a = re.sub(r"\D", "", extracted[0].get("cpf") or "")
        cpf_b = re.sub(r"\D", "", extracted[1].get("cpf") or "")
        name_a = " ".join((extracted[0].get("nome") or "").upper().split())
        name_b = " ".join((extracted[1].get("nome") or "").upper().split())
        different = bool((cpf_a and cpf_b and cpf_a != cpf_b) or (name_a and name_b and name_a != name_b))
    result = {"referencia_titular_confirmada": identity_ready, "identidades_diferentes": different,
              "primeiro_status": results[0]["status_documento"], "segundo_status": results[1]["status_documento"]}
    results.append({"comparacao": result})
    print(json.dumps(result, ensure_ascii=False), flush=True)
    RESULTS.with_name("resultados_identidade_20261001.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    engine.dispose()
    sys.exit(0)


try:
    heif = SOURCE / "doc-gustavo-paes" / "CNH_ZERO_RUIM.heif"
    rg = SOURCE / "doc-gabriel-mendes" / "RG_FRENTE_GA.jpg"
    cnh_other = SOURCE / "doc-gustavo-paes" / "CNH_ZERO_BOA.jpg"
    residence = SOURCE / "doc-gabriel-mendes" / "RES_GA.jpg"

    upload("T09", heif, expected=400)
    upload("T10", None, filename="vazio.jpg", content=b"", expected=400)
    upload("T11", None, filename="grande.jpg", content=b"0" * (15 * 1024 * 1024 + 1), expected=413)

    active_user["id"] = 2
    upload("T14", rg, expected=403)
    active_user["id"] = 1
    upload("T15", rg, membro_id=1, expected=400)
    upload("T16", rg, solicitado_id=999, expected=400)
    record("T31", client.get("/auditoria/1"), 403)

    identity = upload("T03", rg)
    identity_id = identity.get("documento_id")
    upload("T12", rg, solicitado_id=2, expected=422)
    active_user["id"] = 2
    record("T32", client.get(f"/documentos/{identity_id}/arquivo"), 403)
    active_user["id"] = 1

    upload("T07", cnh_other, solicitado_id=2)
    active_user["id"] = 3
    upload("T21", residence, solicitado_id=3)
    record("T23", client.post("/inscricoes/1/auditar"), 200)
    response = client.get("/auditoria/1")
    payload = record("T25", response, 200)
    results[-1]["documentos_na_tela"] = len(payload.get("documentos", []))

finally:
    RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    engine.dispose()
