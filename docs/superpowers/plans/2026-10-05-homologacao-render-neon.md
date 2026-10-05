# Homologação Render + Neon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disponibilizar uma versão de testes do ValidaDoc para três integrantes do TCC, usando Render Free e Neon Free.

**Architecture:** Conservar React/Vite e FastAPI; o navegador acessa somente a API. Adaptar SQLAlchemy para PostgreSQL mantendo desenvolvimento local com MySQL. Inicializar um banco de homologação novo, sem copiar o banco local.

**Tech Stack:** React, Vite, FastAPI, SQLAlchemy, Psycopg 3, PyMySQL, PostgreSQL, MariaDB/MySQL, Render e Neon.

**Spec:** `docs/superpowers/specs/2026-10-05-homologacao-render-neon-design.md` — aprovado pelo usuário em 05/10/2026.

## Global Constraints

- Acesso ao produto exige contas; analista/administrador acessam auditoria e candidato acessa somente sua inscrição.
- Os testes iniciais na nuvem usam dados fictícios; os packs pessoais locais não serão copiados automaticamente.
- Manter FastAPI, React/Vite, MySQL local, histórico de reenvios, limite de upload de 15 MB e documentos criptografados.
- Nenhum segredo será incluído no Git, no bundle do frontend ou nos relatórios.
- A amostra prevista contém 50 documentos; verificar bytes e reenvios, sem criar limite novo de quantidade no produto.
- Usar somente planos Free; não contratar planos pagos nem adicionar método de pagamento automaticamente.
- SMTP desativado nesta homologação inicial; não enviar mensagens de pré-cadastro para terceiros.
- Inicialização de banco separada do startup normal; não apagar tabelas, duplicar dados ou trocar senhas silenciosamente.
- Regra inicial: não criar commits/push automaticamente. Autorização posterior explícita do usuário: commit, push da branch `codex/homologacao-render-neon` e publicação Free, sem merge na main.

## Review Focus

1. URL Neon `postgresql://` ou `postgres://` deve selecionar Psycopg 3, mantendo TLS e parâmetros de conexão; teste na tarefa 2.
2. Inicialização repetida deve preservar usuários, hashes e inscrições existentes; teste na tarefa 2.
3. Atualização de jornada deve atualizar `ultima_atividade` também em PostgreSQL; teste na tarefa 2.
4. Configuração incorreta deve falhar com mensagem útil sem revelar credenciais; teste na tarefa 1.
5. Reinício durante extração e abertura de uma rota profunda devem permitir recuperação no navegador; verificação na tarefa 3.

---

### Task 1: Configuração dos ambientes local e de homologação

**Files:**
- Modify: `Backend/app/config.py`, `Backend/app/main.py`, `Backend/app/services/email_service.py`, `Backend/.env.example`.
- Create: `Backend/tests/test_config_homologacao.py`.
- Modify: `Frontend/src/api/client.js`, `Frontend/vite.config.js`.
- Create: `Frontend/.env.example`, `Frontend/src/api/config.js`, `Frontend/tests/api-config.test.mjs`.
- Modify: `.gitignore` para ignorar arquivos de segredos de homologação mantendo `.env.example` versionáveis.

**Interfaces:**
- Consumes: `Settings`, atualmente em `Backend/app/config.py`; cliente Axios já usado por todas as páginas.
- Produces: `Settings.app_env` com valores `development`/`homologation`; `Settings.cors_origins: list[str]`, lido como JSON em `CORS_ORIGINS`; `Settings.smtp_enabled: bool`.
- Produces: `getApiBaseUrl(env: { DEV: boolean, VITE_API_URL?: string }): string` em `Frontend/src/api/config.js`.
- Preserva: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `GEMINI_API_KEY`, modelos e timeout da IA já existentes.

- [x] **Step 1: Escrever os testes antes do código.** `test_homologacao_rejeita_jwt_padrao`, `test_homologacao_rejeita_chave_criptografia_invalida`, `test_homologacao_rejeita_cors_local_ou_curinga`, `test_erro_configuracao_nao_expoe_segredos`. Testar `Settings(_env_file=None, ...)` com valores fictícios; erro deve apontar o campo e não exibir o segredo. Testar frontend: desenvolvimento sem URL → `http://127.0.0.1:8000`; homologação sem URL ou com HTTP → erro; URL HTTPS explícita → essa URL sem barra final.
- [x] **Step 2: Confirmar as falhas.** Na pasta Backend: `python -m pytest tests/test_config_homologacao.py -q`. Na pasta Frontend: `node --test tests/api-config.test.mjs`.
- [x] **Step 3: Implementar configuração.** Homologação exige JWT não padrão com pelo menos 32 caracteres, Fernet válido e origens HTTPS explícitas. Desativar SMTP por `SMTP_ENABLED=false` e retornar antes de acessar a rede. Ler `VITE_API_URL` no cliente e validar também durante o build, para não publicar um bundle que só falha ao abrir. O desenvolvimento continua usando os padrões locais. Erros de configuração não exibem entradas sensíveis.
- [x] **Step 4: Verificar.** Rodar os testes novos, `python -m pytest -q`, `npm run lint` e um build com `VITE_API_URL=https://api.exemplo.invalid`. Confirmar ausência do endereço local e de segredos no bundle. O teste de build usa um domínio fictício, não uma API real.

### Task 2: PostgreSQL real e provisionamento seguro do banco de testes

**Files:**
- Modify: `Backend/app/models.py`, `Backend/app/db.py`, `Backend/requirements.txt`, `Backend/tests/test_operacional.py`.
- Create: `Backend/app/database_config.py`, `Backend/app/manage.py`, `Backend/app/services/provisionamento.py`.
- Create: `Backend/tests/test_database_config.py`, `Backend/tests/test_provisionamento.py`, `Backend/tests/test_postgresql_homologacao.py`.

**Interfaces:**
- Consumes: configuração da tarefa 1 e `Base.metadata` de `Backend/app/models.py`.
- Produces: `normalize_database_url(raw_url: str) -> sqlalchemy.engine.URL`; URLs `postgres://` e `postgresql://` usam `postgresql+psycopg`, preservando usuário, senha, host, banco e query sem imprimir a URL.
- Produces: `criar_esquema(engine: Engine) -> None` e `preparar_processo_teste(session: Session) -> ProcessosBolsa` em `provisionamento.py`.
- Produces: CLI `python -m app.manage --env-file <arquivo-ignorado> init-db`, `create-user --email <email> --perfil ADMIN|ANALISTA|CANDIDATO` e `check-db`. Senha de usuário é solicitada por entrada oculta, nunca por argumento ou por padrão fixo.
- Preserva: `get_db()`, `SessionLocal`, tabelas, enums, relações, dados binários e funções consumidas pelas rotas existentes.

- [x] **Step 1: Escrever testes antes da adaptação.** Testar normalização de URL e preservação de `sslmode=require`. Testar criação do esquema, armazenamento e leitura de um binário Fernet fictício, enums e atualização de `ultima_atividade`. Usar PostgreSQL descartável dedicado para os testes de banco. Testar inicialização duas vezes sem duplicar processo/documentos e criação de usuário existente sem alterar hash ou perfil.
- [x] **Step 2: Confirmar falhas.** `python -m pytest tests/test_database_config.py tests/test_provisionamento.py tests/test_postgresql_homologacao.py -q`. Os testes PostgreSQL requerem URL de um banco descartável, explicitamente separado da homologação; nunca executar `drop_all` no banco local ou no banco publicado.
- [x] **Step 3: Implementar a adaptação.** Adicionar Psycopg 3 com versão fixada após verificar compatibilidade no runtime escolhido; manter PyMySQL. Trocar `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` por default/atualização portáveis em SQLAlchemy. Evitar reflexão do banco durante importação para que a configuração e o provisionamento possam ser testados independentemente; inicializar automap quando a função de consulta de tabelas refletidas for usada.
- [x] **Step 4: Implementar provisionamento explícito.** `init-db` aceita somente `APP_ENV=homologation` com PostgreSQL e cria o esquema atual sem apagar tabelas; verificar estrutura existente e recusar divergência que exija migração. Preparar processo `Homologação TCC 2026` até 31/12/2026: CNH obrigatória, RG/frente, RG/verso, residência e holerite opcionais nesta primeira rodada, seguindo o processo controlado já usado nos testes. Documentar essa configuração como cenário de homologação. `create-user` exige senha forte própria; conflito de e-mail não promove perfil nem redefine senha. `check-db` informa somente conectividade e divergências de esquema sanitizadas.
- [x] **Step 5: Verificar em PostgreSQL real.** Executar provisionamento duas vezes e rodar os testes de persistência, enum, atividade e criptografia. Confirmar que nenhum dado do MariaDB local foi alterado. Rodar toda a suíte existente. Se o PostgreSQL de teste estiver indisponível, registrar o impedimento; testes SQLite ou DDL compilada não substituem essa verificação.

### Task 3: Implantação gratuita, acesso do grupo e reteste no navegador

**Files:**
- Create: `render.yaml`, `Backend/.python-version`, `docs/HOMOLOGACAO.md`.
- Modify: `Backend/app/main.py`, `README.md`.
- Create: `Backend/tests/test_health.py`, `outputs/20261005-homologacao/VALIDACAO.md`.

**Interfaces:**
- Consumes: configuração e banco provisionados nas tarefas 1 e 2.
- Produces: `GET /health`, com sucesso quando o banco responde a `SELECT 1`, ou HTTP 503 sanitizado sem URL/segredo quando indisponível.
- Produces: blueprint Render com `validadoc-api` (Python, Free) e `validadoc-web` (static), build `npm ci && npm run build`, publicação `dist`, rewrite `/*` → `/index.html`. API inicia Uvicorn com `0.0.0.0` e `$PORT`.
- Produces: guia de publicação, acesso, backup/restauração e relatório com URLs verificadas e pendências reais.

- [x] **Step 1: Escrever e observar falha dos testes de saúde.** Testar `/health` com banco disponível e indisponível, sem retornar detalhes internos. Implementar a checagem sem criar ou migrar tabelas no startup.
- [x] **Step 2: Preparar artefatos de implantação.** Conferir sintaxe atual do blueprint Render e runtime Python; usar somente Free. Exigir configuração das URLs reais `VITE_API_URL` e `CORS_ORIGINS` após escolha dos nomes dos serviços. Segredos são configurados nos ambientes privados das plataformas. Documentar backup com a ferramenta PostgreSQL e recuperação com a chave de criptografia separada. Registrar tamanho real dos 50 documentos quando a amostra estiver disponível, crescimento por reenvio e uso no painel do Neon.
- [x] **Step 3: Verificar localmente antes de publicar.** `python -m pytest -q`, `npm run lint`, `npm run build` com URL HTTPS, checagem de blueprint e `git diff --check`. Revisar o diff. Não enviar ao GitHub automaticamente; se o Render exigir acesso ao commit novo, usar a autorização específica do usuário antes do push.
- [x] **Step 4: Usar as contas autorizadas.** Usuário entra nas contas Render/Neon. Criar um projeto Neon Free de homologação, conferir as franquias reais no painel e guardar a conexão TLS de forma privada. Executar `init-db`, preparar contas próprias para o grupo sem enviar e-mails e publicar API/site somente Free. Não acessar projetos existentes de produção nem copiar documentos locais.
- [x] **Step 5: Retestar no navegador com dados fictícios.** Login, KYC, família, upload, reenvio rejeitado/corrigido, conclusão, fila e auditoria. Testar candidato acessando inscrição alheia e auditoria interna; esperar bloqueio. Testar refresh direto em `/familia` e `/auditoria/<id>`, hibernação e interrupção de extração. Registrar evidências sanitizadas; nenhuma decisão de elegibilidade com documentos pessoais.
- [x] **Step 6: Entregar.** URLs funcionando e relatório de testes; informar limites de hibernação, cota, armazenamento e tarefas em processo. Se contas/credenciais ou permissão de push impedirem a publicação, entregar código e configuração verificados e nomear exatamente o bloqueio, sem afirmar que o sistema está publicado.

## Self-Review

Os requisitos do desenho estão cobertos pelas três tarefas: configuração, persistência/provisionamento e implantação/testes. Os cinco pontos de Review Focus têm testes ou verificações explícitas. A amostra de 50 documentos é uma previsão de volume, não um novo bloqueio de upload. Os nomes de interfaces são definidos nas tarefas que os produzem; a publicação depende dos resultados anteriores. Não existe etapa que copie, apague ou migre os dados locais para a nuvem.

## Execution Handoff

Plano preparado para revisão do usuário. Recomendo execução **Native**: implementar aqui, em sequência, porque configuração, banco e publicação dependem uns dos outros; uma revisão independente do código acontece antes de publicar. A implementação começa após o usuário revisar o plano e escolher o método de execução, conforme o fluxo `writing-plans`.

## Resultado da execução — 05/10/2026

Publicado no Render Free + Neon Free; URLs verificadas no relatório `outputs/20261005-homologacao/VALIDACAO.md`. Fluxo remoto fictício e hibernação passaram. O reinício remoto terminou a extração antes da perda; interrupção efetiva e recuperação por timeout/reenvio verificadas no clone local. Amostra de 50 documentos e concorrência ainda pendentes por disponibilidade da amostra. Branch enviada com autorização posterior, main sem merge.
