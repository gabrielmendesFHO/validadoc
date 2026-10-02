"""Diagnóstico sem imprimir conteúdo dos documentos ou a chave da API."""

from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings
from app.services.gemini_service import _SCHEMAS_E_PROMPTS
from app.services.image_processing import preparar_para_ia_multimodal


root = Path(r"C:\Users\gabri\OneDrive\Documentos\TCC")
cases = [
    ("RG frente", root / "doc-gabriel-mendes" / "RG_FRENTE_GA.jpg", "RG", "image/jpeg"),
    ("CNH PDF", root / "doc-gabriel-mendes" / "CNH_DIG_GA.pdf", "CNH", "application/pdf"),
]
client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=30000))

for label, path, category, mime in cases:
    raw = path.read_bytes()
    processed, processed_mime = preparar_para_ia_multimodal(raw, path.name, mime)
    spec = _SCHEMAS_E_PROMPTS[category]
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[spec["prompt"], types.Part.from_bytes(data=processed, mime_type=processed_mime)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=spec["schema"],
                temperature=0.1,
            ),
        )
        print({"caso": label, "modelo": settings.gemini_model,
               "resultado": "ok", "texto_presente": bool(response.text)}, flush=True)
    except Exception as exc:
        message = str(exc).replace(settings.gemini_api_key, "[redacted]")
        print({"caso": label, "modelo": settings.gemini_model,
               "resultado": "erro", "tipo": type(exc).__name__,
               "codigo": getattr(exc, "code", None),
               "status": getattr(exc, "status", None),
               "detalhe": message[:400]}, flush=True)
