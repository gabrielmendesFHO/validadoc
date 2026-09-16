-- Migração 007: Adiciona colunas para controle do funil de conversão da jornada na tabela inscricoes
ALTER TABLE `inscricoes`
  ADD COLUMN `status_funil` enum('PRE_CADASTRADO','KYC_PENDENTE','KYC_VALIDADO','FAMILIA_PENDENTE','DOCS_PENDENTES','PRONTO_AUDITORIA','CONCLUIDO','ABANDONO') NOT NULL DEFAULT 'PRE_CADASTRADO' AFTER `candidato_id`,
  ADD COLUMN `ultima_atividade` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER `status_funil`,
  ADD COLUMN `alertas_dificuldade` int(11) NOT NULL DEFAULT 0 AFTER `ultima_atividade`;

