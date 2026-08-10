import json
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..db import get_db, serialize
from ..models import Inscricoes, DocumentosEnviados, AnalisesOcr, MembrosFamilia

router = APIRouter(prefix="/inscricoes", tags=["Consolidação"])


def _parse_date_ddmmyyyy(s: str):
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None


@router.get("/{inscricao_id}/parecer")
def consolidar_parecer(inscricao_id: int, db: Session = Depends(get_db)):
    inscricao: Inscricoes = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada")

    processo = inscricao.processo
    limite_pc = float(processo.renda_per_capita_limite) if processo.renda_per_capita_limite is not None else None

    # Carrega membros e rendas declaradas
    membros: List[MembrosFamilia] = db.query(MembrosFamilia).filter(MembrosFamilia.inscricao_id == inscricao_id).all()
    membros_renda_sum = sum(float(m.renda_declarada or 0) for m in membros)
    household_size = 1 + len(membros)

    # Carrega análises OCR dos documentos enviados dessa inscrição
    documentos = db.query(DocumentosEnviados).filter(DocumentosEnviados.inscricao_id == inscricao_id).all()

    analises = []
    for doc in documentos:
        for a in doc.analises_ocr:
            # parse JSON safely
            try:
                dados = json.loads(a.dados_extraidos) if a.dados_extraidos else {}
            except Exception:
                dados = {}
            analises.append({
                "categoria": doc.solicitado.nome_documento if doc.solicitado else None,
                "dados": dados,
                "taxa_confianca": a.taxa_confianca,
                "status_auditoria": a.status_auditoria,
            })

    # Regras de negócio
    motivos = []
    apto = True

    # 1) Cruzamento de identidade: nomes e CPF (se presentes) devem bater entre documentos
    nomes = []
    cpfs = []
    for a in analises:
        d = a["dados"]
        if not d:
            continue
        # possíveis campos de nome conforme tipo
        for k in ("nome", "nome_titular", "nome_completo"):
            v = d.get(k)
            if v:
                nomes.append(v.strip().lower())
        cpf = d.get("cpf")
        if cpf:
            cpfs.append(cpf.strip())

    # se houver pelo menos um cpf diferente -> divergência
    if cpfs:
        if len(set(cpfs)) > 1:
            motivos.append("CPF divergente entre documentos")
            apto = False
    # nomes: se houver pelo menos dois nomes extraídos e eles divergem (levemente), sinalizar
    if len(nomes) >= 2:
        normalized = list({n for n in nomes})
        if len(normalized) > 1:
            motivos.append("Nomes divergentes entre documentos")
            apto = False

    # 2) Renda: holerite renda_bruta >= renda_liquida
    renda_bruta = None
    renda_liquida = None
    for a in analises:
        if (a["categoria"] or "").upper() == "HOLERITE":
            d = a["dados"]
            if d:
                if d.get("renda_bruta") is not None:
                    renda_bruta = float(d.get("renda_bruta"))
                if d.get("renda_liquida") is not None:
                    renda_liquida = float(d.get("renda_liquida"))
    if renda_bruta is not None and renda_liquida is not None:
        if renda_bruta + 0.0 < renda_liquida - 1e-6:
            motivos.append("Renda bruta menor que renda líquida no holerite")
            apto = False

    # 3) Validade temporal
    hoje = datetime.now().date()
    # residencia: emissao até 90 dias
    for a in analises:
        if (a["categoria"] or "").upper() == "RESIDENCIA":
            d = a["dados"]
            data_emissao = d.get("data_emissao") if d else None
            if data_emissao:
                dt = _parse_date_ddmmyyyy(data_emissao)
                if dt is None:
                    motivos.append("Data de emissão do comprovante de residência em formato inválido")
                    apto = False
                else:
                    if (hoje - dt).days > 90:
                        motivos.append("Comprovante de residência muito antigo (>90 dias)")
                        apto = False
    # holerite: competencia até 60 dias
    for a in analises:
        if (a["categoria"] or "").upper() == "HOLERITE":
            d = a["dados"]
            competencia = d.get("competencia") if d else None
            if competencia:
                try:
                    # competencia ex: MM/YYYY or DD/MM/YYYY — tenta extrair mês/ano
                    parts = competencia.split("/")
                    if len(parts) == 2:
                        comp_dt = datetime(int(parts[1]), int(parts[0]), 1).date()
                    else:
                        comp_dt = datetime.strptime(competencia, "%d/%m/%Y").date()
                except Exception:
                    motivos.append("Competência do holerite em formato inválido")
                    apto = False
                    comp_dt = None
                if comp_dt:
                    if (hoje - comp_dt).days > 60:
                        motivos.append("Holerite fora da janela aceita (>60 dias)")
                        apto = False
    # RG: validade (quando presente)
    for a in analises:
        if (a["categoria"] or "").upper() == "RG":
            d = a["dados"]
            if d:
                validade = d.get("data_validade") or d.get("data_expedicao")
                if validade:
                    dt = _parse_date_ddmmyyyy(validade)
                    if dt is None:
                        motivos.append("Data de validade/expedição do RG em formato inválido")
                        apto = False
                    else:
                        # se existir campo data_validade e for anterior a hoje => inválido
                        if d.get("data_validade") and dt < hoje:
                            motivos.append("RG vencido")
                            apto = False

    # 4) Teto de elegibilidade: renda per capita
    renda_total = membros_renda_sum + (renda_liquida or 0)
    if limite_pc is not None:
        renda_pc = renda_total / household_size if household_size > 0 else renda_total
        if renda_pc > limite_pc + 1e-6:
            motivos.append(f"Renda per capita {renda_pc:.2f} acima do limite {limite_pc:.2f}")
            apto = False

    resposta = {
        "inscricao_id": inscricao_id,
        "apto": apto,
        "motivos": motivos,
        "detalhes": {
            "renda_total": renda_total,
            "renda_per_capita_calculada": round(renda_total / household_size, 2) if household_size > 0 else None,
            "limite_renda_per_capita": limite_pc,
            "renda_bruta_holerite": renda_bruta,
            "renda_liquida_holerite": renda_liquida,
            "nomes_extraidos": nomes,
            "cpfs_extraidos": cpfs,
        },
    }

    return resposta
