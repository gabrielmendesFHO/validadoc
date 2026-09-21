-- Índices usados pelas métricas do funil e pela fila operacional.
-- Os testes em information_schema tornam a migração segura para reexecução.
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'inscricoes'
     AND index_name = 'idx_inscricoes_status_funil_atividade') = 0,
  'CREATE INDEX idx_inscricoes_status_funil_atividade ON inscricoes (status_funil, ultima_atividade)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'inscricoes'
     AND index_name = 'idx_inscricoes_alertas_dificuldade') = 0,
  'CREATE INDEX idx_inscricoes_alertas_dificuldade ON inscricoes (alertas_dificuldade)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'documentos_enviados'
     AND index_name = 'idx_documentos_enviados_inscricao_criado') = 0,
  'CREATE INDEX idx_documentos_enviados_inscricao_criado ON documentos_enviados (inscricao_id, criado_em)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
