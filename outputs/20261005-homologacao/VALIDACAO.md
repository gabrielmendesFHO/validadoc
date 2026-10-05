# Validação da preparação Render + Neon — 05/10/2026

## Estado

Configuração e PostgreSQL implementados. Projeto Neon **ValidaDoc-Homologacao** criado no plano Free em Ohio, PostgreSQL 18. Conexão agrupada com TLS guardada em arquivo ignorado pelo Git; segredos não constam deste relatório. `init-db` executado duas vezes, seguido de `check-db`: schema compatível, sem duplicação do processo. Nenhum pack pessoal ou banco MariaDB foi copiado.

**Site/API ainda não publicados.** Usuário autorizou commit/push da branch `codex/homologacao-render-neon` e publicação Free, sem merge na main. Faltam os serviços Render e a rodada fictícia remota. As URLs de exemplo não são endereços verificados. Login Render confirmado na conta do usuário; serviços existentes de outro projeto não foram alterados.

## Evidências locais

| Verificação | Resultado |
|---|---|
| Baseline Windows | 95 testes do backend passaram |
| Backend final, Python 3.14.3/Linux + PostgreSQL 17 dedicado | 123 testes passaram; 3 avisos de dependências |
| Novos testes de banco | 13 passaram, com schemas descartáveis exclusivos |
| Normalização da URL | `postgres://`/`postgresql://` → Psycopg 3, preservando TLS/query/credenciais |
| Repetição do provisionamento | Preserva processo, documentos, inscrições, perfil e hash de usuário existente |
| PostgreSQL | Persistência de enum/binário Fernet e atualização de atividade confirmadas |
| Configuração e SMTP | Chaves/CORS inválidos recusados, erros sanitizados, SMTP desativado não acessa rede |
| `/health` | Testes 200 com banco e 503 sanitizado sem banco |
| Frontend | 3 testes Node, lint e build com URL HTTPS passaram; build sem URL recusado |
| Bundle | Sem `127.0.0.1:8000`, URL PostgreSQL ou `GEMINI_API_KEY` |
| Dependências frontend | Axios e brace-expansion atualizados dentro das faixas atuais; `npm audit` sem vulnerabilidades |
| Blueprint | Validado com JSON Schema oficial obtido em `https://render.com/schema/render.yaml.json` |

As regressões de configuração foram observadas falhando antes da validação. O novo `/health` inicialmente respondeu 404. A comparação do schema falhou na repetição por aliases PostgreSQL e foi corrigida; divergência real de coluna permanece bloqueada. Uma execução isolada com o default MySQL anterior reproduziu erro de sintaxe PostgreSQL em `ON UPDATE`, seguida da suíte com o default portável passando. A mutação não alterou arquivos do produto.

O Controle de Aplicativo do Windows bloqueou a DLL Psycopg 3.3.6. Os testes e o provisionamento Neon foram executados no Docker/Linux sem desativar proteções. O teste PostgreSQL usa apenas banco dedicado `validadoc_test_*`; a conexão publicada não é usada em fixtures que removem schemas.

## Capacidade e memória

O painel Neon usado na criação mostra **0,5 GB**; não assumir 1 GB anunciado sem confirmar na conta. A estimativa histórica de sete arquivos/10.043.489 bytes projeta aproximadamente 96 MB Fernet para 50 documentos, antes de overhead/reenvios. A amostra completa de 50 ainda não foi medida.

Nesta execução foram encontrados seis arquivos de formatos aceitos no diretório controlado. Processamento sequencial local, sem rede e com container limitado a 512 MB: pico de **363,8 MiB RSS** no subprocesso isolado e **491,6 MiB RSS** repetindo o processamento depois de importar a API completa; imagem maior 4032×3024 pixels. Os seis arquivos somaram **8.298.042 bytes**. Não houve envio desses documentos ao Neon/Gemini nessa medição. A margem é pequena e a medição ainda não cobre envio ao provedor, escrita criptografada no banco ou uploads simultâneos: não considerar a hospedagem estável até esses testes.

O build mantém aviso de bundle de aproximadamente 742 kB; divisão de código pode ser feita depois. O SMTP fica desativado; mensagens de boas-vindas não são enviadas.

## Pendências da publicação

- Revisão independente concluída: três problemas importantes corrigidos; nenhuma observação menor pendente.
- Commit/push especificamente autorizados; envio da branch em andamento.
- Criar API Free e site Static no Render, preencher segredos privados e conferir os dois domínios reais/CORS.
- Criar contas próprias/fictícias com senha forte e executar login, KYC, família, upload/reenvio, conclusão, fila/auditoria e bloqueios por perfil/inscrição.
- Verificar refresh de rotas profundas, cold start e interrupção da extração no ambiente remoto.
- Medir a amostra completa/uso de banco e a memória da API inteira antes de considerar a hospedagem estável.

Há tarefas de IA em processo, sem fila durável. Reinício pode interromper a extração; recuperação inicial depende de novo envio, preservando o histórico. Guia operacional e backup em `docs/HOMOLOGACAO.md`.

## Revisão e regressões finais

As três constatações foram reproduzidas com testes falhando e corrigidas na mesma rodada: candidato provisionado agora usa nome provisório reconhecido e aceita identidade fictícia, preenche nome/CPF e avança KYC; KYC aplica o mesmo timeout de 120 segundos do checklist e libera reenvio sem alterar histórico ou processo recente; schema recusa defaults obrigatórios ausentes e IDs sem geração. A suíte final passou com 123 testes, incluindo 13 de configuração/provisionamento PostgreSQL e dois cenários de interrupção/atividade recente no KYC. `check-db` no Neon passou novamente após a checagem mais completa.

## Decisões de execução

- Worktree nativo a partir de HEAD para preservar a versão local em execução; integração posterior permanece necessária.
- Ledger mantido enquanto não existem commits, pois o plano proíbe commit/push automático; remover somente depois de preservar o registro.
- PostgreSQL testado/administrado em Linux devido ao bloqueio da DLL Windows; Windows precisa desse ambiente Docker para os comandos Neon.
- Apenas atualizações compatíveis de Axios/brace-expansion para eliminar avisos reais do audit; verificados lint/build, rodada de navegador ainda pendente.
