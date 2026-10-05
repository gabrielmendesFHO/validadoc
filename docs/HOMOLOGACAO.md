# Homologação do ValidaDoc no Render + Neon

Esta implantação é para testes dos três integrantes do TCC. O MariaDB local continua separado. Não importar o dump antigo nem copiar documentos ou contas locais para a nuvem.

## Arquitetura e configuração

React estático → FastAPI Free → PostgreSQL Neon Free. Os documentos ficam criptografados no PostgreSQL. O navegador recebe somente `VITE_API_URL`; nenhuma senha ou chave do backend pode começar com `VITE_`.

O blueprint da raiz usa Python 3.14.3, Node 24.19.0, API Free em Ohio e site estático. Os deployments automáticos estão desligados nesta primeira rodada. Não há Render Postgres, disco pago ou worker pago no blueprint.

Variáveis da API, guardadas no painel privado do Render:

| Variável | Valor |
|---|---|
| `APP_ENV` | `homologation` |
| `DATABASE_URL` | URL de conexão agrupada do Neon com `sslmode=require`; aceita `postgresql://`/`postgres://` e seleciona Psycopg 3 |
| `JWT_SECRET_KEY` | Segredo próprio aleatório, pelo menos 32 caracteres; não reutilizar o local |
| `ENCRYPTION_KEY` | Chave Fernet própria, estável entre deployments; guardar backup separado |
| `GEMINI_API_KEY` | Chave autorizada do Google AI Studio; franquia independente do Render/Neon |
| `CORS_ORIGINS` | JSON com origem HTTPS exata do site, por exemplo `["https://validadoc-web.onrender.com"]`, sem barra final |
| `SMTP_ENABLED` | `false`; nenhum e-mail de pré-cadastro é enviado |

`GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL` e `GEMINI_TIMEOUT_MS` conservam os valores atuais, podendo ser configurados no backend. A criptografia deve manter a mesma chave enquanto existirem documentos; gerar outra chave torna os arquivos antigos ilegíveis.

No site, configurar `VITE_API_URL` com a URL HTTPS real da API e executar outro build se ela mudar. O build recusa URL ausente, HTTP ou localhost. Desenvolvimento com `npm run dev` permite a API local. A rewrite `/*` → `/index.html` e assets com base `/` permitem refresh de rotas React.

## Publicação

1. Criar um projeto **Free** exclusivo no Neon, na região da API, somente com PostgreSQL. Não ativar serviços adicionais nem fornecer cartão. Conferir a franquia na conta: em 05/10/2026 o painel usado nesta execução mostrou **0,5 GB** na criação, apesar do anúncio público de 1 GB. Planejar pelo painel até confirmar a alteração.
2. Guardar a conexão e os segredos num arquivo local como `Backend/.env.homologacao` (ignorado pelo Git). Não substituir o `.env` local. Confirmar host Neon e TLS antes de inicializar.
3. Com as dependências instaladas, na pasta `Backend`, executar:

   ```powershell
   python -m app.manage --env-file .env.homologacao init-db
   python -m app.manage --env-file .env.homologacao init-db
   python -m app.manage --env-file .env.homologacao check-db
   ```

   `init-db` exige homologation + PostgreSQL. Usa os nove modelos atuais, não apaga tabelas e recusa estrutura divergente que precise de migração. A segunda execução preserva os dados. O startup da API não cria tabelas nem contas.
4. Provisionar contas próprias. A senha é digitada duas vezes por entrada oculta, tem 12+ caracteres, letras e números. Não há senha fixa ou argumento de senha:

   ```powershell
   python -m app.manage --env-file .env.homologacao create-user --email EMAIL_DO_GRUPO --perfil ADMIN
   python -m app.manage --env-file .env.homologacao create-user --email EMAIL_DO_ANALISTA --perfil ANALISTA
   python -m app.manage --env-file .env.homologacao create-user --email EMAIL_DO_CANDIDATO --perfil CANDIDATO
   ```

   Candidato recebe uma inscrição no processo de teste. E-mail existente é recusado sem promover perfil nem trocar hash. Informar as senhas ao grupo por canal privado; não usar `admin123` ou contas do banco local.
5. Revisar os arquivos e enviar ao GitHub somente com autorização específica. No Render, criar um Blueprint apontando para o commit que contém `render.yaml`. Se houver serviços existentes com esses nomes, escolher nomes novos para evitar atualizar outro projeto. Conferir que a API está **Free** e o site é **Static**, sem recursos pagos.
6. Preencher os campos privados `sync: false`. Conferir os endereços atribuídos e ajustar `VITE_API_URL`/`CORS_ORIGINS` para os domínios reais. Publicar e conferir `/health` → `200 {"status":"ok"}`; banco indisponível retorna 503 sanitizado.
7. Executar a rodada fictícia abaixo antes de liberar o endereço ao grupo. Não considerar a publicação concluída apenas porque o build passou.

Se a DLL Psycopg for bloqueada pelo Controle de Aplicativo do Windows, usar Python no Linux/Docker. Não desativar a proteção. Nesta execução a imagem local `validadoc-homologacao-tests` foi preparada com Python 3.14.3 e os requirements. Com Docker ativo, a partir da raiz:

```powershell
docker run --rm -v "${PWD}:/workspace" validadoc-homologacao-tests python -m app.manage --env-file .env.homologacao check-db
docker run --rm -it -v "${PWD}:/workspace" validadoc-homologacao-tests python -m app.manage --env-file .env.homologacao create-user --email EMAIL --perfil ADMIN
```

Essa imagem é uma ferramenta local de teste, não um artefato publicado. A senha continua sendo solicitada pelo CLI. Em outra máquina, instalar os requirements num ambiente Python/Linux equivalente.

## Cenário inicial e testes

O processo **Homologação TCC 2026** vai de 01/01/2026 a 31/12/2026. CNH é obrigatória; RG/frente, RG/verso, residência e holerite são opcionais nesta rodada. Essa configuração reproduz o cenário controlado e não representa os requisitos completos do TCC nem de uma instituição real.

Testar no navegador com nomes/documentos fictícios claramente identificados: login, KYC, família, upload, reenvio rejeitado/corrigido, conclusão, fila e auditoria. Confirmar que candidato não acessa inscrição alheia nem auditoria. Abrir `/familia` e `/auditoria/ID` diretamente e atualizar a página.

Para a suíte PostgreSQL, usar somente `TEST_POSTGRESQL_URL` num banco descartável cujo nome começa com `validadoc_test_`. As fixtures criam schemas aleatórios e removem apenas esses schemas. Nunca usar a conexão publicada nos testes destrutivos. Rodar `python -m pytest -q`; sem essa variável os testes PostgreSQL ficam **pulados**, o que não comprova compatibilidade.

## Hibernação e processamento

Render Free hiberna após 15 minutos sem tráfego; a primeira requisição pode demorar cerca de um minuto. Não repetir uploads enquanto o envio anterior ainda estiver aguardando resposta. O pool da homologação mantém até duas conexões e permite duas adicionais.

As extrações são tarefas do processo da API. Reinício pode deixar documento `PROCESSANDO_IA` sem análise concluída. Ao consultar KYC ou checklist, envios que passaram de 120 segundos sem conclusão são marcados como erro e a tela permite reenviar. Não há fila persistente nem retomada automática nesta versão: reenviar e acompanhar o novo envio; o histórico anterior permanece. Um resultado antigo que chegar depois do reenvio não deve avançar a jornada. Testar um reinício durante extração e registrar o resultado. Se isso ocorrer com frequência, uma fila durável deverá ser priorizada antes da defesa.

Preservar o limite de 15 MB por upload. O número previsto de 50 documentos não é um limite implementado. Sete arquivos disponíveis somaram 10.043.489 bytes; a projeção para 50 é cerca de 72 MB originais/96 MB Fernet, antes de índices, análises e reenvios. Medir a amostra completa e conferir uso no Neon antes/depois da rodada. Imagens grandes podem consumir mais memória do que o tamanho do arquivo; a estabilidade nos 512 MB do Render depende dessa verificação.

## Backup e restauração

Usar PostgreSQL client da mesma versão principal do Neon ou mais recente. Para backup/restauração, preferir conexão **direta** Neon (sem `-pooler`), mantendo TLS. Inserir credenciais por arquivo privado de serviço `pg_service.conf` + arquivo de senha `pgpass.conf` (permissões somente do usuário); não colocar URL/senha em comandos compartilhados. Exemplo com um serviço privado chamado `validadoc_homologacao`:

```text
pg_dump --dbname=service=validadoc_homologacao --format=custom --file=validadoc-homologacao.dump
pg_restore --dbname=service=validadoc_restauracao --no-owner --no-acl validadoc-homologacao.dump
```

Restaurar em um banco **novo e vazio**, conferir schema/contagens e testar a descriptografia de um arquivo fictício antes de trocar a API. Não usar `--clean` no banco ativo. Guardar a chave Fernet num cofre separado do dump; o dump contém dados sensíveis mesmo com binários criptografados. Não enviar dump/chaves ao repositório ou canais compartilhados. O histórico de seis horas do Neon Free não substitui backup.

Fontes de implantação verificadas em 05/10/2026: [Blueprint Render](https://render.com/docs/blueprint-spec), [runtime Python](https://render.com/docs/python-version), [limites Free](https://render.com/docs/free), [Psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html). Quotas podem mudar; conferir o painel antes de qualquer atualização de plano.
