-- Registra o último login do candidato para acompanhamento operacional.
ALTER TABLE `inscricoes`
  ADD COLUMN `ultimo_acesso` timestamp NULL DEFAULT NULL AFTER `ultima_atividade`;
