-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 10/08/2026 às 19:22
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

--
-- Despejando dados para a tabela `analises_ocr`
--

INSERT INTO `analises_ocr` (`id`, `documento_id`, `dados_extraidos`, `taxa_confianca`, `status_auditoria`, `parecer`, `inconsistencias`, `criado_em`) VALUES
(12, 15, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 503 UNAVAILABLE. {\'error\': {\'code\': 503, \'message\': \'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.\', \'status\': \'UNAVAILABLE\'}}', NULL, '2026-08-04 12:42:06'),
(13, 16, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, foco adequado e texto claramente legível.\", \"documento_integro\": true, \"nome\": \"464530198/50\", \"data_nascimento\": \"15/02/2022\", \"filiacao\": \"SSP\", \"numero_rg\": \"verso\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-04 13:42:42'),
(14, 17, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Imagem de alta resolução, boa iluminação, nitidez e sem rasuras.\", \"documento_integro\": true, \"nome\": \"ARARAS SP ARARAS CN:LV.A71 /FLS.85 /Nº55308\", \"data_nascimento\": \"15/02/2022\", \"filiacao\": \"Mitiaki Yamamoto\", \"numero_rg\": \"58.614.967-3\", \"orgao_expedidor\": \"IIRGD.SSP\", \"uf\": \"SP\", \"data_expedicao\": \"15/02/2022\", \"cpf\": \"464530198/50\", \"lado_documento\": \"verso\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-04 13:52:26'),
(15, 18, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', NULL, '2026-08-04 14:24:46'),
(16, 19, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', NULL, '2026-08-04 14:25:11'),
(17, 20, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', NULL, '2026-08-04 14:25:34'),
(18, 27, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', NULL, '2026-08-04 14:31:53'),
(19, 28, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', NULL, '2026-08-04 14:32:15'),
(20, 29, '{\"legibilidade\": 100, \"qualidade_imagem\": \"Excelente, documento digital original de alta resolução.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"numero_cnh\": \"08370470546\", \"data_nascimento\": \"06/05/2005\", \"data_validade\": \"07/06/2033\", \"categorias\": [\"A\", \"B\"], \"cpf\": \"464.530.198-50\"}', 1, 'EXTRAIDO', NULL, NULL, '2026-08-04 14:45:59'),
(21, 30, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, foco e resolução.\", \"documento_integro\": true, \"nome_titular\": \"LUANA BRESSAN RODRIGUES\", \"endereco\": \"R GUILHERME NARDI, 283 - . ARARAS SP\", \"cep\": \"13604-306\", \"data_emissao\": \"25/03/2026\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-04 14:46:41'),
(22, 31, '{\"legibilidade\": 100, \"qualidade_imagem\": \"Excelente qualidade, imagem digital de alta definição e legibilidade perfeita.\", \"documento_integro\": true, \"nome\": \"Gabriel Fernando Mendes\", \"cpf\": \"464.530.198-50\", \"empresa\": \"Tech Solutions Desenvolvimento de Software LTDA\", \"competencia\": \"07/2026\", \"renda_bruta\": 2500.0, \"renda_liquida\": 2149.19, \"data_emissao\": \"05/08/2026\"}', 1, 'EXTRAIDO', NULL, NULL, '2026-08-04 14:47:39'),
(23, 32, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, foco e nitidez em todo o documento.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"filiacao\": \"JOSÉ ROBERTO MENDES e JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"numero_rg\": \"5070737A\", \"orgao_expedidor\": \"SSP-SP\", \"uf\": \"SP\", \"data_expedicao\": \"06/05/2005\", \"cpf\": \"123.456.789-00\", \"lado_documento\": \"frente\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-04 14:50:27'),
(24, 33, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', NULL, '2026-08-10 14:40:34'),
(25, 34, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', NULL, '2026-08-10 14:41:27'),
(26, 35, NULL, NULL, 'ERRO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', NULL, '2026-08-10 14:48:06'),
(27, 36, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, foco claro e alta resolução.\", \"documento_integro\": true, \"lado\": \"FRENTE\", \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"filiacao\": \"JOSÉ ROBERTO MENDES e JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"numero_rg\": \"5070737A\", \"orgao_expedidor\": \"SSP\", \"uf\": \"SP\", \"data_expedicao\": \"06/05/2005\", \"cpf\": \"5070737A\", \"lado_documento\": \"frente\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 15:27:58'),
(28, 37, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, nitidez e foco, com excelente visibilidade dos dados.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"nome_pai\": \"JOSÉ ROBERTO MENDES\", \"nome_mae\": \"JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"lado_documento\": \"frente\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 15:42:53'),
(29, 38, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Imagem com ótima resolução, foco e iluminação adequados.\", \"documento_integro\": true, \"nome\": \"ARARAS SP ARARAS\", \"data_nascimento\": \"15/02/2022\", \"nome_pai\": \"CN:LV.A71\", \"nome_mae\": \"FLS.85\", \"lado_documento\": \"verso\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 15:43:38'),
(30, 39, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Imagem com excelente foco, boa iluminação e nitidez.\", \"documento_integro\": true, \"numero_rg\": \"58.614.967-3\", \"cpf\": \"464530198/50\", \"orgao_expedidor\": \"IIRGD - SSP\", \"uf\": \"SP\", \"data_expedicao\": \"15/02/2022\", \"codigo_barras\": \"\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 15:45:53'),
(31, 40, '{\"legibilidade\": 100, \"qualidade_imagem\": \"Imagem com excelente iluminação, alta resolução e foco nítido.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"nome_pai\": \"JOSÉ ROBERTO MENDES\", \"nome_mae\": \"JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"lado_documento\": \"frente\"}', 1, 'EXTRAIDO', NULL, NULL, '2026-08-10 15:55:33'),
(32, 41, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Imagem com ótima iluminação, foco e resolução.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"nome_pai\": \"JOSÉ ROBERTO MENDES\", \"nome_mae\": \"JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"lado_documento\": \"frente\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 16:46:51'),
(33, 42, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Documento digital com excelente resolução, foco nítido e boa iluminação.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"numero_cnh\": \"08370470546\", \"data_nascimento\": \"06/05/2005\", \"data_validade\": \"02/06/2033\", \"categorias\": [\"AB\"], \"cpf\": \"464.530.198-50\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 16:57:21'),
(34, 43, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Imagem com excelente resolução, foco e iluminação uniforme.\", \"documento_integro\": true, \"numero_rg\": \"58.614.967-3\", \"cpf\": \"464530198/50\", \"orgao_expedidor\": \"IIRGD\", \"uf\": \"SP\", \"data_expedicao\": \"15/02/2022\", \"codigo_barras\": \"null\", \"observacoes\": \"2 via\", \"lado_documento\": \"verso\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 16:58:34'),
(35, 44, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Boa iluminação, boa resolução e foco claro.\", \"documento_integro\": true, \"nome_titular\": \"LUANA BRESSAN RODRIGUES\", \"endereco\": \"R GUILHERME NARDI, 283 - , ARARAS SP\", \"cep\": \"13604-306\", \"data_emissao\": \"25/03/2026\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 16:59:49'),
(36, 45, '{\"legibilidade\": 95, \"qualidade_imagem\": \"Excelente iluminação, foco e nitidez.\", \"documento_integro\": true, \"nome\": \"GABRIEL FERNANDO MENDES\", \"data_nascimento\": \"06/05/2005\", \"nome_pai\": \"JOSÉ ROBERTO MENDES\", \"nome_mae\": \"JOCELINA APARECIDA BUENO DA SILVA MENDES\", \"lado_documento\": \"frente\"}', 0.95, 'EXTRAIDO', NULL, NULL, '2026-08-10 17:15:49');

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

--
-- Despejando dados para a tabela `documentos_enviados`
--

INSERT INTO `documentos_enviados` (`id`, `inscricao_id`, `solicitado_id`, `membro_id`, `caminho_arquivo`, `status_processamento`, `mensagem_erro`, `criado_em`) VALUES
(15, 1, 4, NULL, 'uploads/documentos\\1_4_20260804094151_RG verso.jpg', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 503 UNAVAILABLE. {\'error\': {\'code\': 503, \'message\': \'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.\', \'status\': \'UNAVAILABLE\'}}', '2026-08-04 12:41:51'),
(16, 1, 4, NULL, 'uploads/documentos\\1_5_20260804104140_RG verso.jpg', 'CONCLUIDO', NULL, '2026-08-04 13:41:40'),
(17, 1, 4, NULL, 'uploads/documentos\\1_5_20260804105104_RG verso.jpg', 'CONCLUIDO', NULL, '2026-08-04 13:51:04'),
(18, 1, 3, NULL, 'uploads/documentos\\1_3_20260804112444_holerite.png', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', '2026-08-04 14:24:44'),
(19, 1, 3, NULL, 'uploads/documentos\\1_3_20260804112510_holerite.png', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', '2026-08-04 14:25:10'),
(20, 1, 3, NULL, 'uploads/documentos\\1_3_20260804112533_holerite.png', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', '2026-08-04 14:25:33'),
(27, 1, 2, NULL, 'uploads/documentos\\1_2_20260804113149_comprovante de residência.jpg', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', '2026-08-04 14:31:49'),
(28, 1, 1, NULL, 'uploads/documentos\\1_1_20260804113213_Documento exportado pela CDT.pdf', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.response_schema\\\': Cannot find field.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.BadRequest\', \'fieldViolations\': [{\'field\': \'generation_config.response_schema\', \'description\': \'Invalid JSON payload received. Unknown name \"additional_properties\" at \\\'generation_config.respon', '2026-08-04 14:32:13'),
(29, 1, 1, NULL, 'uploads/documentos\\1_1_20260804114551_Documento exportado pela CDT.pdf', 'CONCLUIDO', NULL, '2026-08-04 14:45:51'),
(30, 1, 2, NULL, 'uploads/documentos\\1_2_20260804114629_comprovante de residência.jpg', 'CONCLUIDO', NULL, '2026-08-04 14:46:29'),
(31, 1, 3, NULL, 'uploads/documentos\\1_3_20260804114730_holerite.png', 'CONCLUIDO', NULL, '2026-08-04 14:47:30'),
(32, 1, 4, NULL, 'uploads/documentos\\1_4_20260804115014_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-04 14:50:14'),
(33, 1, 4, NULL, 'uploads/documentos\\1_4_20260810114024_RG frente _1 (1).jpg', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', '2026-08-10 14:40:24'),
(34, 1, 2, NULL, 'uploads/documentos\\1_2_20260810114120_RG frente _1 (1).jpg', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', '2026-08-10 14:41:20'),
(35, 1, 4, NULL, 'uploads/documentos\\1_4_20260810114800_RG frente _1 (1).jpg', 'ERRO_EXTRACAO', 'Falha na chamada à API do Gemini: 400 INVALID_ARGUMENT. {\'error\': {\'code\': 400, \'message\': \'API key not valid. Please pass a valid API key.\', \'status\': \'INVALID_ARGUMENT\', \'details\': [{\'@type\': \'type.googleapis.com/google.rpc.ErrorInfo\', \'reason\': \'API_KEY_INVALID\', \'domain\': \'googleapis.com\', \'metadata\': {\'service\': \'generativelanguage.googleapis.com\'}}, {\'@type\': \'type.googleapis.com/google.rpc.LocalizedMessage\', \'locale\': \'en-US\', \'message\': \'API key not valid. Please pass a valid API key.\'}]', '2026-08-10 14:48:00'),
(36, 1, 4, NULL, 'uploads/documentos\\1_4_20260810122653_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-10 15:26:53'),
(37, 1, 4, NULL, 'uploads/documentos\\1_4_20260810124241_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-10 15:42:41'),
(38, 1, 4, NULL, 'uploads/documentos\\1_4_20260810124318_RG verso.jpg', 'CONCLUIDO', NULL, '2026-08-10 15:43:18'),
(39, 1, 4, NULL, 'uploads/documentos\\1_5_20260810124539_RG verso.jpg', 'CONCLUIDO', NULL, '2026-08-10 15:45:39'),
(40, 1, 4, NULL, 'uploads/documentos\\1_4_20260810125518_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-10 15:55:33'),
(41, 3, 4, NULL, 'uploads/documentos\\3_4_20260810134635_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-10 16:46:51'),
(42, 3, 1, NULL, 'uploads/documentos\\3_1_20260810135712_Documento exportado pela CDT.pdf', 'CONCLUIDO', NULL, '2026-08-10 16:57:12'),
(43, 3, 4, NULL, 'uploads/documentos\\3_5_20260810135817_RG verso.jpg', 'CONCLUIDO', NULL, '2026-08-10 16:58:34'),
(44, 3, 2, NULL, 'uploads/documentos\\3_2_20260810135930_comprovante de residência.jpg', 'CONCLUIDO', NULL, '2026-08-10 16:59:30'),
(45, 1, 4, NULL, 'uploads\\documentos\\1_4_20260810141539_1_2_20260810114120_RG frente _1 (1).jpg', 'CONCLUIDO', NULL, '2026-08-10 17:15:39');

-- --------------------------------------------------------

--
-- Estrutura para tabela `documentos_solicitados`
--

CREATE TABLE `documentos_solicitados` (
  `id` int(11) NOT NULL,
  `processo_id` int(11) NOT NULL,
  `nome_documento` enum('RG','RG_VERSO','CNH','RESIDENCIA','HOLERITE','OUTRO') NOT NULL,
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
  `renda_per_capita_calculada` decimal(10,2) DEFAULT NULL,
  `parecer` text DEFAULT NULL,
  `inconsistencias` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (`inconsistencias` is null or json_valid(`inconsistencias`)),
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `inscricoes`
--

INSERT INTO `inscricoes` (`id`, `processo_id`, `candidato_id`, `status_geral`, `renda_per_capita_calculada`, `parecer`, `inconsistencias`, `criado_em`) VALUES
(1, 1, 2, 'NAO_APTO', 3200.00, 'Renda per capita calculada (R$ 3200.00) ultrapassa o limite máximo do processo (R$ 1412.00).', '[\"RESIDENCIA: documento emitido há 138 dias (limite: 90).\"]', '2026-07-24 15:32:49'),
(2, 1, 3, 'PENDENTE', NULL, 'Documentos obrigatórios pendentes: CNH, RESIDENCIA, RG, RG_VERSO.', NULL, '2026-08-10 16:42:18'),
(3, 1, 4, 'REVISAO_MANUAL', NULL, 'Inconsistências encontradas — revisão manual necessária.', '[\"RESIDENCIA: documento emitido há 138 dias (limite: 90).\", \"Renda per capita não calculada — holerite não processado ou renda_bruta ausente.\", \"CPF não cadastrado no perfil do candidato — identidade não confirmada.\", \"Nome do documento de identidade diverge do nome cadastrado.\"]', '2026-08-10 16:42:18');

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

--
-- Despejando dados para a tabela `membros_familia`
--

INSERT INTO `membros_familia` (`id`, `inscricao_id`, `nome_completo`, `parentesco`, `renda_declarada`, `criado_em`) VALUES
(1, 1, 'Jocelina', 'Mãe', 7500.00, '2026-08-04 11:32:57'),
(2, 1, 'Beto', 'Pai', 2800.00, '2026-08-04 11:33:45'),
(3, 1, 'Gabi', 'Irmã', 0.00, '2026-08-04 11:34:08'),
(4, 2, 'Nicolle Amy', 'Esposa', 1000.00, '2026-08-10 16:44:02'),
(5, 3, 'Nicolle Amy', 'Esposa', 1000.00, '2026-08-10 16:45:25'),
(6, 3, 'jessi Amy', 'fio', 1000.00, '2026-08-10 16:45:40'),
(7, 3, 'bartolomeu Amy', 'fio', 0.00, '2026-08-10 16:45:47');

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
  `cpf` varchar(14) DEFAULT NULL,
  `instituicao_id` int(11) DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `usuarios`
--

INSERT INTO `usuarios` (`id`, `nome_completo`, `email`, `senha_hash`, `perfil`, `cpf`, `instituicao_id`, `criado_em`) VALUES
(1, 'Administrador ValidaDoc', 'admin@example.com', '$2b$12$r42AFSEB6LjndMQZuURY2O67UUaz1ZVTcH9F/G1uVy8fPJpnLUIpa', 'ANALISTA', NULL, 1, '2026-07-24 11:38:06'),
(2, 'Candidato Teste', 'candidato@example.com', '$2b$12$r42AFSEB6LjndMQZuURY2O67UUaz1ZVTcH9F/G1uVy8fPJpnLUIpa', 'CANDIDATO', '464.530.198-50', 1, '2026-07-24 11:38:06'),
(3, 'Candidato teste 2', 'teste2@gmail.com', '123', 'CANDIDATO', NULL, 1, '2026-08-10 16:30:55'),
(4, 'Candidato Teste 3', 'teste3@gmail.com', '123', 'CANDIDATO', NULL, 1, '2026-08-10 16:30:55');

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=37;

--
-- AUTO_INCREMENT de tabela `documentos_enviados`
--
ALTER TABLE `documentos_enviados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=46;

--
-- AUTO_INCREMENT de tabela `documentos_solicitados`
--
ALTER TABLE `documentos_solicitados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de tabela `inscricoes`
--
ALTER TABLE `inscricoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `instituicoes`
--
ALTER TABLE `instituicoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `membros_familia`
--
ALTER TABLE `membros_familia`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de tabela `processos_bolsa`
--
ALTER TABLE `processos_bolsa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

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
