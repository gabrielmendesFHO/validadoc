"""Seleção dos envios vigentes sem remover versões anteriores dos documentos."""
from datetime import datetime


def ultimos_documentos(enviados):
    """Seleciona o último envio por inscrição, pessoa e documento solicitado."""
    ultimos = {}
    for documento in enviados:
        chave = (documento.inscricao_id, documento.membro_id, documento.solicitado_id)
        anterior = ultimos.get(chave)
        ordem = (documento.criado_em or datetime.min, documento.id)
        if anterior is None or ordem > (anterior.criado_em or datetime.min, anterior.id):
            ultimos[chave] = documento
    return list(ultimos.values())
