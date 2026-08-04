from PIL import Image
from app.config import settings
from app.services.gemini_service import _SCHEMAS_E_PROMPTS, _mime_type
from google import genai
from google.genai import types

img = Image.new('RGB', (200, 200), (255, 255, 255))
path = 'tmp_debug_rg.png'
img.save(path)

schema = _SCHEMAS_E_PROMPTS['RG']['schema']
prompt = _SCHEMAS_E_PROMPTS['RG']['prompt']

with open(path, 'rb') as f:
    data = f.read()

client = genai.Client(api_key=settings.gemini_api_key)

try:
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            prompt,
            types.Part.from_bytes(data=data, mime_type=_mime_type(path)),
        ],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=schema,
            temperature=0.1,
        ),
    )
    print('SUCCESS')
    print(response.text)
except Exception as exc:
    import traceback
    traceback.print_exc()
    print(type(exc).__name__, exc)
