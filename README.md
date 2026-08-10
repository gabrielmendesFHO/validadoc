# ValidaDoc

Backend API scaffold usando FastAPI e SQLAlchemy.

## Setup

1. Criar o ambiente virtual:

   python -m venv .venv

2. Ativar o ambiente virtual:

   Windows PowerShell:

   .\.venv\Scripts\Activate.ps1

   Windows Command Prompt:

   .\.venv\Scripts\activate.bat

3. Instalar dependências:

   pip install -r Backend/requirements.txt

4. Copiar arquivo de ambiente:

   copy .env.example .env

5. Executar o servidor de desenvolvimento:

   cd Backend
   uvicorn app.main:app --reload

Para executar os testes:

cd Backend
python -m unittest discover -s tests -v

## Notas

- Use o arquivo `.env` para configurar sua conexão com o banco de dados.
- O SDK do Gemini é instalado usando o pacote `google-genai`.
