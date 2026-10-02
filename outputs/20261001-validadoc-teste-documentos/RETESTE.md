# Reteste de extração e identidade — 02/10/2026

## Correções

- Modelo alternativo configurável e prazo de 45 segundos por chamada.
- Tentativas redundantes do SDK limitadas para permitir a recuperação pelo modelo alternativo.
- Mensagens específicas para autenticação, cota, sobrecarga e modelo indisponível, sem registrar documentos ou chave nos logs.
- Rejeição de CPF divergente do titular. Divergência de nome sem CPF correspondente também é rejeitada.
- Seleção explícita de RG ou CNH no KYC, para evitar associar RG ao campo CNH.

## Evidências

- Testes reais pela API: RG e CNH PDF terminaram em CONCLUIDO; identidade de outra pessoa terminou em REJEITADO.
- A chave atual funcionou. O modelo principal retornou 503/429 e o fallback anterior retornou 404. O novo fallback processou os documentos.
- Backend no reteste anterior: 67 testes aprovados. Após as correções desta rodada: 77 testes aprovados, 6 avisos de depreciação.
- Frontend: lint e build aprovados. Build alerta sobre tamanho do bundle.
- Web: extração concluída na inscrição controlada 8. Esse teste revelou a associação incorreta de RG ao tipo CNH, corrigida no seletor.
- Web de 02/10, tentativa inicial: a conexão de automação com o Chrome impediu completar a repetição. Esse impedimento foi resolvido nesta rodada, com uploads pelo seletor nativo usando caminhos Windows com barras normais.

## Rodada web concluída em 02/10/2026

Inscrição local controlada 9, com sessões separadas de candidato e administrador. CNH obrigatória para titular e familiar neste processo de teste. RG e verso, residência e holerite opcionais. A obrigatoriedade de RG foi removida somente deste processo de teste, pois o pack familiar contém CNH e não contém RG.

- KYC: RG frente enviado e concluído, liberando o cadastro familiar.
- Família: dados extraídos da CNH legível, cadastro salvo e CPF editado com persistência confirmada ao reabrir.
- Identidade: CNH PDF do titular, CNH PDF familiar e RG verso concluídos no reteste.
- Rejeição: CNH de outra pessoa no campo do titular rejeitada com motivo visível. Mesmo PDF enviado em outro campo bloqueado por duplicidade.
- Auditoria: CPF familiar ausente e CPF sintético divergente produziram REVISAO_MANUAL com motivos específicos. O CPF correto foi restaurado após os testes.
- Pendências: concluir documentos antes das CNHs obrigatórias foi bloqueado. A auditoria listou os documentos ausentes como PENDENTE.
- Após ambas as CNHs concluídas, inscrição passou a PRONTO_AUDITORIA. Administrador conferiu documento original e dados declarados/extraídos lado a lado. Motivos persistiram após recarregar.
- Candidato tentou acessar a auditoria interna e recebeu bloqueio de perfil, sem dados internos exibidos.
- Resultado atual: REVISAO_MANUAL por comprovante de residência vencido há 191 dias, possível divergência de categoria na leitura e ausência de holerites. Inscrição permanece na fila. Candidato vê “Aguardando revisão manual do analista” e resultado final pendente.

### Problemas encontrados e corrigidos

1. A CNH inicialmente retornou CPF com dígitos verificadores inválidos, causando falso conflito com o RG verso. Foi adicionada validação dos dígitos, instrução específica para leitura do CPF e nova tentativa/modelo alternativo. A validação dos dígitos não comprova autenticidade. Os documentos originais foram conferidos visualmente. Somente o CPF inválido preenchido automaticamente na conta de teste foi limpo para o reenvio. O reteste confirmou CPF válido e correspondente, sem alterar manualmente os valores extraídos.
2. Faltava o botão para concluir envio na tela de comprovantes. O botão agora chama a conclusão e mostra as pendências. A contagem considera documentos obrigatórios individualmente.
3. A interface do analista não oferecia conferência automática nem exibia todos os motivos persistidos. Botão, resultado e inconsistências foram adicionados.
4. REVISAO_MANUAL encerrava a jornada e retirava a inscrição da fila. Agora permanece PRONTO_AUDITORIA até parecer manual. Teste de regressão cobre a permanência na fila.

### Evidências e limites

Evidências sanitizadas em resultados_web_20261002.json e capturas web-rejeicao.jpg, web-pronto-auditoria.jpg e web-revisao-manual.jpg. Documentos originais, CPFs e chave API não foram copiados para a planilha.

Planilha: 33 casos, 22 aprovados, 0 falhas abertas registradas, 5 bloqueados e 6 não executados. Aprovações distinguem rodada API e navegador. T13 registra apenas a parte verificada do reenvio; a coerência completa do histórico permanece pendente. T30, parecer final, não foi executado nesta rodada. Não foi emitida decisão de elegibilidade.

T21 está bloqueado porque falta comprovante recente. T26 a T29 dependem de holerites controlados, ainda ausentes. Testes unitários de regras não substituem esses cenários completos com documentos. Outros casos não executados estão identificados na planilha.

Validação técnica final: 77 testes de backend aprovados, lint e build do frontend aprovados, git diff --check sem erros. Permanecem avisos de depreciação nas dependências e de tamanho do bundle no build.

## Situação local

API 8000, frontend 5173 e MariaDB 3306 disponíveis na verificação final. Alterações locais ainda sem commit ou implantação.

As abas do candidato e da fila administrativa foram deixadas abertas. Nenhuma implantação ou commit foi feito nesta rodada.
