# Dashboard com detalhamento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** abrir indicadores e etapas em painel lateral com inscrições, documentos e motivos, com navegação até o documento na auditoria.

**Architecture:** compartilhar uma expressão SQL de dificuldade baseada no envio vigente por pessoa/documento. Filtrar e paginar a lista no servidor; carregar resumo sob demanda, sem binários. Controlar filtro, página e expansão pela URL e manter o texto da busca no history.state da aba para preservar o retorno da auditoria sem nomes no endereço.

**Tech Stack:** React, React Router, CSS, FastAPI, SQLAlchemy, pytest; Playwright para verificar navegação e layout.

**Spec:** docs/superpowers/specs/2026-11-04-dashboard-detalhamento-design.md (aprovada pelo usuário em 04/11/2026).

## Global Constraints

- Preservar alterações existentes; branch codex/dashboard-detalhamento, sem publicação no Render.
- Apenas ADMIN/ANALISTA nos endpoints de consulta; nenhuma alteração de parecer no resumo.
- Usar envio mais recente por inscrição, pessoa e documento solicitado, com desempate pelo ID.
- Separar recusa, falha técnica e ausência de envio; não inventar motivos.

## Review Focus

- Dados mudam enquanto o painel carrega: respostas antigas não substituem o filtro atual.
- Histórico corrigido ou datas empatadas: contador e lista devem selecionar o mesmo envio.
- Familiar e titular enviam o mesmo tipo: considerar cada pessoa separadamente.
- Entrada direta por URL ou retorno: restaurar painel, busca e página com validação dos parâmetros.
- Teclado, celular e falhas de API: permitir fechar, tentar novamente e navegar sem perda de contexto.

### Task 1: Consultas consistentes

**Files:** Backend/app/services/indicadores_dashboard.py (novo), Backend/app/routes/operacional.py, Backend/app/routes/inscricoes.py, Backend/tests/test_operacional.py.

**Interfaces:** `criterio_dificuldade()` retorna expressão SQL para Inscricoes; `documentos_vigentes(db, inscricao_id)` retorna envios atuais. GET /inscricoes/dashboard/candidatos aceita com_dificuldade, status_funil, busca, pagina, por_pagina; retorna itens/total/pagina/por_pagina. GET /dashboard/inscricoes/{id}/resumo retorna candidato/etapa/alertas e documentos por pessoa, incluindo ausentes.

- [x] Adicionar testes de API que exigem igualdade entre métrica e filtro, reenvio corrigido, empate de data, familiar, paginação, motivos e permissões. Rodar e observar falhas da funcionalidade ausente.
- [x] Implementar expressão compartilhada, filtros e resumo. Atualizar a fila de atenção para usar a mesma regra.
- [x] Rodar testes operacionais e suíte do backend; conferir resultados.

### Task 2: Painel e navegação

**Files:** Frontend/src/components/DashboardDrawer.jsx e .css (novos), Frontend/src/pages/Dashboard.jsx, Frontend/src/pages/Dashboard.css, Frontend/src/pages/Auditoria.jsx, Frontend/tests/dashboard-detalhamento.cjs (novo).

**Interfaces:** drawer recebe seleção/filtros/onClose; lê APIs da Task 1. Auditoria aceita documento e retorno validado por query string; retorno permitido apenas para /dashboard.

- [x] Criar teste Playwright com respostas sintéticas nos limites HTTP, cobrindo abrir KPI, expandir inscrição, abrir documento e voltar; observar falha sem painel.
- [x] Implementar painel com paginação, busca, motivos, foco e estados de erro/vazio. Ligar KPIs, gráficos, legenda e ação por candidato; restaurar seleção via URL.
- [x] Executar teste de fluxo e verificar celular/teclado, estados vazio/erro e resposta atrasada. Rodar lint e build.

### Task 3: Revisão e entrega

- [x] Revisar diff da tarefa e pedir revisão independente com spec, plano e resultados. Corrigir problemas relevantes e verificar novamente apenas o necessário.
- [x] Registrar validação e escopo entregue neste plano. Informar branch e ausência de publicação.

## Registro de execução

- Pré-execução: branch criada a partir do checkout atual, mantendo alterações visuais ainda não commitadas. Execução local autorizada pelo pedido “Aprovado pode implementar”; não haverá nova rodada de aprovação do plano.
- Dependência Task 1 → Task 2: lista paginada com com_dificuldade e resumo por inscrição; contratos acima serão compartilhados. Sem conflitos com a spec.

- Task 1: complete — novos testes falharam antes da implementação (critério antigo e endpoint ausente); após implementação, testes operacionais e suíte completa passaram.
- Task 2: complete — teste de navegador falhou por ausência do painel antes da implementação; passou após integrar KPI, barra, legenda, resumo, documento e retorno. Usado diálogo nativo com foco e largura responsiva.
- Task 3: complete — revisão independente concluída, com correção e testes RED→GREEN para busca fora da URL, possível divergência, documento removido, foco no retorno e intervalo de página vazia. Os dois últimos foram tratados como relevantes à navegação aprovada, apesar da classificação menor inicial.
- Final: backend `python -m pytest -q` → 107 passed, 4 avisos de depreciação de dependências/código existente. Testes usam SQLite local e não acessam dados de produção.
- Final: `node node_modules/eslint/bin/eslint.js .` e `node node_modules/vite/bin/vite.js build` → exit 0; permanece aviso de bundle maior que 500 kB, já presente no build inicial.
- Final: Playwright com Edge headless → fluxo completo e cinco cenários de revisão passaram. Cobertura: indicador/etapa/barra, pessoas e documento selecionado, retorno com busca/página, Escape/foco, celular sem overflow, vazio, erro e nova tentativa, resposta antiga descartada, privacidade da busca, possível divergência, arquivo removido e página fora do intervalo. Dados do navegador são fictícios nas fronteiras HTTP.
- Evidências visuais: outputs/dashboard-detalhamento-desktop.png e outputs/dashboard-detalhamento-mobile.png (dados fictícios).
- Entrega mantida na branch local codex/dashboard-detalhamento. Alterações preexistentes preservadas; nenhum commit, push, merge ou deploy realizado. As mudanças sobrepostas no dashboard continuam no checkout para não incluir ajustes visuais anteriores em um commit desta tarefa.
- Revisão não avaliou alterações visuais preexistentes, decisões de parecer nem publicação em produção; esses itens permanecem fora do escopo aprovado.

## Publicação autorizada posteriormente

- Em 04/11/2026, o usuário autorizou a publicação. Preparada cópia de release em `codex/publicar-dashboard-20261104`, a partir de `943ec9c` da branch `codex/homologacao-render-neon`, mantendo configuração de produção e correções posteriores à base local.
- Aplicados apenas o painel, seus endpoints, navegação, testes e documentação. Ajustes preexistentes do checkout original não foram sobrescritos nem incluídos novamente.
- Validação da release: 173 testes do backend aprovados, 8 testes de PostgreSQL descartável ignorados por ausência de banco dedicado, 2 avisos de depreciação. Lint, 3 testes de configuração da API, build com URL HTTPS de produção e 6 cenários Playwright Edge aprovados. Permanece o aviso preexistente de tamanho de bundle.
- Render: workspace Teste, serviços validadoc-api e validadoc-web, publicação manual na branch codex/homologacao-render-neon. Nenhuma alteração de configuração, banco ou segredo necessária.
