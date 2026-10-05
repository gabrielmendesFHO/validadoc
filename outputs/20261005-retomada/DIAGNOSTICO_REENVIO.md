# Retomada e diagnóstico de reenvio — 05/10/2026

## Estado verificado

- API, frontend e MariaDB com portas locais 8000, 5173 e 3306 em escuta.
- Repositório inicialmente sem alterações locais; HEAD 317d4c7.
- Packs continuam com sete arquivos; não foram encontrados holerites nem comprovante de residência adicional.

## Reprodução com dados fictícios

As funções reais de `Backend/app/routes/inscricoes.py` foram chamadas com registros fictícios e uma sessão simulada. Nenhum documento foi enviado ao Gemini e nenhum registro do banco local foi alterado. Esta reprodução da lógica não substitui o reteste completo pelo navegador.

1. RG antigo rejeitado seguido de RG corrigido concluído: `_gerar_checklist_para_pessoa` retorna ENVIADO, enquanto `_coletar_documentos_auditoria` retorna RG PENDENTE. O coletor inclui a versão rejeitada na condição que exige todas as partes concluídas.
2. Documento obrigatório antigo concluído seguido de reenvio rejeitado: `concluir_documentos` retorna PRONTO_AUDITORIA. A checagem aceita qualquer aprovação no histórico, mesmo que o envio atual esteja rejeitado.

## Correção aplicada

A seleção da versão mais recente por inscrição, pessoa e documento solicitado foi centralizada em `Backend/app/services/historico_documental.py`. A data de criação define a ordem e o ID desempata datas iguais. Checklist, conclusão de documentos, consulta/conclusão de KYC e auditoria usam a mesma seleção. Frente e verso de RG continuam sendo itens distintos. As versões antigas continuam consultáveis no histórico.

Também foi corrigido o avanço automático do KYC após a extração. Somente uma identidade ainda vigente pode preencher nome/CPF ou liberar a etapa familiar. Uma extração antiga continua gravando seu resultado OCR no histórico. A transação de leitura inicial é encerrada antes da chamada à IA e o documento é recarregado depois, evitando conservar a leitura anterior a um reenvio registrado durante a chamada.

## Verificação após a correção

- Os 12 casos iniciais de regressão falharam antes da correção e passaram depois.
- Foram acrescentados casos positivos, processamento fora de ordem e reenvio registrado durante uma chamada de IA simulada. Os testes usam SQLite isolado e simulam somente o provedor externo.
- Suíte completa: `python -m pytest -q -o faulthandler_timeout=30` → 95 aprovados, 6 avisos de depreciação de dependências.
- Os testes de integração de pré-cadastro agora isolam o envio de e-mail. A execução completa terminou em poucos segundos após esse isolamento; não depende do SMTP real configurado.
- Consulta somente leitura na inscrição controlada 9: RG vigente consolidado como CONCLUIDO, oito envios históricos e cinco vigentes, incluindo versões rejeitadas preservadas. Nenhum CPF ou dado extraído foi exportado nesta verificação.
- Revisão independente do código sem problemas acionáveis encontrados.
- API local reiniciada com as alterações; API e frontend responderam com sucesso. MariaDB permanece em escuta na porta 3306.
- `git diff --check` sem erros. Alterações ainda sem commit ou implantação.

## Limites desta verificação

- A execução inicial da suíte parou de produzir saída após 32 testes e foi interrompida. Esse registro é histórico; a suíte completa passou após isolar o envio de e-mail.
- Não houve novo upload ao Gemini nem repetição completa pelo navegador nesta correção. A conferência da inscrição existente foi feita somente por leitura no banco, com as funções corrigidas.
- A planilha e o Trello não foram alterados nesta retomada. T13 tem a regressão técnica corrigida e verificada; o reteste completo pelo navegador permanece pendente.
