"""Script de diagnóstico para testar conexão com o Gemini (executar localmente).

Este script carrega as mesmas configurações da aplicação (app.config.settings)
 e tenta fazer uma requisição mínima ao modelo configurado. Ele imprime
 mensagens legíveis para ajudar a identificar problemas de chave/permissaos.

USO (PowerShell):
    cd <repo>
    .\venv\Scripts\Activate
    pip install -r requirements.txt
    python scripts\check_gemini.py

Observacao: execute este script localmente — nunca cole a chave da API em chats.
"""
from app.config import settings
import sys
import json

try:
    from google import genai
    from google.genai import types
except Exception as e:
    print("SDK do Google (google-genai) nao encontrado. Rode: pip install google-genai")
    sys.exit(2)

if not settings.gemini_api_key:
    print("GEMINI_API_KEY nao esta configurada no .env. Configure e tente novamente.")
    sys.exit(2)

print("Usando modelo:", settings.gemini_model)

try:
    client = genai.Client(api_key=settings.gemini_api_key)
except Exception as exc:
    print("Falha ao inicializar o client do Gemini:", exc)
    sys.exit(1)

# requisição simples para verificar autenticacao/permissaos
try:
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=["Verificacao de conectividade: responda apenas 'pong' em texto curto."],
        config=types.GenerateContentConfig(response_mime_type="text/plain", temperature=0.0),
    )
    # Alguns SDKs retornam .text, outros .content; imprimimos o que vier
    text = getattr(response, "text", None) or getattr(response, "content", None) or json.dumps(response)
    print("Resposta recebida do Gemini:")
    print(text)
    print("Conexao com Gemini bem sucedida.")
    sys.exit(0)
except Exception as exc:
    msg = str(exc)
    print("Erro ao chamar o Gemini:")
    print(msg)
    print("Sugestoes: \n - Verifique GEMINI_API_KEY no .env\n - Ative a API 'Generative Language' no Google Cloud\n - Confirme billing no projeto\n - Remova restricoes temporariamente na chave (IP/Referrer) para teste")
    sys.exit(1)
