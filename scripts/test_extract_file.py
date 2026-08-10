"""Testar extração local de um arquivo existente em uploads/documentos.
Uso:
    python scripts\test_extract_file.py "uploads/documentos/arquivo.jpg" [categoria] [lado]
Exemplo:
    python scripts\test_extract_file.py "uploads/documentos/1_2_20260810114120_RG frente _1 (1).jpg" RG frente
"""
import sys
import os
import json

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.services.gemini_service import extrair_dados_documento, GeminiExtractionError

if len(sys.argv) < 2:
    print("Uso: python scripts\\test_extract_file.py <caminho_arquivo> [categoria] [lado]")
    sys.exit(2)

caminho = sys.argv[1]
categoria = sys.argv[2] if len(sys.argv) > 2 else "RG"
lado = sys.argv[3] if len(sys.argv) > 3 else "frente"

print(f"Testando extração: arquivo={caminho}, categoria={categoria}, lado={lado}")
try:
    resultado = extrair_dados_documento(caminho, categoria, lado=lado)
    print("Resultado JSON:")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
except GeminiExtractionError as exc:
    print("Erro de extração:", exc)
    sys.exit(1)
except Exception as exc:
    print("Erro inesperado:", exc)
    sys.exit(1)
