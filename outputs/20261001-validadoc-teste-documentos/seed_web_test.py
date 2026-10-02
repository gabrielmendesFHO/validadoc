from datetime import date
import secrets
from app.db import SessionLocal
from app.models import Usuarios, ProcessosBolsa, DocumentosSolicitados, Inscricoes, StatusJornada
from app.security import hash_senha

with SessionLocal() as db:
    email = f"teste.web.{secrets.token_hex(4)}@example.invalid"
    password = secrets.token_urlsafe(18)
    user = Usuarios(nome_completo=f"Candidato ({email})", email=email,
                    senha_hash=hash_senha(password), perfil="CANDIDATO")
    process = ProcessosBolsa(nome="Validação web controlada 01/10/2026",
                            renda_per_capita_limite=1412, data_inicio=date(2026,1,1), data_fim=date(2026,12,31))
    db.add_all([user, process])
    db.flush()
    for category in ("RG", "RG_VERSO", "CNH", "RESIDENCIA", "HOLERITE"):
        db.add(DocumentosSolicitados(processo_id=process.id, nome_documento=category,
                                     obrigatorio=1 if category in ("RG", "CNH") else 0))
    entry = Inscricoes(processo_id=process.id, candidato_id=user.id,
                      status_funil=StatusJornada.PRE_CADASTRADO, status_geral="PENDENTE")
    db.add(entry)
    db.commit()
    print({"email":email,"senha":password,"inscricao_teste":entry.id})
