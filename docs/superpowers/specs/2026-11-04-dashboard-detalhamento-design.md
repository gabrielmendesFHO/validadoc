# Detalhamento do dashboard por painel lateral

Data: 04/11/2026. Estado: aprovado pelo usuário e implementado localmente.

## Objetivo

Permitir que a equipe parta dos indicadores do dashboard e encontre as pessoas, as dificuldades e os documentos associados. Exemplo ilustrativo do usuário: clicar em “Com dificuldade = 3”, identificar as três inscrições e descobrir quais documentos foram recusados e por quê.

## Abordagens

- Painel lateral: mantém o dashboard como contexto e permite consultar resumos sem trocar de página. Escolhido pelo usuário em 04/11/2026.
- Página filtrada: oferece mais espaço para listas extensas, mas exige sair do dashboard. Reservar a tela existente de auditoria para a análise completa.

## Interações

1. Os quatro indicadores e as etapas dos gráficos e da legenda abrem o mesmo painel lateral com o filtro correspondente. Disponibilizar botões acessíveis para as etapas.
2. O painel mostra título, quantidade total, busca e lista paginada. “Com dificuldade” lista somente inscrições com dificuldade. Total, auditoria, concluídas e etapas respeitam seus próprios critérios.
3. Cada inscrição permite expandir um resumo com candidato, etapa, pessoas do grupo familiar, documentos atuais e seus estados. Destacar recusas e erros, identificar de quem é o documento e exibir o motivo disponível.
4. “Abrir documento” leva à auditoria com aquele documento selecionado. “Analisar inscrição” permite abrir a análise completa.
5. Fechar o painel preserva o dashboard. Ao retornar da auditoria, restaurar a seleção do painel por parâmetros da URL, sem dados pessoais na URL.

## Consistência dos dados

- Usar o mesmo critério de dificuldade para o contador e para a listagem: alerta registrado na inscrição ou envio atual com status REJEITADO/ERRO_EXTRACAO.
- Considerar apenas o envio mais recente para cada documento solicitado e pessoa; uma recusa substituída por um envio válido não constitui dificuldade atual. Preservar o histórico na auditoria.
- Diferenciar documento recusado, falha técnica de extração e documento ainda não enviado. Ausência de documento não deve ser chamada de recusa.
- Se existir somente um alerta registrado, mostrar esse fato sem inventar uma causa. Motivo ausente recebe texto explícito de indisponibilidade.
- Paginar e filtrar no backend antes de limitar resultados; não depender dos primeiros 100 candidatos carregados no dashboard.

## Restrições e decisões de implementação

- Manter React, os estilos existentes, FastAPI e as permissões atuais de ADMIN/ANALISTA. Preservar as alterações já presentes no repositório.
- Reutilizar a auditoria e o checklist existentes quando adequado, evitando carregar arquivos binários para apresentar o resumo.
- Painel com carregamento, erro e nova tentativa, resultado vazio, fechamento por Escape, foco controlado e largura adaptada para celular.
- O resumo é de consulta. Decisões e pareceres continuam na auditoria.
- Publicação no Render autorizada pelo usuário em 04/11/2026, após validação local.

## Validação

- Conferir que cada indicador/etapa abre sua lista e que quantidade, filtro e paginação correspondem.
- Testar dificuldade por alerta, recusa atual e erro técnico; envio corrigido; documentos do titular e familiares; lista vazia e acesso não autorizado.
- Verificar seleção do documento na auditoria e retorno ao resumo.
- Executar os testes pertinentes do backend, lint e build do frontend; verificar o painel no desktop, celular e teclado.

## Escopo

Alteração incremental do dashboard e dos endpoints de consulta, com navegação para a auditoria existente. Não inclui notificações, comunicação com candidatos ou mudanças no processo de decisão. Detalhes de componentes e consultas ficam a cargo da implementação.
