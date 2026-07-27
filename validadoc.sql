-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 24/07/2026 às 15:12
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `validadoc`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `analises_ocr`
--

CREATE TABLE `analises_ocr` (
  `id` int(11) NOT NULL,
  `documento_id` int(11) NOT NULL,
  `dados_extraidos` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`dados_extraidos`)),
  `taxa_confianca` float DEFAULT NULL,
  `status_auditoria` varchar(20) NOT NULL DEFAULT 'PENDENTE',
  `parecer` text DEFAULT NULL,
  `inconsistencias` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (`inconsistencias` is null or json_valid(`inconsistencias`)),
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `documentos_enviados`
--

CREATE TABLE `documentos_enviados` (
  `id` int(11) NOT NULL,
  `inscricao_id` int(11) NOT NULL,
  `solicitado_id` int(11) NOT NULL,
  `membro_id` int(11) DEFAULT NULL,
  `caminho_arquivo` varchar(255) NOT NULL,
  `status_processamento` varchar(50) NOT NULL DEFAULT 'PENDENTE',
  `mensagem_erro` text DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `documentos_solicitados`
--

CREATE TABLE `documentos_solicitados` (
  `id` int(11) NOT NULL,
  `processo_id` int(11) NOT NULL,
  `nome_documento` varchar(100) NOT NULL,
  `obrigatorio` tinyint(1) NOT NULL DEFAULT 0,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `documentos_solicitados`
--

INSERT INTO `documentos_solicitados` (`id`, `processo_id`, `nome_documento`, `obrigatorio`, `criado_em`) VALUES
(1, 1, 'CNH', 1, '2026-07-24 11:38:06'),
(2, 1, 'RESIDENCIA', 1, '2026-07-24 11:38:06'),
(3, 1, 'HOLERITE', 0, '2026-07-24 11:38:06'),
(4, 1, 'RG', 1, '2026-07-24 11:38:06');

-- --------------------------------------------------------

--
-- Estrutura para tabela `inscricoes`
--

CREATE TABLE `inscricoes` (
  `id` int(11) NOT NULL,
  `processo_id` int(11) NOT NULL,
  `candidato_id` int(11) NOT NULL,
  `status_geral` varchar(50) NOT NULL DEFAULT 'PENDENTE',
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `instituicoes`
--

CREATE TABLE `instituicoes` (
  `id` int(11) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `endereco` varchar(255) DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `instituicoes`
--

INSERT INTO `instituicoes` (`id`, `nome`, `endereco`, `criado_em`) VALUES
(1, 'Instituição Genérica', 'Rua Exemplo, 100', '2026-07-24 11:38:05');

-- --------------------------------------------------------

--
-- Estrutura para tabela `membros_familia`
--

CREATE TABLE `membros_familia` (
  `id` int(11) NOT NULL,
  `inscricao_id` int(11) NOT NULL,
  `nome_completo` varchar(255) NOT NULL,
  `parentesco` varchar(50) DEFAULT NULL,
  `renda_declarada` decimal(10,2) DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `processos_bolsa`
--

CREATE TABLE `processos_bolsa` (
  `id` int(11) NOT NULL,
  `instituicao_id` int(11) DEFAULT NULL,
  `nome` varchar(255) NOT NULL,
  `renda_per_capita_limite` decimal(10,2) DEFAULT NULL,
  `data_inicio` date NOT NULL,
  `data_fim` date NOT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `processos_bolsa`
--

INSERT INTO `processos_bolsa` (`id`, `instituicao_id`, `nome`, `renda_per_capita_limite`, `data_inicio`, `data_fim`, `criado_em`) VALUES
(1, 1, 'Processo Genérico', 1412.00, '2026-01-01', '2026-12-31', '2026-07-24 11:38:06');

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `nome_completo` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `perfil` enum('CANDIDATO','ANALISTA','ADMIN') NOT NULL DEFAULT 'CANDIDATO',
  `instituicao_id` int(11) DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `usuarios`
--

INSERT INTO `usuarios` (`id`, `nome_completo`, `email`, `senha_hash`, `perfil`, `instituicao_id`, `criado_em`) VALUES
(1, 'Administrador ValidaDoc', 'admin@example.com', '$2b$12$r42AFSEB6LjndMQZuURY2O67UUaz1ZVTcH9F/G1uVy8fPJpnLUIpa', 'ANALISTA', 1, '2026-07-24 11:38:06'),
(2, 'Candidato Teste', 'candidato@example.com', '$2b$12$r42AFSEB6LjndMQZuURY2O67UUaz1ZVTcH9F/G1uVy8fPJpnLUIpa', 'CANDIDATO', 1, '2026-07-24 11:38:06');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `analises_ocr`
--
ALTER TABLE `analises_ocr`
  ADD PRIMARY KEY (`id`),
  ADD KEY `documento_id` (`documento_id`);

--
-- Índices de tabela `documentos_enviados`
--
ALTER TABLE `documentos_enviados`
  ADD PRIMARY KEY (`id`),
  ADD KEY `inscricao_id` (`inscricao_id`),
  ADD KEY `solicitado_id` (`solicitado_id`),
  ADD KEY `membro_id` (`membro_id`);

--
-- Índices de tabela `documentos_solicitados`
--
ALTER TABLE `documentos_solicitados`
  ADD PRIMARY KEY (`id`),
  ADD KEY `processo_id` (`processo_id`);

--
-- Índices de tabela `inscricoes`
--
ALTER TABLE `inscricoes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `processo_id` (`processo_id`),
  ADD KEY `candidato_id` (`candidato_id`);

--
-- Índices de tabela `instituicoes`
--
ALTER TABLE `instituicoes`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `membros_familia`
--
ALTER TABLE `membros_familia`
  ADD PRIMARY KEY (`id`),
  ADD KEY `inscricao_id` (`inscricao_id`);

--
-- Índices de tabela `processos_bolsa`
--
ALTER TABLE `processos_bolsa`
  ADD PRIMARY KEY (`id`),
  ADD KEY `instituicao_id` (`instituicao_id`);

--
-- Índices de tabela `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `instituicao_id` (`instituicao_id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `analises_ocr`
--
ALTER TABLE `analises_ocr`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `documentos_enviados`
--
ALTER TABLE `documentos_enviados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `documentos_solicitados`
--
ALTER TABLE `documentos_solicitados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `inscricoes`
--
ALTER TABLE `inscricoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `instituicoes`
--
ALTER TABLE `instituicoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `membros_familia`
--
ALTER TABLE `membros_familia`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `processos_bolsa`
--
ALTER TABLE `processos_bolsa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `analises_ocr`
--
ALTER TABLE `analises_ocr`
  ADD CONSTRAINT `analises_ocr_ibfk_1` FOREIGN KEY (`documento_id`) REFERENCES `documentos_enviados` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `documentos_enviados`
--
ALTER TABLE `documentos_enviados`
  ADD CONSTRAINT `documentos_enviados_ibfk_1` FOREIGN KEY (`inscricao_id`) REFERENCES `inscricoes` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `documentos_enviados_ibfk_2` FOREIGN KEY (`solicitado_id`) REFERENCES `documentos_solicitados` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `documentos_enviados_ibfk_3` FOREIGN KEY (`membro_id`) REFERENCES `membros_familia` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `documentos_solicitados`
--
ALTER TABLE `documentos_solicitados`
  ADD CONSTRAINT `documentos_solicitados_ibfk_1` FOREIGN KEY (`processo_id`) REFERENCES `processos_bolsa` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `inscricoes`
--
ALTER TABLE `inscricoes`
  ADD CONSTRAINT `inscricoes_ibfk_1` FOREIGN KEY (`processo_id`) REFERENCES `processos_bolsa` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `inscricoes_ibfk_2` FOREIGN KEY (`candidato_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `membros_familia`
--
ALTER TABLE `membros_familia`
  ADD CONSTRAINT `membros_familia_ibfk_1` FOREIGN KEY (`inscricao_id`) REFERENCES `inscricoes` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `processos_bolsa`
--
ALTER TABLE `processos_bolsa`
  ADD CONSTRAINT `processos_bolsa_ibfk_1` FOREIGN KEY (`instituicao_id`) REFERENCES `instituicoes` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `usuarios`
--
ALTER TABLE `usuarios`
  ADD CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`instituicao_id`) REFERENCES `instituicoes` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
