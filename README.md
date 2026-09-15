# ValidaDoc

O ValidaDoc possui uma API em FastAPI (`Backend`) e uma interface em React +
Vite (`Frontend`). No desenvolvimento, mantenha os dois servidores em execucao.

## Requisitos

- Python 3.11 ou superior
- Node.js 20.19 ou superior (a versao LTS e recomendada)
- MySQL, com o banco `validadoc` criado a partir de `Backend/validadoc.sql`

## Instalar o Node.js (Windows)

No PowerShell, execute:

```powershell
winget install OpenJS.NodeJS.LTS
```

Depois da instalacao, feche e abra novamente o terminal. Se estiver usando o
terminal integrado, reinicie o VS Code tambem: programas abertos antes da
instalacao nao recebem a atualizacao do `PATH` automaticamente.

Confirme a instalacao:

```powershell
node --version
npm --version
```

O Node deve ser 20.19 ou mais recente. Caso o `winget` nao esteja disponivel,
instale a versao LTS pelo site oficial: https://nodejs.org/

## Configuracao inicial

Na raiz do repositorio, instale as dependencias do backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r Backend/requirements.txt
```

Crie um arquivo `.env` na raiz do repositorio. Ajuste as credenciais conforme
o MySQL local (nao envie esse arquivo ao Git):

```env
DATABASE_URL=mysql+pymysql://root:SUA_SENHA@127.0.0.1:3306/validadoc
JWT_SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
GEMINI_API_KEY=
ENCRYPTION_KEY=
```

Importe `Backend/validadoc.sql` no MySQL e instale as dependencias fixadas do
frontend:

```powershell
cd Frontend
npm ci
```

Use `npm ci` em uma maquina nova: ele instala exatamente as versoes presentes
em `package-lock.json`.

## Executar em desenvolvimento

Abra dois terminais na raiz do repositorio.

Terminal 1 - API:

```powershell
.\.venv\Scripts\Activate.ps1
cd Backend
uvicorn app.main:app --reload
```

A API estara em http://127.0.0.1:8000 e a documentacao em
http://127.0.0.1:8000/docs.

Terminal 2 - React:

```powershell
cd Frontend
npm run dev
```

Abra o endereco informado pelo Vite, normalmente http://localhost:5173. O
frontend chama a API em `http://127.0.0.1:8000`, entao a API precisa estar em
execucao.

## Validacoes

Frontend:

```powershell
cd Frontend
npm run lint
npm run build
```

Backend:

```powershell
.\.venv\Scripts\Activate.ps1
cd Backend
python -m unittest discover -s tests -v
```

## Problemas comuns

- **`node` ou `npm` nao e reconhecido:** reinicie o terminal e o VS Code. O
  Node ja pode estar instalado, mas processos antigos continuam com o `PATH`
  anterior.
- **Falha de requisicao ou CORS no navegador:** inicie a API na porta `8000` e
  o Vite na porta `5173`.
- **`npm ci` falha por versao do Node:** atualize para Node.js 20.19 ou mais
  recente.
