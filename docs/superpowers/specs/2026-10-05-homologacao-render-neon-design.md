# Homologação gratuita do ValidaDoc — Render + Neon

Status: desenho aprovado pelo usuário em 05/10/2026; implementação e publicação pendentes.

## Objetivo e decisões confirmadas

Publicar uma versão de testes para os três integrantes do TCC, mantendo FastAPI, React/Vite e o fluxo atual de validação e auditoria. O usuário escolheu Render + Neon e autorizou a adaptação para outro banco para manter a hospedagem gratuita por enquanto.

Arquitetura: site estático React no Render → API FastAPI no Render Free → PostgreSQL no Neon Free. O navegador acessa somente a API; as credenciais do PostgreSQL, a chave JWT, a chave de criptografia e a chave Gemini ficam no backend. A franquia do Gemini é independente da hospedagem.

## Escopo da adaptação

1. **Configuração por ambiente:** `Frontend/src/api/client.js` passa a ler `VITE_API_URL`, conservando o endereço local como padrão apenas no desenvolvimento. Builds de homologação exigem URL HTTPS da API. O backend recebe `APP_ENV`, `CORS_ORIGINS` e `DATABASE_URL`; em homologação recusa chave JWT padrão/curta e chave de criptografia inválida. Nenhum segredo será incluído no Git, no bundle do frontend ou nos relatórios.
2. **PostgreSQL sem abandonar o desenvolvimento local:** incluir driver Psycopg 3, aceitar URLs PostgreSQL com TLS e conexão agrupada do Neon, manter suporte MySQL/PyMySQL. Os modelos existentes são a fonte do esquema; não importar diretamente o dump MySQL antigo. `ultima_atividade` deve usar um default e atualização compatíveis com PostgreSQL, preservando o acompanhamento da jornada. Categorias, perfis, valores de enum, IDs, vínculos familiares e documentos binários criptografados mantêm seu comportamento.
3. **Banco de homologação novo:** criar as tabelas a partir do esquema atual em um PostgreSQL separado, preparar processo de teste e contas com senhas próprias por procedimento explícito e repetível. Não copiar inscrições, identidades, documentos ou senhas conhecidos do ambiente local. Reexecutar o procedimento não deve duplicar dados, apagar tabelas ou trocar senhas silenciosamente.
4. **Implantação reproduzível:** arquivo `render.yaml` com API Free e site estático; runtime Python suportado, comando Uvicorn ouvindo `0.0.0.0` e a porta atribuída pelo Render; build Vite e fallback de rotas para `/index.html`. Inicialização de banco separada do startup normal; conexão e saúde verificáveis sem divulgar dados ou credenciais. Requisições após hibernação podem demorar e não devem ser confundidas com falha de extração.
5. **Operação de testes:** preservar limite atual de 15 MB e histórico de reenvios. Testar imagens reais autorizadas quanto ao consumo de memória antes de considerar o ambiente estável. Manter SMTP desativado nesta homologação inicial, pois o Render Free bloqueia as portas SMTP tradicionais. Cadastros de teste serão provisionados sem envio de mensagens.

## Dados e acesso

Acesso ao produto exige contas; analista/administrador acessam auditoria e candidato acessa somente sua inscrição. As credenciais locais conhecidas não serão reutilizadas online. Testes iniciais na nuvem usam dados fictícios; qualquer cópia posterior dos packs de documentos pessoais precisa de autorização específica para este destino.

O armazenamento inicial mantém os documentos criptografados no PostgreSQL. Eles consomem a franquia do banco, incluindo o crescimento causado pela criptografia. Guardar backup do banco e da chave de criptografia em locais protegidos, separados; não incluir essas chaves em backups compartilhados com o grupo. Os planos gratuitos não substituem uma política de backup.

O usuário definiu uma amostra de 50 documentos. Nos sete arquivos atualmente disponíveis, o total é 10.043.489 bytes e a média é aproximadamente 1,43 MB. Projetando essa média para 50 arquivos, seriam cerca de 72 MB originais e 96 MB após o crescimento aproximado da criptografia Fernet, antes dos demais dados do banco. É uma estimativa, não a medição da amostra completa. Cada reenvio preservado consome espaço adicional; o volume real e o uso no painel devem ser conferidos antes e depois da rodada. Não será introduzido bloqueio arbitrário de 50 uploads no produto.

## Verificação e critérios de entrega

- Testes de backend atuais continuam passando, com novas regressões para configuração por ambiente, criação do esquema e atualização de atividade em PostgreSQL.
- Validar criação, leitura, atualização e persistência dos modelos em PostgreSQL real de teste; compilar SQL ou passar testes SQLite isoladamente não prova compatibilidade completa.
- Build/lint do frontend passam; build de homologação não contém `127.0.0.1:8000`, chave Gemini ou credenciais de banco.
- API e frontend publicados em HTTPS, com CORS restrito ao domínio escolhido; conexão PostgreSQL por TLS.
- Fluxo completo fictício no navegador: login, KYC, família, upload, reenvio, conclusão, fila e auditoria. Uma conta de candidato não consegue acessar dados de outra inscrição nem a auditoria interna.
- Conferir reabertura de páginas profundas, reenvio com processamento fora de ordem, hibernação/reinício e mensagens de erro. A publicação não implica aprovação final dos cenários ainda pendentes com holerites e comprovante recente.
- Uso permanece dentro das franquias Free; não contratar planos pagos ou adicionar método de pagamento automaticamente.

## Limites conhecidos e alternativa

Render Free suspende a API após 15 minutos sem tráfego, pode reiniciá-la e não oferece disco persistente. As tarefas de IA atuais rodam no processo da API; esta publicação inicial é para testes e exige verificar a recuperação após interrupção. Uma fila persistente de processamento pode ser uma melhoria posterior conforme o resultado, e não será apresentada como já existente.

Render oferece PostgreSQL Free com 1 GB, mas o banco expira após 30 dias. Por isso a alternativa inteiramente no Render não foi escolhida para testes até a defesa em dezembro. MySQL no Render exige serviço e disco que não fazem parte dessa opção gratuita.

Neon anunciou em 02/10/2026 1 GB de PostgreSQL e 100 CU-horas por projeto por mês no plano Free. Esses limites devem ser conferidos no painel na criação; franquias e preços podem mudar. Acesso às contas Render/Neon e às conexões privadas ainda é necessário para publicar.

## Fontes verificadas em 05/10/2026

- [Render Free: serviços, expiração, suspensão, portas SMTP e franquias](https://render.com/docs/free)
- [Render: implantação MySQL](https://render.com/docs/deploy-mysql)
- [Render: rotas de site estático](https://render.com/docs/redirects-rewrites)
- [Neon: franquia gratuita anunciada em 02/10/2026](https://neon.com/blog/neon-free-plan-1-gb-per-project)

## Revisão do desenho

Não foram encontrados campos de decisão em aberto sobre provedor, stack ou estratégia de dados: o provedor foi escolhido pelo usuário, a stack será preservada e o banco remoto será novo. A implementação detalhada e os testes serão registrados no plano após revisão deste desenho. Não haverá remoção ou alteração do banco local para realizar a publicação.
